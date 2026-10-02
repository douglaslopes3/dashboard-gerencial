# -*- coding: utf-8 -*-
"""FATO_SELLIN e as conferências que travam a publicação.

GRÃO DECLARADO
--------------
Uma linha representa: **o faturamento líquido de um SKU para um cliente em um
mês de competência.** Chave: `ANO_MES × COD_CLIENTE × COD_PRODUTO`.

Não é presunção: medido em 3.085.119 linhas e 24 meses, zero duplicidade nessa
chave. O ETL não agrega e não desagrega.

CAIXAS PERMITE NULO, DE PROPÓSITO
---------------------------------
2,46% das linhas não têm `Qtde Faturado` na fonte — quase todas devoluções.
Preencher com zero somaria uma caixa que não existe e apagaria a diferença entre
"zero caixas" e "a fonte não informou".
"""
from __future__ import annotations

import pandas as pd

from ..utils.config import CFG
from ..utils.log import EXECUCAO_ID, INICIO, abortar, log

_TOL = CFG["validacao"]

COLUNAS = ["ANO_MES", "COD_CLIENTE", "COD_PRODUTO",
           "RECEITA", "PESO_KG", "CAIXAS",
           "ARQUIVO_ORIGEM", "EXECUCAO_ID", "PROCESSADO_EM"]

GRAO = ["ANO_MES", "COD_CLIENTE", "COD_PRODUTO"]


def construir(sellin: pd.DataFrame) -> pd.DataFrame:
    f = pd.DataFrame({
        "ANO_MES": sellin["ANO_MES"].astype("string"),
        "COD_CLIENTE": sellin["COD_CLIENTE"].astype("string"),
        "COD_PRODUTO": sellin["COD_PRODUTO"].astype("string"),
        "RECEITA": sellin["RECEITA"].astype("float64").fillna(0.0),
        "PESO_KG": sellin["PESO_KG"].astype("float64").fillna(0.0),
        "CAIXAS": sellin["CAIXAS"].astype("float64"),      # nulo preservado
        "ARQUIVO_ORIGEM": sellin["ARQUIVO_ORIGEM"].astype("string"),
    })
    f["EXECUCAO_ID"] = EXECUCAO_ID
    f["PROCESSADO_EM"] = pd.Timestamp(INICIO)
    # B3 (auditoria): as colunas de linhagem tem 28 e 1 valores distintos para
    # 3 Mi de linhas — como `category` a fato cai de 418 para 247 MB em RAM.
    # No Parquet nada muda (as strings ja saem dictionary-encoded).
    f["ARQUIVO_ORIGEM"] = f["ARQUIVO_ORIGEM"].astype("category")
    f["EXECUCAO_ID"] = f["EXECUCAO_ID"].astype("category")
    return f[COLUNAS]


def conferir_grao(f: pd.DataFrame) -> list[str]:
    """Duplicidade no grão. A regra é DECLARADA: dentro do mesmo arquivo é erro
    (o grão da fonte se sustenta); entre arquivos diferentes do mesmo mês seria
    reextração duplicada — também erro."""
    dup = int(f.duplicated(GRAO).sum())
    if not dup:
        log(f"grao {' x '.join(GRAO)}: zero duplicados em {len(f):,} linhas", "ok")
        return []

    # O cast para "string" vem ANTES do groupby: com ARQUIVO_ORIGEM em
    # category (B3), o pandas 3 tenta reconverter o resultado do agg de volta
    # para o dtype categorico da coluna de origem e estoura em lista.
    dup_df = f[f.duplicated(GRAO, keep=False)]
    amostra = (dup_df.assign(_ARQ=dup_df["ARQUIVO_ORIGEM"].astype("string"))
               .groupby(GRAO)["_ARQ"]
               .agg(lambda s: sorted(set(s))).head(5))
    abortar(f"{dup:,} linha(s) fora do grao declarado.\n"
            "  O grao da fonte e ANO_MES x COD_CLIENTE x COD_PRODUTO e foi medido\n"
            "  como unico em 24 meses. Duplicidade aqui significa arquivo\n"
            "  reextraido ou mes duplicado na pasta de entrada.\n"
            f"  Exemplos (chave -> arquivos):\n"
            + "\n".join(f"    {k} -> {v}" for k, v in amostra.items()))
    return []


