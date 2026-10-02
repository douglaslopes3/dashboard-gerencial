# -*- coding: utf-8 -*-
"""Leitura das METAS por cliente (D-74, 08/09/2026) -> FATO_META.

Formato do arquivo (`Metas_FY'27.xlsx`, medido em 08/09/2026; desde a D-87 em `../bases compartilhadas/`):
uma linha por CLIENTE x CATEGORIA x PERIODO x TIPO DE META, com o valor na
coluna `Valor`. E o formato certo para crescer: mes novo e linha nova, nunca
coluna nova. O leitor devolve a FATO_META LARGA — uma linha por (ANO_MES,
COD_CLIENTE, CATEGORIA) com META_RECEITA (R$) e META_PESO_KG (kg).

Regras deste leitor (decisoes do Douglas de 08/09/2026):

1. **A pasta inteira e varrida** (Q2). Tanto um arquivo que cresce quanto um
   arquivo por ano fiscal funcionam. A competencia vem do CONTEUDO (coluna
   `Periodo`: data, serial do Excel ou texto AAAA-MM), nunca do nome do
   arquivo (A9: mes inventado por posicao foi defeito real do projeto
   anterior). O MESMO mes em dois arquivos ABORTA: substituir, nunca somar.
2. **Tipo de meta desconhecido ABORTA.** O mapa `Tipo Meta -> metrica` mora
   no config (`fontes.metas.tipos_meta`); um rotulo novo no arquivo nao e
   ignorado em silencio — e o arquivo que precisa ser conferido.
3. **Chave duplicada ABORTA**, valor nulo ABORTA, periodo irreconhecivel
   ABORTA. Meta negativa ENTRA como esta (Q1): o rateio herdou o sinal das
   devolucoes, e nada e corrigido aqui — o caso sai listado no relatorio de
   qualidade (`data/quality/metas_negativas*.csv`).
4. **Reconciliacao interna**: a soma da FATO_META larga por mes tem de bater
   com a soma das linhas cruas do arquivo (o pivo nao pode perder linha).
   O arquivo nao traz linha "Total"; o gabarito e a propria soma bruta.

Unidade: a meta de volume vem em KG e fica em KG na FATO_META, como o
PESO_KG da FATO_SELLIN. A conversao para toneladas acontece UMA vez, na
montagem do cubo (mesma escala do realizado), nunca aqui nem no template.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..utils.config import CFG, caminho
from ..utils.log import abortar, log
from ..utils.texto import ano_mes, digitos, numero, texto
from . import cache

_MET = CFG["fontes"].get("metas") or {}
_VAL = CFG["validacao"]

CHAVE = ["ANO_MES", "COD_CLIENTE", "CATEGORIA"]
METRICAS = ["META_RECEITA", "META_PESO_KG"]
COLUNAS = CHAVE + METRICAS + ["ARQUIVO_ORIGEM"]

# Serial do Excel (sistema 1900): 46266 = 01/09/2026.
_ORIGEM_EXCEL = pd.Timestamp("1899-12-30")


def vazia() -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype="string") for c in CHAVE}
                        | {c: pd.Series(dtype="float64") for c in METRICAS}
                        | {"ARQUIVO_ORIGEM": pd.Series(dtype="string")})


def ano_mes_periodo(s: pd.Series) -> pd.Series:
    """`Periodo` -> `AAAA-MM`. Aceita data (datetime), serial do Excel (int/
    float ou texto de digitos) e texto `AAAA-MM`/`AAAA/MM`. O que nao casar
    vira <NA> — e quem chama ABORTA (regra 1)."""
    out = pd.Series(pd.NA, index=s.index, dtype="string")
    if pd.api.types.is_datetime64_any_dtype(s):
        return s.dt.strftime("%Y-%m").astype("string")
    # 1) datetime ja parseado em coluna object (calamine devolve assim quando
    #    a celula tem formato de data)
    e_data = s.map(lambda v: isinstance(v, (pd.Timestamp,)) or
                   (hasattr(v, "year") and hasattr(v, "month")
                    and not isinstance(v, (int, float, str))))
    if e_data.any():
        out[e_data] = s[e_data].map(lambda v: f"{v.year:04d}-{v.month:02d}")
    resto = ~e_data
    if not resto.any():
        return out
    txt = s[resto].astype("string").str.strip()
    # 2) serial do Excel: so digitos (com ou sem ".0"), entre 1900 e 2100
    e_serial = txt.str.fullmatch(r"\d+(\.0+)?").fillna(False).astype(bool)
    serial = pd.to_numeric(txt.where(e_serial), errors="coerce")
    ok = serial.notna() & (serial >= 1) & (serial <= 80000)
    if ok.any():
        datas = _ORIGEM_EXCEL + pd.to_timedelta(serial[ok], unit="D")
        out[serial[ok].index] = datas.dt.strftime("%Y-%m").values
    # 3) texto AAAA-MM / AAAA/MM / AAAA/MMM (a mesma regra do sell-in)
    sobra = resto.copy()
    sobra[serial[ok].index] = False
    if sobra.any():
        out[sobra] = ano_mes(s[sobra])
    return out


def _ler_um(arq: Path) -> tuple[pd.DataFrame, dict]:
    aba = _MET.get("aba")
    try:
        df = pd.read_excel(arq, sheet_name=aba if aba is not None else 0,
                           engine="calamine")
    except Exception as e:                                   # noqa: BLE001
        abortar(f"arquivo REJEITADO: {arq.name}\n"
                f"  nao foi possivel ler a aba {aba!r}: {e}\n"
                f"  (config/config.yaml -> fontes.metas.aba)")
    df.columns = [" ".join(str(c).split()) for c in df.columns]
    obrig = list(_MET["colunas_obrigatorias"])
    faltando = [c for c in obrig if c not in df.columns]
    if faltando:
        abortar(f"arquivo REJEITADO: {arq.name}\n"
                f"  colunas obrigatorias ausentes: {faltando}\n"
                f"  colunas encontradas         : {list(df.columns)}")
    c_cod, c_cat, c_per, c_tipo, c_val = obrig[:5]

    # Linhas 100% vazias (rodape do Excel) nao sao dado.
    df = df.dropna(how="all").reset_index(drop=True)

    out = pd.DataFrame(index=df.index)
    out["COD_CLIENTE"] = digitos(df[c_cod])
    out["CATEGORIA"] = texto(df[c_cat])
    out["ANO_MES"] = ano_mes_periodo(df[c_per])
    out["TIPO"] = texto(df[c_tipo])
    out["VALOR"] = numero(df[c_val])

    # ---- validacoes que ABORTAM (regras 1-3) ---------------------------
    for col, origem in (("COD_CLIENTE", c_cod), ("CATEGORIA", c_cat),
                        ("ANO_MES", c_per), ("TIPO", c_tipo), ("VALOR", c_val)):
        ruins = out[col].isna()
        if ruins.any():
            crus = sorted(set(df.loc[ruins, origem].astype("string")
                              .fillna("(vazio)")))[:6]
            abortar(f"arquivo REJEITADO: {arq.name}\n"
                    f"  {int(ruins.sum()):,} linha(s) com '{origem}' vazio ou "
                    f"irreconhecivel — valores crus: {crus}\n"
                    "  A meta nao entra pela metade: corrija o arquivo.")

    tipos = {str(k).upper(): v for k, v in (_MET.get("tipos_meta") or {}).items()}
    desconhecidos = sorted(set(out["TIPO"]) - set(tipos))
    if desconhecidos:
        abortar(f"arquivo REJEITADO: {arq.name}\n"
                f"  'Tipo Meta' fora do mapa do config: {desconhecidos}\n"
                f"  aceitos: {sorted(tipos)} (config/config.yaml -> "
                "fontes.metas.tipos_meta)")
    out["METRICA"] = out["TIPO"].map(tipos)
    faltam = sorted(set(METRICAS) - set(out["METRICA"]))
    if faltam:
        abortar(f"arquivo REJEITADO: {arq.name}\n"
                f"  o arquivo nao traz nenhuma linha de {faltam}")

    chave = CHAVE + ["METRICA"]
    dup = out.duplicated(chave, keep=False)
    if dup.any():
        ex = out.loc[dup, chave].drop_duplicates().head(5).values.tolist()
        abortar(f"arquivo REJEITADO: {arq.name}\n"
                f"  {int(dup.sum()):,} linha(s) com a chave (mes, cliente, "
                f"categoria, tipo) REPETIDA — ex.: {ex}\n"
                "  Meta repetida somaria em dobro; o arquivo e que decide "
                "qual vale.")

    # ---- gabarito: soma BRUTA por mes e metrica, antes do pivo ----------
    bruto = (out.groupby(["ANO_MES", "METRICA"])["VALOR"].sum()
                .unstack("METRICA").reindex(columns=METRICAS))
    gabarito = {am: {m: float(bruto.at[am, m]) if pd.notna(bruto.at[am, m]) else 0.0
                     for m in METRICAS} for am in bruto.index}
    linhas_por_mes = out.groupby("ANO_MES").size().to_dict()

    largo = (out.pivot_table(index=CHAVE, columns="METRICA", values="VALOR",
                             aggfunc="sum")
                .reindex(columns=METRICAS).reset_index())
    largo.columns.name = None
    largo["ARQUIVO_ORIGEM"] = arq.name
    for c in CHAVE + ["ARQUIVO_ORIGEM"]:
        largo[c] = largo[c].astype("string")
    for m in METRICAS:
        largo[m] = largo[m].astype("float64")
    so_um = int(largo[METRICAS].isna().any(axis=1).sum())
    extra = {"gabarito": gabarito, "linhas": int(len(out)),
             "linhas_por_mes": {k: int(v) for k, v in linhas_por_mes.items()},
             "meses": sorted(gabarito), "pares_com_um_tipo_so": so_um}
    return largo[COLUNAS], extra


def _arquivos() -> list[Path]:
    pasta = caminho(_MET.get("pasta", "bases/Metas"))
    if not pasta.exists():
        return []
    achados: list[Path] = []
    for padrao in _MET.get("padroes_aceitos") or ["*.xlsx"]:
        achados += [p for p in pasta.glob(padrao)
                    if not p.name.startswith("~$")]
    return sorted(set(achados))


def ler() -> tuple[pd.DataFrame, dict, list[str]]:
    """Devolve (FATO_META larga, meta {arquivos, gabarito por mes}, avisos).
    Sem arquivo nenhum o pipeline SEGUE: o painel sai sem meta, com aviso —
    ausencia e ausencia, nunca zero."""
    avisos: list[str] = []
    if not _MET:
        return vazia(), {"arquivos": [], "gabarito": {}}, avisos
    arquivos = _arquivos()
    if not arquivos:
        msg = (f"base de metas ausente em {caminho(_MET.get('pasta', 'bases/Metas'))} "
               "— o painel sai SEM meta")
        if _MET.get("obrigatorio"):
            abortar(msg)
        log(msg, "aviso")
        return vazia(), {"arquivos": [], "gabarito": {}}, [msg]

    partes: list[pd.DataFrame] = []
    dono_do_mes: dict[str, str] = {}
    gabarito: dict[str, dict] = {}
    info_arquivos: list[dict] = []
    for arq in arquivos:
        try:
            d, extra = cache.ler(arq, _ler_um)
        except PermissionError:
            abortar(f"nao consegui abrir {arq.name}: o arquivo esta ABERTO em "
                    "outro programa (Excel?). Feche-o e rode de novo.")
        for am in extra["meses"]:
            if am in dono_do_mes:
                abortar(f"o mes {am} aparece em DOIS arquivos de metas: "
                        f"{dono_do_mes[am]} e {arq.name}\n"
                        "  Meta e substituida, nunca somada: deixe o mes em um "
                        "arquivo so.")
            dono_do_mes[am] = arq.name
            gabarito[am] = extra["gabarito"][am]
        if extra.get("pares_com_um_tipo_so"):
            msg = (f"{arq.name}: {extra['pares_com_um_tipo_so']:,} par(es) "
                   "cliente x categoria x mes com UM tipo de meta so (o outro "
                   "fica ausente, nao zero)")
            log(msg, "aviso")
            avisos.append(msg)
        info_arquivos.append({"arquivo": arq.name, "linhas": extra["linhas"],
                              "meses": extra["meses"]})
        partes.append(d)

    fm = pd.concat(partes, ignore_index=True) if partes else vazia()
    # ---- reconciliacao interna (regra 4): pivo x soma bruta, por mes ------
    for am, g in fm.groupby("ANO_MES"):
        for metrica, tol in (("META_RECEITA", float(_VAL["tolerancia_receita_reais"])),
                             ("META_PESO_KG", float(_VAL["tolerancia_peso_kg"]))):
            calc, esperado = float(g[metrica].sum()), gabarito[am][metrica]
            if abs(calc - esperado) > tol:
                abortar(f"metas {am}: {metrica} da FATO_META ({calc:,.2f}) "
                        f"difere da soma bruta do arquivo ({esperado:,.2f})")
    meses = sorted(gabarito)
    log(f"metas: {len(fm):,} pares cliente x categoria x mes · "
        f"{fm['COD_CLIENTE'].nunique():,} clientes · "
        f"{fm['CATEGORIA'].nunique()} categorias · meses {meses[0]} a "
        f"{meses[-1]} ({len(meses)}) em {len(arquivos)} arquivo(s)", "ok")
    for am in meses:
        log(f"  meta {am}: R$ {gabarito[am]['META_RECEITA']:,.2f} · "
            f"{gabarito[am]['META_PESO_KG'] / 1000:,.3f} t")
    return fm, {"arquivos": info_arquivos, "gabarito": gabarito}, avisos


def conferir_categorias(fm: pd.DataFrame, dim_produto: pd.DataFrame) -> None:
    """Q5-a (08/09/2026): categoria da meta que NAO existe no modelo ABORTA.
    Medido: 10 de 10 batem; uma grafia nova ("AMENDOIN") criaria uma
    categoria fantasma no painel se entrasse com aviso."""
    if fm.empty:
        return
    modelo = set(dim_produto["CATEGORIA"].dropna())
    fora = sorted(set(fm["CATEGORIA"]) - modelo)
    if fora:
        abortar(f"metas: {len(fora)} categoria(s) que nao existem no modelo: "
                f"{fora}\n  categorias do modelo: {sorted(modelo)}\n"
                "  Corrija a grafia no arquivo de metas (Q5-a: nao entra "
                "categoria nova por meta).")


def registrar_revisoes(fm_nova: pd.DataFrame, anterior: pd.DataFrame | None,
                       alvo: Path, execucao: str) -> tuple[list[dict], list[str]]:
    """Q3 (08/09/2026): a meta de um mes JA CARREGADO pode mudar; o arquivo
    atual e a verdade, e a mudanca fica REGISTRADA (append) em `alvo`.
    Compara a FATO_META nova com a gravada na execucao anterior, mes a mes:
    igual / alterado / novo / removido, com os totais e quantos pares
    mudaram. Devolve (linhas registradas, avisos)."""
    avisos: list[str] = []
    if anterior is None or anterior.empty:
        return [], avisos
    ant = anterior.set_index(CHAVE)[METRICAS].sort_index()
    nov = fm_nova.set_index(CHAVE)[METRICAS].sort_index()
    meses = sorted(set(ant.index.get_level_values(0))
                   | set(nov.index.get_level_values(0)))
    linhas: list[dict] = []
    for am in meses:
        a = ant.loc[am] if am in ant.index.get_level_values(0) else None
        n = nov.loc[am] if am in nov.index.get_level_values(0) else None
        if a is None:
            situacao, pares = "novo", int(len(n))
        elif n is None:
            situacao, pares = "removido", int(len(a))
        else:
            j = a.join(n, how="outer", lsuffix="_A", rsuffix="_N").fillna(0.0)
            dif = ((j["META_RECEITA_A"] - j["META_RECEITA_N"]).abs() > 0.005) \
                | ((j["META_PESO_KG_A"] - j["META_PESO_KG_N"]).abs() > 0.0005)
            pares = int(dif.sum())
            situacao = "alterado" if pares else "igual"
        if situacao == "igual":
            continue
        linha = {
            "execucao": execucao,
            "registrado_em": pd.Timestamp.now().strftime("%d/%m/%Y %H:%M"),
            "ANO_MES": am, "situacao": situacao, "pares_alterados": pares,
            "receita_anterior": round(float(a["META_RECEITA"].sum()), 2) if a is not None else None,
            "receita_nova": round(float(n["META_RECEITA"].sum()), 2) if n is not None else None,
            "peso_kg_anterior": round(float(a["META_PESO_KG"].sum()), 3) if a is not None else None,
            "peso_kg_novo": round(float(n["META_PESO_KG"].sum()), 3) if n is not None else None,
        }
        linhas.append(linha)
        if situacao != "novo":
            msg = (f"metas {am}: {situacao.upper()} em relacao a execucao "
                   f"anterior ({pares:,} par(es); R$ "
                   f"{linha['receita_anterior'] or 0:,.2f} -> "
                   f"R$ {linha['receita_nova'] or 0:,.2f}) — registrado em "
                   f"{alvo.name}")
            log(msg, "aviso")
            avisos.append(msg)
    if linhas:
        df = pd.DataFrame(linhas)
        alvo.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(alvo, mode="a", index=False, header=not alvo.exists(),
                  encoding="utf-8-sig", sep=";", decimal=",")
    return linhas, avisos
