# -*- coding: utf-8 -*-
"""CUBO_META — meta x realizado x ano anterior, cruzados NA GERACAO (D-44).

O painel nao junta nada: recebe as tres series ja pareadas por
(mes, grupo comercial, bandeira, categoria) e so agrega e formata.

ROTA A (decisao do Douglas, 01/09/2026): na visao de metas, o realizado de uma
bandeira NOMEADA segue o dono DECLARADO na meta (head/gerente/executivo da
propria base de metas), mesmo quando a hierarquia vigente distribui os clientes
dela por outros codigos — e o que faz Meta x Realizado fecharem ao centavo em
todos os niveis (N3 soma para N2, que soma para N1). O que NAO tem bandeira
nomeada na meta (a cauda) segue a hierarquia vigente do cliente e entra com o
rotulo DEMAIS_BANDEIRAS — que e tambem onde os baldes da meta (Sem Mudanca /
Projeto L, abertos por gerente/executivo mas sem bandeira) se encaixam.

Atribuicao de cliente a bandeira da meta: CODIGO primeiro (D-42 — codigo 1 e,
na fusao, codigo 2), nome como fallback declarado, e o resto e cauda. Cliente
nenhum e atribuido duas vezes; codigo reivindicado por duas entidades fica com
a primeira (por RL de meta) e sai AVISO.

Ausencia e ausencia: mes sem sell-in ainda (set/26 antes da carga) viaja como
null, nunca como zero — a tela mostra "sem dados", nao "0% de atingimento".
"""
from __future__ import annotations

import pandas as pd

from ..utils.log import abortar, log

ESC_R = 100      # centavos
ESC_P = 1000     # gramas

DEMAIS = "DEMAIS BANDEIRAS"
BALDES = {"SEM MUDANÇA", "PROJETO L"}

# Tolerancia RELATIVA, como na reconciliacao dos cubos principais (cubos.py):
# cada celula vira inteiro escalado com arredondamento de ate meio centavo, e a
# soma dos arredondados deriva alguns centavos do float somado (medido:
# R$ 0,13 em R$ 122,28 mi na primeira carga = 1,1e-9). A tolerancia absoluta de
# 1 centavo e para reconciliar SOMAS de float (leitor de metas); aqui o desvio
# de arredondamento por celula e esperado e limitado.
_TOL_REL = 0.000001


def _rotulo_por_codigo(serie: pd.Series) -> dict:
    """'20 - ATACADO - ADEMIR TAVARES' -> {'20': rotulo}. Primeiro rotulo vence
    (na DIM cada codigo tem um rotulo so; medido)."""
    mapa: dict[str, str] = {}
    for r in serie.dropna().unique():
        cod = str(r).split(" - ")[0].strip()
        mapa.setdefault(cod, str(r))
    return mapa


def _ly_de(am: str) -> str:
    return f"{int(am[:4]) - 1}{am[4:]}"