def contar_orfaos(f: pd.DataFrame, dim: pd.DataFrame, coluna: str) -> int:
    """Linhas da fato cuja chave nao existe na dimensao.

    C5 (auditoria): esta e A definicao de orfao — o relatorio de qualidade usa
    esta funcao em vez de reconstruir o `set`+`isin` por conta propria, para as
    duas medicoes nunca divergirem.
    """
    return int((~f[coluna].isin(set(dim[coluna].dropna()))).sum())


def conferir_integridade(f: pd.DataFrame, dim_cliente: pd.DataFrame,
                         dim_produto: pd.DataFrame,
                         dim_calendario: pd.DataFrame) -> None:
    for coluna, dim, nome in (("COD_PRODUTO", dim_produto, "DIM_PRODUTO"),
                              ("COD_CLIENTE", dim_cliente, "DIM_CLIENTE"),
                              ("ANO_MES", dim_calendario, "DIM_CALENDARIO")):
        chaves = set(dim[coluna].dropna())
        orfaos = ~f[coluna].isin(chaves)
        if orfaos.any():
            abortar(f"integridade referencial: {int(orfaos.sum()):,} linha(s) da "
                    f"fato com {coluna} fora de {nome}. "
                    f"Exemplos: {sorted(f.loc[orfaos, coluna].unique())[:5]}")
        log(f"FK {coluna:<14} -> {nome:<16} ok")


