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
# ATENDIMENTO_PONTA saiu com a troca da base (D-34): a Hierarquia_Consolidada
# nao traz a coluna, e ela nunca chegou ao painel.
# D-50 (Fase 2): VENDEDOR (N4) entrou — nivel de ponta da matriz hierarquica.
_COLS_ESTRUTURA = ["HEAD", "GERENTE", "SUPERVISOR", "VENDEDOR", "PROJETO"]


def dim_cliente(sellin: pd.DataFrame, estrutura: pd.DataFrame,
                canais: pd.DataFrame | None = None,
                clientes_extra: pd.Series | None = None) -> pd.DataFrame:
    """Cliente + bandeira + UF + estrutura comercial + canal na mesma tabela.

    UF e bandeira são ATRIBUTOS do cliente, não dimensões próprias: vêm da mesma
    linha, têm o cliente como única chave e nunca são recortadas sem ele.
    Head, gerente, supervisor, canal e subcanal idem — uma tabela separada
    ligaria na fato pelo cliente de qualquer jeito. Ver `docs/06 §2.3`.

    D-74 (Q4-a, 08/09/2026): `clientes_extra` sao codigos que NAO tem sell-in
    na serie mas precisam existir na dimensao — hoje, clientes com META. Eles
    entram com nome/bandeira/UF ausentes (nada inventado), recebem a
    hierarquia e o canal pelos mesmos de-paras de todo mundo (quem nao esta
    na Hierarquia_Consolidada fica "sem estrutura", como qualquer outro) e
    carregam a flag SEM_SELLIN. Medido em 08/09: zero casos na base atual;
    a regra existe para o dia em que aparecer um.
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
    base["SEM_SELLIN"] = False
    if clientes_extra is not None and len(clientes_extra):
        novos = sorted(set(clientes_extra.dropna().astype("string"))
                       - set(base["COD_CLIENTE"]))
        if novos:
            ext = pd.DataFrame({"COD_CLIENTE": pd.Series(novos, dtype="string")})
            for c in base.columns:
                if c not in ext.columns:
                    ext[c] = pd.Series(pd.NA, index=ext.index,
                                       dtype=base[c].dtype if c != "SEM_SELLIN" else "boolean")
            ext["SEM_SELLIN"] = True
            base = pd.concat([base, ext[base.columns]], ignore_index=True)
            log(f"{len(novos):,} cliente(s) SEM sell-in na serie entram na "
                "DIM_CLIENTE por terem META (D-74/Q4-a) — nome, bandeira e "
                "UF ficam ausentes; hierarquia e canal pelos de-paras", "aviso")
    base["SEM_SELLIN"] = base["SEM_SELLIN"].astype(bool)

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

    # D-74: cliente sem sell-in (so meta) nao tem bandeira de sell-in; se a
    # Hierarquia_Consolidada traz o nome da bandeira, ele vale — e cadastro,
    # nao invencao. Sem nada, fica o balde de ausencia.
    if "BANDEIRA_ESTRUTURA" in d.columns and d["SEM_SELLIN"].any():
        so_meta = d["SEM_SELLIN"] & d["BANDEIRA"].isna()
        d.loc[so_meta, "BANDEIRA"] = d.loc[so_meta, "BANDEIRA_ESTRUTURA"]
    d["BANDEIRA"] = d["BANDEIRA"].fillna(SEM_BANDEIRA)
    d["UF"] = d["UF"].fillna(SEM_UF)

    # D-42: codigo de bandeira vindo da Hierarquia_Consolidada. Era a ponte por
    # codigo com a base de metas antiga; desde a D-49 (tema Metas removido) e
    # so ATRIBUTO do cadastro — a futura meta cruza pela chave do cliente.
    # Ausencia fica <NA> (esquema estavel mesmo sem estrutura).
    for c in ("COD_BANDEIRA", "BANDEIRA_ESTRUTURA"):
        if c not in d.columns:
            d[c] = pd.Series(pd.NA, index=d.index, dtype="string")
    com_cod = int(d["COD_BANDEIRA"].notna().sum())
    if com_cod:
        log(f"codigo de bandeira (hierarquia): {com_cod:,} de {len(d):,} "
            f"clientes ({com_cod / len(d):.1%})", "ok")
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
