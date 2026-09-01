# -*- coding: utf-8 -*-
"""Leitura da base de metas FY 26/27 (D-43) -> FATO_META.

O arquivo vem do Comercial DO JEITO QUE ELE E (regra da pasta `bases/Metas`):
cabecalho fora da linha 1, rotulo do indicador numa linha e o mes na outra,
linhas "Total" no meio dos dados. E o leitor que se adapta — em um lugar so.

Tres regras deste leitor, todas medidas em 01/09/2026:

1. **Competencia vem do CONTEUDO**: o rotulo da coluna ("SET'26") vira
   `ANO_MES` ("2026-09"). Rotulo que nao casar com MMM'AA ABORTA — mes
   inventado por posicao foi um defeito real do projeto anterior (A9).
2. **A linha total geral e o GABARITO**: a soma do detalhe tem de bater com
   ela nas duas metricas (mesmas tolerancias do sell-in), senao ABORTA —
   arquivo que nao reconcilia consigo mesmo nao entra.
3. **`CÓD. BANDEIRA 2` so e fusao quando e DIGITO PURO e diferente do 1**
   (D-43): "Ok" e autorreferencia nao sao fusao; os baldes usam o campo como
   chave interna `codigo_categoria` (ex.: "201_AMENDOIM") e tambem nao sao.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from ..utils.config import CFG, caminho
from ..utils.log import abortar, log
from ..utils.texto import digitos, texto
from . import cache

_MET = CFG["fontes"]["metas"]
_VAL = CFG["validacao"]

_MESES_PT = {"JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
             "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12}
_RE_MES = re.compile(r"^([A-Z]{3})'(\d{2})$")

# Colunas fixas do arquivo -> colunas da FATO_META. O que nao esta aqui NAO e
# ingerido (N4, nomes por extenso dos niveis, CLIENTE ATIVO): o join com o
# realizado e por codigo, e os rotulos oficiais moram na Hierarquia_Consolidada.
_FIXAS = {
    "CÓDIGO HEAD": "COD_HEAD",
    "HEAD": "HEAD_META",
    "CLUSTER": "CLUSTER",
    "CLIENTE": "BANDEIRA_META",
    "CÓD. BANDEIRA 1": "COD_BANDEIRA",
    "CÓD. BANDEIRA 2": "COD_BANDEIRA_2",
    "CATEGORIA": "CATEGORIA",
    "(N2) CÓDIGO GERENTE": "COD_GERENTE",
    "(N3) CÓDIGO SUP./EXEC.": "COD_SUPERVISOR",
    "STATUS VÍNCULO": "STATUS_VINCULO",
}

_COLS_SAIDA = ["ANO_MES", "COD_HEAD", "HEAD_META", "CLUSTER", "BANDEIRA_META",
               "COD_BANDEIRA", "COD_BANDEIRA_2", "CATEGORIA", "COD_GERENTE",
               "COD_SUPERVISOR", "STATUS_VINCULO",
               "META_RECEITA", "META_PESO_KG", "ARQUIVO_ORIGEM"]

_CHAVE_GRAO = ["ANO_MES", "COD_HEAD", "BANDEIRA_META", "COD_BANDEIRA",
               "CATEGORIA"]


def _norm(v) -> str:
    return " ".join(str(v).split()) if v is not None and v == v else ""


def ano_mes_de_rotulo(rotulo: str) -> str | None:
    """`SET'26` -> `2026-09`. Devolve None para o que nao casar — quem chama
    decide se aborta (coluna de mes) ou ignora (coluna qualquer)."""
    m = _RE_MES.match(_norm(rotulo).upper())
    if not m:
        return None
    mes = _MESES_PT.get(m.group(1))
    if not mes:
        return None
    return f"20{m.group(2)}-{mes:02d}"


def _cod_bandeira_2(bruto: pd.Series, cod1: pd.Series) -> pd.Series:
    """Regra 3 do modulo: fusao = digito puro E diferente do COD_BANDEIRA."""
    t = texto(bruto)
    puro = t.str.fullmatch(r"\d+(\.0)?").fillna(False)
    cod2 = digitos(t.where(puro))
    return cod2.where(cod2 != cod1)


def _achar_cabecalho(bruto: pd.DataFrame) -> int:
    for i in range(min(len(bruto), 20)):
        vals = {_norm(v).upper() for v in bruto.iloc[i]}
        if "CLIENTE" in vals and "CATEGORIA" in vals:
            return i
    abortar(f"arquivo REJEITADO: {_MET['arquivo']}\n"
            "  nenhuma linha das 20 primeiras tem os cabecalhos CLIENTE e "
            "CATEGORIA\n  (config/config.yaml -> fontes.metas.aba)")
    return -1  # inalcancavel


def _estruturar(bruto: pd.DataFrame, nome_arquivo: str) -> tuple[pd.DataFrame, dict]:
    """Do grid cru (header=None) para a FATO_META longa + gabarito no extra."""
    hdr = _achar_cabecalho(bruto)
    nomes = [_norm(v) for v in bruto.iloc[hdr]]
    acima = ([_norm(v) for v in bruto.iloc[hdr - 1]] if hdr > 0
             else [""] * len(nomes))

    faltando = [c for c in _MET["colunas_obrigatorias"] if c not in nomes]
    if faltando:
        abortar(f"arquivo REJEITADO: {nome_arquivo}\n"
                f"  colunas obrigatorias ausentes: {faltando}\n"
                f"  colunas encontradas         : {[n for n in nomes if n]}")

    # ---- colunas de mes: par (indicador na linha de cima, mes no cabecalho)
    meses: dict[str, dict[str, int]] = {}       # ANO_MES -> {metrica: coluna}
    for j, nome in enumerate(nomes):
        am = ano_mes_de_rotulo(nome)
        if am is None:
            continue
        ind = acima[j].upper()
        if "KG" in ind:
            metrica = "META_PESO_KG"
        elif "R$" in ind or "RL" in ind:
            metrica = "META_RECEITA"
        else:
            abortar(f"arquivo REJEITADO: {nome_arquivo}\n"
                    f"  coluna de mes '{nome}' sem indicador reconhecivel na "
                    f"linha acima (achei '{acima[j]}'; esperado algo com 'kg' "
                    "ou 'R$')")
        if metrica in meses.setdefault(am, {}):
            abortar(f"arquivo REJEITADO: {nome_arquivo}\n"
                    f"  duas colunas de {metrica} para o mes {am}")
        meses[am][metrica] = j
    if not meses:
        abortar(f"arquivo REJEITADO: {nome_arquivo}\n"
                "  nenhuma coluna de mes no formato MMM'AA no cabecalho")
    incompletos = [am for am, m in meses.items() if len(m) < 2]
    if incompletos:
        abortar(f"arquivo REJEITADO: {nome_arquivo}\n"
                f"  mes(es) sem o PAR kg + R$: {sorted(incompletos)}")

    dados = bruto.iloc[hdr + 1:].reset_index(drop=True)
    col_head = nomes.index("CÓDIGO HEAD")
    rot_head = dados[dados.columns[col_head]].map(_norm)
    e_total = rot_head.str.upper() == "TOTAL"
    vazia = dados.apply(lambda r: all(_norm(v) == "" for v in r), axis=1)

    # ---- gabarito: a linha total GERAL (CATEGORIA tambem "Total") ----------
    col_cat = nomes.index("CATEGORIA")
    geral = e_total & (dados[dados.columns[col_cat]].map(_norm).str.upper()
                       == "TOTAL")
    if int(geral.sum()) != 1:
        abortar(f"arquivo REJEITADO: {nome_arquivo}\n"
                f"  esperava exatamente 1 linha total geral (todas as colunas "
                f"'Total'), achei {int(geral.sum())}")
    linha_g = dados[geral].iloc[0]
    gabarito = {am: {met: float(pd.to_numeric(linha_g.iloc[j]))
                     for met, j in cols.items()}
                for am, cols in meses.items()}

    detalhe = dados[~e_total & ~vazia]
    fixas = pd.DataFrame(index=detalhe.index)
    for origem, destino in _FIXAS.items():
        fixas[destino] = detalhe[detalhe.columns[nomes.index(origem)]]

    # ---- normalizacao (formato, nunca grafia) ------------------------------
    out_fixas = pd.DataFrame(index=fixas.index)
    out_fixas["COD_HEAD"] = digitos(fixas["COD_HEAD"])
    out_fixas["HEAD_META"] = texto(fixas["HEAD_META"])
    out_fixas["CLUSTER"] = texto(fixas["CLUSTER"])
    out_fixas["BANDEIRA_META"] = texto(fixas["BANDEIRA_META"])
    out_fixas["COD_BANDEIRA"] = digitos(fixas["COD_BANDEIRA"])
    out_fixas["COD_BANDEIRA_2"] = _cod_bandeira_2(fixas["COD_BANDEIRA_2"],
                                                  out_fixas["COD_BANDEIRA"])
    out_fixas["CATEGORIA"] = texto(fixas["CATEGORIA"])
    out_fixas["COD_GERENTE"] = digitos(fixas["COD_GERENTE"])
    out_fixas["COD_SUPERVISOR"] = digitos(fixas["COD_SUPERVISOR"])
    out_fixas["STATUS_VINCULO"] = texto(fixas["STATUS_VINCULO"])

    sem_chave = (out_fixas["COD_HEAD"].isna()
                 | out_fixas["BANDEIRA_META"].isna()
                 | out_fixas["CATEGORIA"].isna())
    if sem_chave.any():
        log(f"metas: {int(sem_chave.sum())} linha(s) sem head/bandeira/"
            "categoria aproveitavel, descartadas", "aviso")
        out_fixas = out_fixas[~sem_chave]
        detalhe = detalhe[~sem_chave]

    # ---- melt: um registro por mes -----------------------------------------
    partes = []
    for am in sorted(meses):
        p = out_fixas.copy()
        p.insert(0, "ANO_MES", am)
        for met, j in meses[am].items():
            p[met] = pd.to_numeric(detalhe[detalhe.columns[j]], errors="coerce")
        partes.append(p)
    df = pd.concat(partes, ignore_index=True)
    df["ARQUIVO_ORIGEM"] = nome_arquivo
    return df[_COLS_SAIDA], {"gabarito": gabarito}


def _ler_metas(arq: Path) -> tuple[pd.DataFrame, dict]:
    try:
        bruto = pd.read_excel(arq, sheet_name=_MET["aba"], engine="calamine",
                              header=None)
    except Exception as e:                                    # noqa: BLE001
        abortar(f"arquivo REJEITADO: {arq.name}\n"
                f"  nao foi possivel ler a aba '{_MET['aba']}': {e}\n"
                "  (config/config.yaml -> fontes.metas.aba)")
    return _estruturar(bruto, arq.name)


def _reconciliar(df: pd.DataFrame, gabarito: dict, nome_arquivo: str) -> None:
    tol = {"META_RECEITA": float(_VAL["tolerancia_receita_reais"]),
           "META_PESO_KG": float(_VAL["tolerancia_peso_kg"])}
    ruins = []
    for am, metas_mes in gabarito.items():
        recorte = df[df["ANO_MES"] == am]
        for met, esperado in metas_mes.items():
            soma = float(recorte[met].sum())
            if abs(soma - esperado) > tol[met]:
                ruins.append(f"{am} [{met}]: detalhe {soma:,.4f} x linha "
                             f"Total {esperado:,.4f} (dif {soma - esperado:,.4f})")
    if ruins:
        abortar(f"a FATO_META nao bate com a linha 'Total' de {nome_arquivo}:"
                "\n  " + "\n  ".join(ruins))


def ler() -> tuple[pd.DataFrame, list[str]]:
    """Devolve (FATO_META, avisos). Ausencia do arquivo NAO derruba o pipeline:
    meta ausente aparece como ausente no painel — nunca como zero."""
    avisos: list[str] = []
    vazia = pd.DataFrame(columns=_COLS_SAIDA)
    arq = caminho(_MET["arquivo"])
    if not arq.exists():
        msg = (f"base de metas ausente ({arq.name}) — o painel fica sem a "
               "visao de meta")
        if _MET.get("obrigatorio"):
            abortar(msg)
        log(msg, "aviso")
        return vazia, [msg]

    df, extra = cache.ler(arq, _ler_metas)

    # grao: 1 linha por mes x head x bandeira x categoria — duplicidade aqui
    # dobraria a meta em silencio no join, entao ABORTA (mesma regra da fato).
    dup = df.duplicated(subset=_CHAVE_GRAO)
    if dup.any():
        exemplos = df.loc[dup, _CHAVE_GRAO].head(3).values.tolist()
        abortar(f"{int(dup.sum())} linha(s) de meta fora do grao "
                f"{' x '.join(_CHAVE_GRAO)}.\n  Exemplos: {exemplos}")

    _reconciliar(df, extra["gabarito"], arq.name)

    negativas = int(((df["META_RECEITA"] < 0) | (df["META_PESO_KG"] < 0)).sum())
    if negativas:
        msg = f"{negativas} linha(s) de meta com valor NEGATIVO — confira a origem"
        log(msg, "aviso")
        avisos.append(msg)

    for am in sorted(df["ANO_MES"].unique()):
        r = df[df["ANO_MES"] == am]
        log(f"meta {am}: {len(r):,} linhas · R$ {r['META_RECEITA'].sum():,.2f} "
            f"· {r['META_PESO_KG'].sum() / 1000:,.1f} t · "
            f"{r['COD_HEAD'].nunique()} heads · "
            f"{r['BANDEIRA_META'].nunique()} bandeiras (reconciliada com a "
            "linha Total)", "ok")
    return df, avisos


def conferir_cobertura(fato_meta: pd.DataFrame,
                       dim_cliente: pd.DataFrame) -> list[str]:
    """Quanto da meta encontra par no realizado — por CODIGO primeiro (D-42),
    nome como fallback. So MEDE e RELATA; o join de verdade e da fase dos
    visuais. Nao aborta: meta sem par e lacuna de cadastro, nao defeito."""
    if fato_meta.empty:
        return []
    cods = set(dim_cliente["COD_BANDEIRA"].dropna())
    nomes = set(dim_cliente["BANDEIRA"].dropna())
    por_cod = (fato_meta["COD_BANDEIRA"].isin(cods)
               | fato_meta["COD_BANDEIRA_2"].isin(cods))
    por_nome = ~por_cod & fato_meta["BANDEIRA_META"].isin(nomes)
    rl = fato_meta["META_RECEITA"].sum()
    p_cod = fato_meta.loc[por_cod, "META_RECEITA"].sum() / rl if rl else 0.0
    p_nome = fato_meta.loc[por_nome, "META_RECEITA"].sum() / rl if rl else 0.0
    sem = fato_meta[~por_cod & ~por_nome]
    msg = (f"cobertura da meta sobre o realizado: {p_cod:.1%} do R$ casa por "
           f"CODIGO de bandeira + {p_nome:.1%} por nome; sem par: "
           f"{1 - p_cod - p_nome:.1%} em {sem['BANDEIRA_META'].nunique()} "
           "bandeira(s)")
    log(msg, "ok")
    avisos = [msg]
    if len(sem):
        maiores = (sem.groupby("BANDEIRA_META")["META_RECEITA"].sum()
                      .sort_values(ascending=False).head(5))
        detalhe = " · ".join(f"{b} (R$ {v:,.0f})" for b, v in maiores.items())
        log(f"meta sem par (maiores): {detalhe}", "aviso")
        avisos.append(f"meta sem par (maiores): {detalhe}")
    return avisos