def retirar_nao_produto(f: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """D-84 (02/10/2026): tira da fato os SKUs declarados em
    `fontes.sellin.skus_nao_produto` (pallet e displays). Roda DEPOIS da
    reconciliacao contra a fonte, que confere todas as linhas. Devolve a fato
    sem eles e o que saiu por SKU x mes (para log, relatorio e csv)."""
    cods = {str(k) for k in (CFG["fontes"]["sellin"].get("skus_nao_produto") or {})}
    sai = f["COD_PRODUTO"].astype(str).isin(cods)
    retirado = (f[sai].groupby(["COD_PRODUTO", "ANO_MES"], observed=True)
                      [["RECEITA", "PESO_KG", "CAIXAS"]].sum().reset_index())
    if sai.any():
        log(f"D-84: {int(sai.sum()):,} linha(s) de {retirado['COD_PRODUTO'].nunique()} SKU(s) "
            f"que nao sao produto sairam do painel: R$ {retirado['RECEITA'].sum():,.2f} · "
            f"{retirado['PESO_KG'].sum():,.1f} kg · {retirado['CAIXAS'].sum():,.0f} cx "
            "(a reconciliacao com a fonte ja contou estas linhas)", "ok")
    fora = sorted(cods - set(f["COD_PRODUTO"].astype(str)))
    if fora:
        log(f"D-84: SKU(s) declarado(s) sem linha no sell-in (regra ociosa): {fora}", "aviso")
    return f[~sai].reset_index(drop=True), retirado


def reconciliar_origem(f: pd.DataFrame, meta: dict) -> list[str]:
    """Soma da fato x linha `Total` de cada arquivo, nas TRÊS métricas.

    Meses partidos em `p1`/`p2` somam: a conferência é por ARQUIVO, e cada
    arquivo tem o seu próprio gabarito, então a soma fecha naturalmente.
    """
    gabaritos = meta["gabaritos"]
    if not gabaritos:
        msg = "arquivos sem linha 'Total' — reconciliacao contra a origem NAO executada"
        log(msg, "aviso")
        return [msg]

    calc = f.groupby("ARQUIVO_ORIGEM")[["RECEITA", "PESO_KG", "CAIXAS"]].sum()
    ruins, avisos = [], []

    # A5: arquivo sem gabarito, ou gabarito com métrica vazia/ilegível, NÃO é
    # "reconciliado" — é conferência que não rodou, e isso sai como AVISO.
    # "Checagem que não roda é pior do que checagem que não existe."
    for arq in meta.get("arquivos") or calc.index.tolist():
        if arq not in gabaritos:
            msg = f"{arq}: sem linha 'Total' legivel — reconciliacao NAO executada"
            log(msg, "aviso")
            avisos.append(msg)

    for arq, gab in sorted(gabaritos.items()):
        if arq not in calc.index:
            ruins.append(f"{arq}: nenhuma linha util apos a limpeza do rodape")
            continue
        c = calc.loc[arq]
        for chave, coluna, tol in (("receita", "RECEITA", _TOL["tolerancia_receita_reais"]),
                                   ("peso_kg", "PESO_KG", _TOL["tolerancia_peso_kg"]),
                                   ("caixas", "CAIXAS", _TOL["tolerancia_caixas"])):
            esperado = gab.get(chave)
            if esperado is None:
                msg = (f"{arq}: gabarito sem '{chave}' (celula vazia ou "
                       "ilegivel no rodape) — metrica NAO conferida")
                log(msg, "aviso")
                avisos.append(msg)
                continue
            dif = float(c[coluna]) - float(esperado)
            if abs(dif) > tol:
                ruins.append(f"{arq} [{chave}]: calculado {c[coluna]:,.4f} x "
                             f"gabarito {esperado:,.4f} (dif {dif:,.4f})")
    if ruins:
        abortar("a fato NAO bate com a linha 'Total' da fonte:\n  "
                + "\n  ".join(ruins))
    log(f"reconciliado contra o gabarito da fonte em {len(gabaritos)} arquivo(s), "
        "nas 3 metricas", "ok")
    return avisos


def _cobertura(f: pd.DataFrame, dim_cliente: pd.DataFrame, flag: str,
               piso_chave: str, rotulo: str) -> float:
    """Piso de cobertura de um atributo do cliente sobre a RECEITA.

    Existe por um erro real: `Cód. cliente` zero-preenchido faz o join casar com
    ZERO cliente — e casar em silêncio, com o painel inteiro num balde de
    "não atribuído". Vale tanto para a estrutura comercial quanto para o
    de-para de canais, que traz o código no mesmo formato.
    """
    tem = dim_cliente.set_index("COD_CLIENTE")[flag]
    receita_total = float(f["RECEITA"].sum())
    if receita_total == 0:
        return 0.0
    com = float(f.loc[f["COD_CLIENTE"].map(tem).fillna(False), "RECEITA"].sum())
    cobertura = com / receita_total

    piso = float(_TOL[piso_chave])
    if cobertura < piso:
        abortar(
            f"cobertura de {rotulo} sobre a receita: {cobertura:.2%} "
            f"(piso: {piso:.0%}).\n"
            "  Isto quase sempre significa que a chave de cliente nao esta\n"
            "  casando — o de-para traz o codigo zero-preenchido e o sell-in\n"
            "  traz o numero puro. Confira `src/utils/texto.py: digitos()`.\n"
            f"  Se a queda for real, ajuste `validacao.{piso_chave}`.")
    log(f"cobertura de {rotulo} sobre a receita: {cobertura:.2%} "
        f"(piso {piso:.0%})", "ok")
    return cobertura


def conferir_cobertura_estrutura(f: pd.DataFrame,
                                 dim_cliente: pd.DataFrame) -> float:
    return _cobertura(f, dim_cliente, "NA_ESTRUTURA",
                      "cobertura_minima_head", "estrutura comercial")


def conferir_cobertura_canal(f: pd.DataFrame,
                             dim_cliente: pd.DataFrame) -> float:
    if "TEM_CANAL" not in dim_cliente.columns or not dim_cliente["TEM_CANAL"].any():
        log("de-para de canais indisponivel — cobertura de canal nao conferida",
            "aviso")
        return 0.0
    return _cobertura(f, dim_cliente, "TEM_CANAL",
                      "cobertura_minima_canal", "canal")
