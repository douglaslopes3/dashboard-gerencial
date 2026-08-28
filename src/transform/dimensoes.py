# -*- coding: utf-8 -*-
"""DIM_CLIENTE e DIM_PRODUTO.

As duas seguem a mesma regra: **quem aparece no fato existe na dimensão**. SKU
fora do cadastro e cliente fora do de-para NÃO são descartados — descartá-los
faria o total do painel não bater com o total da fonte, que é exatamente o tipo
de divergência silenciosa que o §14 do prompt proíbe.
"""
from __future__ import annotations

import pandas as pd

from ..utils.config import CFG
from ..utils.log import log
from ..utils.texto import texto

SEM_ESTRUTURA = CFG["dimensoes"]["rotulo_sem_estrutura"]
# C2 (auditoria): os rotulos de ausencia moram no config — o relatorio de
# qualidade le as MESMAS strings; duplicar aqui e la fazia a contagem divergir
# em silencio se alguem trocasse um rotulo num modulo so.
SEM_CANAL = CFG["dimensoes"]["rotulo_sem_canal"]
SEM_BANDEIRA = CFG["dimensoes"]["rotulo_sem_bandeira"]
SEM_UF = CFG["dimensoes"]["rotulo_sem_uf"]
SEM_CATEGORIA = CFG["dimensoes"]["rotulo_sem_categoria"]
_COLS_ESTRUTURA = ["HEAD", "GERENTE", "SUPERVISOR", "ATENDIMENTO_PONTA", "PROJETO"]


def dim_cliente(sellin: pd.DataFrame, estrutura: pd.DataFrame,
                canais: pd.DataFrame | None = None) -> pd.DataFrame:
    """Cliente + bandeira + UF + estrutura comercial + canal na mesma tabela.

    UF e bandeira são ATRIBUTOS do cliente, não dimensões próprias: vêm da mesma
    linha, têm o cliente como única chave e nunca são recortadas sem ele.
    Head, gerente, supervisor, canal e subcanal idem — uma tabela separada
    ligaria na fato pelo cliente de qualquer jeito. Ver `docs/06 §2.3`.
    """
    # O nome/bandeira/UF MAIS RECENTE vence: cliente renomeado no meio da serie
    # apareceria duas vezes no ranking.
    # B5 (auditoria): UM sort + UMA agregacao — eram dois sorts de 3 Mi de
    # linhas para tirar colunas da mesma passada.
    agg = {"NOME_CLIENTE": ("NOME_CLIENTE", "last"),
           "BANDEIRA": ("BANDEIRA", "last"),
           "UF": ("UF", "last")}
    if "SUBCANAL" in sellin.columns:                 # GAP-01, se o BI entregar
        agg["SUBCANAL"] = ("SUBCANAL", "last")
    base = (sellin.sort_values("ANO_MES", kind="stable")
                  .groupby("COD_CLIENTE", as_index=False).agg(**agg))

    antes = len(base)
    # validate="m:1" (A15): a garantia de cardinalidade nao pode morar so num
    # assert, que desaparece com `python -O`.
    d = base.merge(estrutura, on="COD_CLIENTE", how="left", validate="m:1")
    assert len(d) == antes, "o merge da estrutura comercial multiplicou clientes"

    d["NA_ESTRUTURA"] = d["HEAD"].notna() if "HEAD" in d.columns else False
    for c in _COLS_ESTRUTURA:
        if c not in d.columns:
            d[c] = pd.Series(pd.NA, index=d.index, dtype="string")
        d[c] = d[c].fillna(SEM_ESTRUTURA)

    sem = int((~d["NA_ESTRUTURA"]).sum())
    if sem:
        log(f"{sem:,} cliente(s) de sell-in SEM linha no de-para de estrutura — "
            f"entram como '{SEM_ESTRUTURA}' (nao sao descartados)", "aviso")

    # ---- canal (de bases/Canais/Canais.xlsx) -----------------------------
    # O aceite da devolutiva de 26/08/2026 pede 100% classificado, e quem sobrar
    # vai para a lista de excecoes (`data/quality/clientes_sem_canal.csv`) —
    # nunca escondido num "Outros". Medido na entrega: cobertura 100,0000%.
    if canais is not None and len(canais):
        antes = len(d)
        cols = [c for c in ("COD_CLIENTE", "CANAL", "SUBCANAL") if c in canais.columns]
        d = d.merge(canais[cols], on="COD_CLIENTE", how="left", validate="m:1")
        assert len(d) == antes, "o merge do de-para de canais multiplicou clientes"
        d["TEM_CANAL"] = d["CANAL"].notna()
        sem_canal = int((~d["TEM_CANAL"]).sum())
        if sem_canal:
            log(f"{sem_canal:,} cliente(s) de sell-in SEM canal no de-para — "
                f"entram como '{SEM_CANAL}' e saem na lista de excecoes", "aviso")
    else:
        d["TEM_CANAL"] = False
    for c in ("CANAL", "SUBCANAL"):
        if c not in d.columns:
            d[c] = pd.Series(pd.NA, index=d.index, dtype="string")
        d[c] = d[c].fillna(SEM_CANAL)

    d["BANDEIRA"] = d["BANDEIRA"].fillna(SEM_BANDEIRA)
    d["UF"] = d["UF"].fillna(SEM_UF)
    return d.sort_values("COD_CLIENTE").reset_index(drop=True)


