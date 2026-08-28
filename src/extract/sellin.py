# -*- coding: utf-8 -*-
"""Leitura da fonte de Sell In (camada bronze).

Devolve o dado CRU, já tipado e com nome de coluna normalizado, SEM nenhuma regra
de negócio. Juntar, deduplicar e decidir precedência é trabalho das dimensões e
da fato — não daqui.

Três coisas acontecem aqui e em nenhum outro lugar:

1. **O rodapé sai.** Cada arquivo traz uma linha `Total` e duas de
   `Filtros aplicados`. Somar sem tirar dobra o arquivo.
2. **A linha `Total` vira gabarito.** É contra ela que o passo de reconciliação
   prova que não perdemos nem inventamos linha.
3. **O texto do filtro é guardado.** É ele que denuncia, no mês seguinte, que
   alguém reextraiu com outro recorte e o universo mudou em silêncio.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from ..utils.config import CFG, caminho
from ..utils.log import abortar, log
from ..utils.texto import ano_mes, digitos, numero, texto
from . import cache

FONTE = CFG["fontes"]["sellin"]

# Como cada coluna de origem vira coluna do modelo. O nome de ORIGEM está no
# config; o nome de DESTINO é contrato interno e mora aqui.
DESTINO = {
    "Ano mês": ("ANO_MES", ano_mes),
    "Cód. cliente": ("COD_CLIENTE", digitos),
    "Cliente": ("NOME_CLIENTE", texto),
    "Bandeira cliente": ("BANDEIRA", texto),
    "Estado": ("UF", texto),
    "Desc. categoria": ("CATEGORIA_SELLIN", texto),
    "Cód. material": ("COD_PRODUTO", digitos),
    "Desc. material sem código": ("DESCRICAO_SELLIN", texto),
    "Receita Líquida": ("RECEITA", numero),
    "Peso Líquido": ("PESO_KG", numero),
    "Qtde Faturado": ("CAIXAS", numero),
    "Subcanal": ("SUBCANAL", texto),          # GAP-01 — entra sozinha se existir
    "Representante": ("REPRESENTANTE", texto),
}


def _num_rodape(v) -> float | None:
    """Número da linha `Total`, com a mesma tolerância de `numero()`.

    Auditoria, A5: o `float()` cru estourava traceback em texto pt-BR e deixava
    célula vazia virar NaN — e `abs(nan) > tol` é False, ou seja, a checagem
    mais importante do pipeline passava DE MÃO VAZIA. Vazio/ilegível agora vira
    None, que a reconciliação trata como "gabarito ausente" COM AVISO.
    """
    n = numero(pd.Series([v]))
    return float(n.iloc[0]) if pd.notna(n.iloc[0]) else None


def arquivos() -> list[Path]:
    """Todos os arquivos de entrada, das duas pastas declaradas no config."""
    achados: list[Path] = []
    tentadas = []
    for pasta in FONTE["pastas"]:
        p = caminho(pasta)
        tentadas.append((p, p.exists()))
        if not p.exists():
            continue
        for padrao in FONTE["padroes_aceitos"]:
            achados += [a for a in p.glob(padrao) if not a.name.startswith("~$")]

    if not achados:
        # A mensagem tem de dizer ONDE se procurou. Caminho fixo na mensagem de
        # erro manda o operador procurar no lugar errado.
        det = "\n".join(f"    {p}  ({'existe' if ok else 'NAO EXISTE'})"
                        for p, ok in tentadas)
        abortar("nenhum arquivo de Sell In encontrado.\n"
                f"  pastas procuradas:\n{det}\n"
                f"  padroes aceitos  : {FONTE['padroes_aceitos']}\n"
                "  (config/config.yaml -> fontes.sellin.pastas)")
    return sorted(set(achados))


def _validar_schema(df: pd.DataFrame, arq: Path) -> None:
    """Impede ingestão silenciosa de arquivo incompatível."""
    faltando = [c for c in FONTE["colunas_obrigatorias"] if c not in df.columns]
    if faltando:
        abortar(f"arquivo REJEITADO: {arq.name}\n"
                f"  colunas obrigatorias ausentes: {faltando}\n"
                f"  colunas encontradas         : {list(df.columns)}\n"
                "  (config/config.yaml -> fontes.sellin.colunas_obrigatorias)")


def _ler_um(arq: Path) -> tuple[pd.DataFrame, dict]:
    try:
        df = pd.read_excel(arq, sheet_name=FONTE["aba"], engine="calamine")
    except Exception as e:                                   # noqa: BLE001
        abortar(f"arquivo REJEITADO: {arq.name}\n"
                f"  nao foi possivel ler a aba '{FONTE['aba']}': {e}")
    df.columns = [str(c).strip() for c in df.columns]
    _validar_schema(df, arq)

    ano_txt = df["Ano"].astype("string").str.strip()
    rotulo = str(FONTE.get("rotulo_linha_total", "total")).casefold()

    extra: dict = {}
    if FONTE.get("ultima_linha_e_total"):
        tot = df[ano_txt.str.casefold() == rotulo]
        if len(tot):
            t = tot.iloc[0]
            extra["gabarito"] = {
                "receita": _num_rodape(t["Receita Líquida"]),
                "peso_kg": _num_rodape(t["Peso Líquido"]),
                "caixas": _num_rodape(t["Qtde Faturado"]),
            }

    # C8 (auditoria): o texto do filtro comeca na linha "Filtros aplicados".
    # Capturar QUALQUER linha de rodape faria um rotulo de Total desconhecido
    # (ex.: "Total geral") virar "filtro" — e todo mes novo acusaria falso
    # recorte divergente, o aviso que sempre aparece e ninguem le mais.
    rodape = df.loc[df["Ano mês"].isna() & ano_txt.notna()
                    & (ano_txt.str.casefold() != rotulo), "Ano"]
    txts = [str(x).strip() for x in rodape]
    ini = next((i for i, tx in enumerate(txts)
                if tx.casefold().startswith("filtros aplicados")), None)
    if ini is not None:
        extra["filtro"] = "\n".join(txts[ini:])
    elif txts:
        log(f"{arq.name}: rodape sem a linha 'Filtros aplicados' — "
            f"{len(txts)} linha(s) de rodape ignoradas (1a: {txts[0][:60]})",
            "aviso")

    # Fica só o corpo: linha sem `Ano mês` é rodapé.
    corpo = df[df["Ano mês"].notna() & (ano_txt.str.casefold() != rotulo)]

    out = pd.DataFrame(index=corpo.index)
    for origem, (destino, conv) in DESTINO.items():
        if origem in corpo.columns:
            out[destino] = conv(corpo[origem])

    out["ARQUIVO_ORIGEM"] = arq.name

    # A9: linha de DADO com `Ano mês` não reconhecido não pode sumir no dropna
    # — mês errado ou formato novo entraria (ou sumiria) em silêncio.
    mal = out["ANO_MES"].isna()
    if mal.any():
        exemplos = sorted(set(corpo.loc[mal, "Ano mês"].astype(str)))[:5]
        abortar(f"arquivo REJEITADO: {arq.name}\n"
                f"  {int(mal.sum())} linha(s) com 'Ano mês' nao reconhecido. "
                f"Exemplos: {exemplos}\n"
                "  Formatos aceitos: AAAA/MM, AAAA-MM e AAAA/MMM (ex.: 2026/08).\n"
                "  Se a extracao mudou de formato, peca a reextracao no layout "
                "padrao — o pipeline nao adivinha mes.")
    # C7 (auditoria): descarte de linha de dado nao pode ser mudo — celula
    # mesclada em Cod. cliente/material sumiria sem contagem, e com receita
    # nula nem o gabarito reclamaria.
    perdidas = out["COD_CLIENTE"].isna() | out["COD_PRODUTO"].isna()
    if perdidas.any():
        log(f"{arq.name}: {int(perdidas.sum())} linha(s) de dado sem "
            f"Cod. cliente/material, descartadas — receita descartada "
            f"R$ {out.loc[perdidas, 'RECEITA'].sum():,.2f}", "aviso")
    out = out.dropna(subset=["ANO_MES", "COD_CLIENTE", "COD_PRODUTO"])
    return out.reset_index(drop=True), extra


_RE_CLAUSULA_MES = re.compile(r"\|?\s*Ano m[êe]s [ée][^|]*", re.IGNORECASE)


def _assinatura_filtro(txt: str) -> str:
    """Assinatura do filtro SEM a cláusula do mês.

    `Ano mês é 2025/07` muda em todo arquivo por construção; deixá-la dentro
    faria todo mês parecer um recorte diferente, e aviso que sempre aparece
    ninguém lê mais.
    """
    limpo = _RE_CLAUSULA_MES.sub("", txt.replace("\n", " | "))
    limpo = re.sub(r"\s+", " ", limpo).strip(" |")
    return limpo.casefold()


def ler() -> tuple[pd.DataFrame, dict]:
    """Consolida todos os arquivos. Devolve (dados, metadados de linhagem)."""
    arqs = arquivos()
    log(f"{len(arqs)} arquivo(s) de Sell In encontrado(s)")

    partes, gabaritos, filtros, meses_por_arq = [], {}, {}, {}
    declaradas = FONTE.get("colunas_opcionais") or []
    # C4 (auditoria): opcional declarada no config sem destino no leitor era
    # documentacao mentindo — parecia ingerida e nao era.
    sem_destino = [c for c in declaradas if c not in DESTINO]
    if sem_destino:
        log(f"coluna(s) opcionais declaradas no config SEM destino no leitor — "
            f"NAO serao ingeridas: {sem_destino}. Ajuste "
            "`fontes.sellin.colunas_opcionais` ou o DESTINO em sellin.py",
            "aviso")
    opcionais = [(c, DESTINO[c][0]) for c in declaradas if c in DESTINO]
    presenca: dict[str, list[bool]] = {origem: [] for origem, _ in opcionais}
    for a in arqs:
        d, extra = cache.ler(a, _ler_um)
        partes.append(d)
        if extra.get("filtro"):
            filtros[a.name] = extra["filtro"]
        if extra.get("gabarito"):
            gabaritos[a.name] = extra["gabarito"]
        meses_por_arq[a.name] = sorted(d["ANO_MES"].dropna().unique())
        for origem, destino in opcionais:
            presenca[origem].append(destino in d.columns)

    # A12: opcional que some da extração nova derruba um eixo do painel de um
    # mês para o outro — isso não pode acontecer em silêncio absoluto.
    for origem, _ in opcionais:
        n_com = sum(presenca[origem])
        if n_com == 0:
            log(f"coluna opcional '{origem}': ausente nos {len(arqs)} arquivos "
                "(segue fora do modelo)")
        elif n_com == len(arqs):
            log(f"coluna opcional '{origem}': presente nos {len(arqs)} arquivos", "ok")
        else:
            sem = [a.name for a, tem in zip(arqs, presenca[origem]) if not tem]
            log(f"coluna opcional '{origem}': presente em {n_com} de {len(arqs)} "
                f"arquivo(s) — AUSENTE em {', '.join(sem[:5])}"
                + (f" (+{len(sem) - 5})" if len(sem) > 5 else "")
                + ". Se a extracao mudou, esse eixo some do painel nesses meses.",
                "aviso")

    df = pd.concat(partes, ignore_index=True)

    meta = {
        "arquivos": [a.name for a in arqs],
        "gabaritos": gabaritos,
        "filtros": filtros,
        "meses_por_arquivo": meses_por_arq,
        "tem_subcanal": "SUBCANAL" in df.columns,
    }
    if meta["tem_subcanal"]:
        log("a extracao traz a coluna `Subcanal` — GAP-01 resolvido na origem", "ok")
    return df, meta


def conferir_filtro_extracao(meta: dict) -> list[str]:
    """O recorte da extração vive DENTRO do arquivo, não no config.

    Dois casos de filtro diferente, e só um é problema:

    1. Mês partido em `p1`/`p2` — os pedaços têm filtros COMPLEMENTARES (um
       exclui um conjunto de gerentes, o outro exclui o resto) e juntos formam o
       mês inteiro. É o esperado, e a reconciliação contra a SOMA dos gabaritos
       já prova que fecha.
    2. Meses INTEIROS com filtros diferentes entre si — aí o recorte mudou no
       meio da série e os meses deixaram de ser comparáveis.

    Só o caso 2 vira aviso.
    """
    achados: list[str] = []
    filtros = meta["filtros"]
    if not filtros:
        log("arquivos sem texto de filtro — conferencia de recorte nao executada",
            "aviso")
        return ["sem texto de filtro nos arquivos de origem"]

    partes_por_mes: dict[str, list[str]] = {}
    for arq, meses in meta["meses_por_arquivo"].items():
        for m in meses:
            partes_por_mes.setdefault(m, []).append(arq)

    inteiros = {m: a[0] for m, a in partes_por_mes.items() if len(a) == 1}
    partidos = {m: a for m, a in partes_por_mes.items() if len(a) > 1}

    assinaturas: dict[str, list[str]] = {}
    for mes, arq in sorted(inteiros.items()):
        if arq in filtros:
            assinaturas.setdefault(_assinatura_filtro(filtros[arq]), []).append(mes)

    if len(assinaturas) > 1:
        msg = (f"{len(assinaturas)} recortes de extracao DIFERENTES entre meses "
               "inteiros — a serie deixa de ser comparavel")
        log(msg, "aviso")
        achados.append(msg)
        for i, (ass, meses) in enumerate(assinaturas.items(), 1):
            log(f"  recorte {i}: {len(meses)} mes(es), {meses[0]} a {meses[-1]}: "
                f"{ass[:180]}", "aviso")
    elif assinaturas:
        log(f"recorte de extracao identico nos {len(inteiros)} meses inteiros", "ok")

    # A3: partes complementares têm filtros DIFERENTES por construção (cada
    # uma exclui um conjunto de gerentes). Duas partes do mesmo mês com o MESMO
    # recorte são quase sempre uma cópia duplicada — a cópia de conflito do
    # OneDrive (`... - Copia.xlsx`, `...-DESKTOP-XYZ.xlsx`) é o caso real. Cada
    # cópia carrega o próprio gabarito, então a reconciliação por arquivo FECHA
    # e a receita do mês DOBRARIA no painel. Abortar é a única resposta.
    for mes, arqs_mes in sorted(partidos.items()):
        por_assinatura: dict[str, list[str]] = {}
        for arq in arqs_mes:
            if arq in filtros:
                por_assinatura.setdefault(
                    _assinatura_filtro(filtros[arq]), []).append(arq)
        for iguais in por_assinatura.values():
            if len(iguais) > 1:
                abortar(
                    f"o mes {mes} esta partido em {len(arqs_mes)} arquivo(s) e "
                    f"{len(iguais)} deles tem o MESMO recorte de extracao:\n"
                    + "\n".join(f"    {a}" for a in sorted(iguais)) + "\n"
                    "  Partes complementares tem filtros diferentes por "
                    "construcao. Recorte identico e copia duplicada — ex.: "
                    "copia de conflito do OneDrive, ou o mesmo arquivo nas "
                    "duas pastas de entrada. Apague a copia e rode de novo.")

    if partidos:
        log(f"{len(partidos)} mes(es) partidos em mais de um arquivo "
            f"({', '.join(sorted(partidos))}) — filtros complementares, "
            "conferidos contra a SOMA dos gabaritos", "ok")
    return achados