def construir(fato: pd.DataFrame, dim_cli: pd.DataFrame, dim_prod: pd.DataFrame,
              fato_meta: pd.DataFrame) -> dict | None:
    if fato_meta is None or fato_meta.empty:
        log("CUBO_META: sem base de metas — o painel sai sem a aba", "aviso")
        return None

    m_head = _rotulo_por_codigo(dim_cli["HEAD"])
    m_ger = _rotulo_por_codigo(dim_cli["GERENTE"])
    m_sup = _rotulo_por_codigo(dim_cli["SUPERVISOR"])

    def rot(mapa: dict, cod) -> str:
        if cod is None or pd.isna(cod):
            return "NÃO ATRIBUÍDO"
        return mapa.get(str(cod), f"{cod} (fora da hierarquia)")

    fm = fato_meta.copy()
    fm["_balde"] = fm["BANDEIRA_META"].isin(BALDES)

    # ------------------------------------------ entidades nomeadas (por codigo)
    # Uma entidade por COD_BANDEIRA: e o que consolida as linhas duplicadas do
    # mesmo codigo (Passarela + Via Atacadista) sem tocar na planilha.
    nom = fm[~fm["_balde"]]
    entidades: list[dict] = []          # {cods:set, label, grupo:(h,g,s)}
    dono_cod: dict[str, int] = {}       # codigo -> indice em `entidades`
    avisos = 0
    for cod, sub in sorted(nom.groupby("COD_BANDEIRA"),
                           key=lambda kv: -kv[1]["META_RECEITA"].sum()):
        rotulos = sorted(sub["BANDEIRA_META"].unique())
        na_dim = [r for r in rotulos
                  if r in set(dim_cli["BANDEIRA"].dropna())]
        label = na_dim[0] if na_dim else rotulos[0]
        grupos = sub[["COD_HEAD", "COD_GERENTE", "COD_SUPERVISOR"]].drop_duplicates()
        if len(grupos) > 1:
            # vale o dono com mais meta; o resto e relatado, nunca engolido
            grupos = (sub.groupby(["COD_HEAD", "COD_GERENTE", "COD_SUPERVISOR"])
                      ["META_RECEITA"].sum().sort_values(ascending=False)
                      .head(1).reset_index())
            log(f"meta: bandeira {label} com mais de um dono declarado — vale "
                "o de maior meta", "aviso")
            avisos += 1
        g = grupos.iloc[0]
        ent = {"cods": {cod}, "label": label,
               "grupo": (rot(m_head, g["COD_HEAD"]),
                         rot(m_ger, g["COD_GERENTE"]),
                         rot(m_sup, g["COD_SUPERVISOR"]))}
        i = len(entidades)
        entidades.append(ent)
        dono_cod[cod] = i
        for c2 in sub["COD_BANDEIRA_2"].dropna().unique():
            if c2 in dono_cod and dono_cod[c2] != i:
                log(f"meta: codigo {c2} reivindicado por {label} (fusao) ja "
                    f"pertence a {entidades[dono_cod[c2]]['label']} — fica com "
                    "quem o tem como codigo principal", "aviso")
                avisos += 1
                continue
            ent["cods"].add(c2)
            dono_cod[c2] = i

    # ------------------------------------------------- cliente -> entidade
    cli = dim_cli[["COD_CLIENTE", "COD_BANDEIRA", "BANDEIRA",
                   "HEAD", "GERENTE", "SUPERVISOR"]].copy()
    cli["_ent"] = cli["COD_BANDEIRA"].map(
        lambda c: dono_cod.get(c, -1) if pd.notna(c) else -1)
    # fallback por NOME so para entidade que nao achou NENHUM cliente por codigo
    com_cliente = set(cli.loc[cli["_ent"] >= 0, "_ent"])
    por_nome = {e["label"]: i for i, e in enumerate(entidades)
                if i not in com_cliente}
    if por_nome:
        sem_ent = cli["_ent"] < 0
        cli.loc[sem_ent, "_ent"] = cli.loc[sem_ent, "BANDEIRA"].map(
            lambda b: por_nome.get(b, -1))
    n_por_ent = int((cli["_ent"] >= 0).sum())
    log(f"CUBO_META: {n_por_ent:,} clientes atribuidos a "
        f"{len(entidades)} bandeiras da meta (rota A); "
        f"{len(cli) - n_por_ent:,} na cauda (hierarquia vigente)", "ok")

    # ------------------------------------------------------------ meses
    meses_meta = sorted(fm["ANO_MES"].unique())
    meses_fato = set(fato["ANO_MES"].unique())
    meses = []                       # [am, rotulo, ly_am, rotulo_ly, tem_real, tem_ly]
    _ROT = {"01": "jan", "02": "fev", "03": "mar", "04": "abr", "05": "mai",
            "06": "jun", "07": "jul", "08": "ago", "09": "set", "10": "out",
            "11": "nov", "12": "dez"}

    def rot_mes(am: str) -> str:
        return f"{_ROT[am[5:7]]}/{am[2:4]}"

    for am in meses_meta:
        ly = _ly_de(am)
        meses.append([am, rot_mes(am), ly, rot_mes(ly),
                      am in meses_fato, ly in meses_fato])

    # -------------------------------------------------- realizado (atual + LY)
    slots: dict[str, list[tuple[str, int]]] = {}   # ANO_MES -> [(campo, i_mes)]
    for i, (am, _, ly, _, tem_real, tem_ly) in enumerate(meses):
        if tem_real:
            slots.setdefault(am, []).append(("real", i))
        if tem_ly:
            slots.setdefault(ly, []).append(("ly", i))

    f = fato[fato["ANO_MES"].isin(slots)]
    f = f.merge(cli[["COD_CLIENTE", "_ent", "HEAD", "GERENTE", "SUPERVISOR"]],
                on="COD_CLIENTE", how="left")
    f = f.merge(dim_prod[["COD_PRODUTO", "CATEGORIA"]], on="COD_PRODUTO",
                how="left")
    nomeada = f["_ent"] >= 0
    f["_g0"] = f["HEAD"]
    f["_g1"] = f["GERENTE"]
    f["_g2"] = f["SUPERVISOR"]
    f["_band"] = DEMAIS
    if nomeada.any():
        ents = f.loc[nomeada, "_ent"].astype(int)
        f.loc[nomeada, "_g0"] = ents.map(lambda i: entidades[i]["grupo"][0]).values
        f.loc[nomeada, "_g1"] = ents.map(lambda i: entidades[i]["grupo"][1]).values
        f.loc[nomeada, "_g2"] = ents.map(lambda i: entidades[i]["grupo"][2]).values
        f.loc[nomeada, "_band"] = ents.map(lambda i: entidades[i]["label"]).values
    gr = (f.groupby(["ANO_MES", "_g0", "_g1", "_g2", "_band", "CATEGORIA"],
                    dropna=False)[["RECEITA", "PESO_KG"]].sum().reset_index())

    # ------------------------------------------------------------- meta
    fm["_g0"] = fm["COD_HEAD"].map(lambda c: rot(m_head, c))
    fm["_g1"] = fm["COD_GERENTE"].map(lambda c: rot(m_ger, c))
    fm["_g2"] = fm["COD_SUPERVISOR"].map(lambda c: rot(m_sup, c))
    fm["_band"] = DEMAIS
    ent_nom = fm.loc[~fm["_balde"], "COD_BANDEIRA"].map(dono_cod)
    fm.loc[~fm["_balde"], "_band"] = ent_nom.map(lambda i: entidades[i]["label"]).values
    fm.loc[~fm["_balde"], "_g0"] = ent_nom.map(lambda i: entidades[i]["grupo"][0]).values
    fm.loc[~fm["_balde"], "_g1"] = ent_nom.map(lambda i: entidades[i]["grupo"][1]).values
    fm.loc[~fm["_balde"], "_g2"] = ent_nom.map(lambda i: entidades[i]["grupo"][2]).values
    gm = (fm.groupby(["ANO_MES", "_g0", "_g1", "_g2", "_band", "CATEGORIA"],
                     dropna=False)[["META_RECEITA", "META_PESO_KG"]]
            .sum().reset_index())

    # ----------------------------------------------------- montagem das linhas
    grupos: list[list[str]] = []
    i_grupo: dict[tuple, int] = {}
    bands: list[str] = []
    i_band: dict[str, int] = {}
    cats: list[str] = []
    i_cat: dict[str, int] = {}

    def idx(lista, mapa, chave):
        if chave not in mapa:
            mapa[chave] = len(lista)
            lista.append(list(chave) if isinstance(chave, tuple) else chave)
        return mapa[chave]

    linhas: dict[tuple, list] = {}     # chave -> [mr, mp, rr, rp, lr, lp]

    def celula(i_mes, g0, g1, g2, band, cat):
        chave = (i_mes, idx(grupos, i_grupo, (g0, g1, g2)),
                 idx(bands, i_band, band),
                 idx(cats, i_cat, "NAO INFORMADO" if pd.isna(cat) else cat))
        return linhas.setdefault(chave, [None] * 6)

    for r in gm.itertuples(index=False):
        am_meta = r[0]
        i_mes = next(i for i, mm in enumerate(meses) if mm[0] == am_meta)
        c = celula(i_mes, r[1], r[2], r[3], r[4], r[5])
        c[0] = (c[0] or 0) + round(r[6] * ESC_R)
        c[1] = (c[1] or 0) + round(r[7] * ESC_P)
    for r in gr.itertuples(index=False):
        for campo, i_mes in slots[r[0]]:
            c = celula(i_mes, r[1], r[2], r[3], r[4], r[5])
            base = 2 if campo == "real" else 4
            c[base] = (c[base] or 0) + round(r[6] * ESC_R)
            c[base + 1] = (c[base + 1] or 0) + round(r[7] * ESC_P)

    cubo = [[k[0], k[1], k[2], k[3], *v] for k, v in sorted(linhas.items())]

    # ------------------------------------------------------- reconciliacao
    ruins: list[str] = []

    def _confere(rotulo, soma, alvo):
        rel = abs(soma - alvo) / abs(alvo) if alvo else abs(soma)
        if rel > _TOL_REL:
            ruins.append(f"{rotulo}: cubo {soma:,.2f} x origem {alvo:,.2f} "
                         f"(dif {soma - alvo:,.2f})")

    for i, (am, _, ly, _, tem_real, tem_ly) in enumerate(meses):
        alvo_m = fm[fm["ANO_MES"] == am]
        _confere(f"meta R$ de {am}",
                 sum((l[4] or 0) for l in cubo if l[0] == i) / ESC_R,
                 float(alvo_m["META_RECEITA"].sum()))
        _confere(f"meta kg de {am}",
                 sum((l[5] or 0) for l in cubo if l[0] == i) / ESC_P,
                 float(alvo_m["META_PESO_KG"].sum()))
        for campo, base, mes_alvo, tem in (("realizado", 6, am, tem_real),
                                           ("LY", 8, ly, tem_ly)):
            if not tem:
                continue
            _confere(f"{campo} R$ de {mes_alvo}",
                     sum((l[base] or 0) for l in cubo if l[0] == i) / ESC_R,
                     float(fato.loc[fato["ANO_MES"] == mes_alvo,
                                    "RECEITA"].sum()))
    if ruins:
        abortar("CUBO_META NAO reconcilia:\n  " + "\n  ".join(ruins))

    log(f"CUBO_META              {len(cubo):>10,} linhas "
        f"(MES x GRUPO x BANDEIRA x CATEGORIA) · {len(grupos)} grupos · "
        f"{len(bands)} bandeiras · reconciliado (meta, realizado e LY)", "ok")
    return {
        "escala": {"R": ESC_R, "P": ESC_P},
        "meses": meses,
        "grupos": grupos,
        "bands": bands,
        "cats": cats,
        "linhas": cubo,
        "rotulo_demais": DEMAIS,
    }