def dim_produto(sellin: pd.DataFrame, produtos: pd.DataFrame) -> pd.DataFrame:
    """SKU + categoria + marca.

    Categoria é ATRIBUTO do produto: 12 valores para 494 SKUs, sempre lidos junto
    com o SKU. Uma DIM_CATEGORIA acrescentaria uma junção e nenhum atributo.
    """
    # O que o sell-in sabe sobre cada SKU, para o caso de ele nao estar no cadastro.
    do_fato = (sellin.sort_values("ANO_MES")
                     .groupby("COD_PRODUTO", as_index=False)
                     .agg(DESC_SELLIN=("DESCRICAO_SELLIN", "last"),
                          CAT_SELLIN=("CATEGORIA_SELLIN", "last")))

    d = do_fato.merge(produtos, on="COD_PRODUTO", how="left")
    d["FORA_DO_CADASTRO"] = d["DESCRICAO_PRODUTO"].isna()

    d["DESCRICAO_PRODUTO"] = d["DESCRICAO_PRODUTO"].fillna(d["DESC_SELLIN"])
    d["CATEGORIA"] = d["CATEGORIA"].fillna(d["CAT_SELLIN"]).fillna(SEM_CATEGORIA)
    d["MARCA"] = texto(d["MARCA"]) if "MARCA" in d.columns else pd.NA

    fora = int(d["FORA_DO_CADASTRO"].sum())
    if fora:
        log(f"{fora} SKU(s) movimentado(s) e FORA do cadastro Produtos.xlsx — "
            "entram com a descricao e a categoria do proprio sell-in, sem marca",
            "aviso")

    # Divergencia de categoria entre as duas fontes: relatada, NUNCA resolvida
    # em silencio. (Medido em 26/08/2026: zero linhas.)
    amb = d[d["CATEGORIA"].notna() & d["CAT_SELLIN"].notna()
            & (d["CATEGORIA"] != d["CAT_SELLIN"]) & ~d["FORA_DO_CADASTRO"]]
    if len(amb):
        log(f"{len(amb)} SKU(s) com categoria DIFERENTE entre o cadastro e o "
            "sell-in — vale o cadastro; a lista sai no relatorio de qualidade",
            "aviso")

    cols = ["COD_PRODUTO", "DESCRICAO_PRODUTO", "CATEGORIA", "MARCA",
            "FORA_DO_CADASTRO", "CAT_SELLIN"]
    return d[cols].sort_values("COD_PRODUTO").reset_index(drop=True)
