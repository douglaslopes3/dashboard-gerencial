# -*- coding: utf-8 -*-
"""Camada analítica — os dois cubos que o painel consome.

REGRA QUE MANDA AQUI: **linha transacional nunca chega ao HTML.**
Entram 3.085.119 linhas de fato; saem 280.972 linhas de agregado.

Os números vão para o JSON como INTEIROS ESCALADOS — receita em centavos, peso em
gramas, caixas em centésimos. Dois motivos:

  1. inteiro serializa mais curto que float com casas decimais;
  2. e, principalmente, a soma volta **exata**. Arredondar para reais faria a
     soma dos 72 mil registros do cubo divergir da fato em alguns milhares de
     reais — pequeno na tela, mas suficiente para a reconciliação nunca fechar,
     e reconciliação que não fecha vira reconciliação que ninguém olha.

Os cortes de cada cubo estão medidos em `docs/09_ARQUITETURA_SOLUCAO.md §4`.
"""
from __future__ import annotations

import pandas as pd

from ..utils.config import CFG
from ..utils.log import abortar, log

_DASH = CFG["dashboard"]
_TOL_REL = float(CFG["validacao"]["tolerancia_cubo_relativa"])

ESC_RECEITA = 100      # centavos
ESC_PESO = 1000        # gramas
ESC_CAIXAS = 100       # centesimos de caixa


def _indexar(valores) -> tuple[list, dict]:
    lista = list(valores)
    return lista, {v: i for i, v in enumerate(lista)}


def _escalar(g: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=g.index)
    out["R"] = (g["RECEITA"] * ESC_RECEITA).round().astype("int64")
    out["P"] = (g["PESO_KG"] * ESC_PESO).round().astype("int64")
    out["C"] = (g["CAIXAS"].fillna(0.0) * ESC_CAIXAS).round().astype("int64")
    return out


def construir(fato: pd.DataFrame, dim_cliente: pd.DataFrame,
              dim_produto: pd.DataFrame, dim_cal: pd.DataFrame) -> dict:
    d = fato.merge(
        dim_cliente[["COD_CLIENTE", "BANDEIRA", "UF", "HEAD", "GERENTE"]],
        on="COD_CLIENTE", how="left")
    d = d.merge(dim_produto[["COD_PRODUTO", "CATEGORIA"]],
                on="COD_PRODUTO", how="left")

    # ---------------------------------------------------------------- eixos
    meses, i_mes = _indexar(dim_cal["ANO_MES"].tolist())
    cats, i_cat = _indexar(sorted(d["CATEGORIA"].dropna().unique()))
    ufs, i_uf = _indexar(sorted(d["UF"].dropna().unique()))
    heads, i_head = _indexar(sorted(dim_cliente["HEAD"].dropna().unique()))

    # HEAD e GERENTE viajam como UM eixo (o par), nao como dois.
    # Medido: 14 pares para 13 gerentes — "Gerente NENO" atende dois heads.
    # Guardar o par custa 1 linha a mais e mantem os dois filtros exatos;
    # guardar so o gerente perderia o head, e guardar os dois separados
    # multiplicaria o cubo por combinacoes que nao existem.
    pares = (d[["HEAD", "GERENTE"]].drop_duplicates()
              .sort_values(["HEAD", "GERENTE"]).values.tolist())
    i_par = {(h, g): i for i, (h, g) in enumerate(pares)}

    # ------------------------------------------------- bandeira: top N + balde
    topn = int(_DASH["top_bandeiras"])
    rotulo_demais = _DASH["rotulo_demais_bandeiras"]
    ranking = d.groupby("BANDEIRA", observed=True)["RECEITA"].sum().sort_values(ascending=False)
    principais = list(ranking.head(topn).index)
    n_demais = max(len(ranking) - len(principais), 0)
    rotulo_balde = f"{rotulo_demais} ({n_demais:,} bandeiras)".replace(",", ".")
    cobertura = float(ranking.head(topn).sum() / ranking.sum()) if len(ranking) else 1.0

    d["BAN_CUBO"] = d["BANDEIRA"].where(d["BANDEIRA"].isin(principais), rotulo_balde)
    bans, i_ban = _indexar(principais + ([rotulo_balde] if n_demais else []))
    log(f"bandeiras: {len(principais):,} principais ({cobertura:.1%} da receita) "
        f"+ balde com {n_demais:,}", "ok")

    # -------------------------------------------------------- CUBO PRINCIPAL
    g = (d.groupby(["ANO_MES", "BAN_CUBO", "CATEGORIA", "HEAD", "GERENTE", "UF"],
                   observed=True, dropna=False)[["RECEITA", "PESO_KG", "CAIXAS"]]
          .sum(min_count=1).reset_index())
    esc = _escalar(g)
    cubo = [[i_mes[am], i_ban[bn], i_cat[ct], i_par[(hd, gr)], i_uf[uf], r, p, c]
            for am, bn, ct, hd, gr, uf, r, p, c
            in zip(g["ANO_MES"], g["BAN_CUBO"], g["CATEGORIA"], g["HEAD"],
                   g["GERENTE"], g["UF"], esc["R"], esc["P"], esc["C"])]
    log(f"CUBO_PRINCIPAL         {len(cubo):>10,} linhas "
        f"(ANO_MES x BANDEIRA x CATEGORIA x HEAD/GERENTE x UF)", "ok")

    # -------------------------------------------------------------- CUBO SKU
    gs = (d.groupby(["ANO_MES", "COD_PRODUTO", "HEAD", "UF"],
                    observed=True, dropna=False)[["RECEITA", "PESO_KG", "CAIXAS"]]
           .sum(min_count=1).reset_index())
    skus, i_sku = _indexar(dim_produto["COD_PRODUTO"].tolist())
    escs = _escalar(gs)
    cubo_sku = [[i_mes[am], i_sku[sk], i_head[hd], i_uf[uf], r, p, c]
                for am, sk, hd, uf, r, p, c
                in zip(gs["ANO_MES"], gs["COD_PRODUTO"], gs["HEAD"], gs["UF"],
                       escs["R"], escs["P"], escs["C"])]
    log(f"CUBO_SKU               {len(cubo_sku):>10,} linhas "
        f"(ANO_MES x SKU x HEAD x UF)", "ok")

    # ------------------------------------------------------------ calendario
    idx_ly = [(i_mes[ly] if isinstance(ly, str) and ly in i_mes else -1)
              for ly in dim_cal["ANO_MES_LY"]]
    cal = [[am, rot, int(ano), int(mes), int(tri), int(sem), int(fy), fyrot,
            int(mf), int(tf), int(sf), ly]
           for am, rot, ano, mes, tri, sem, fy, fyrot, mf, tf, sf, ly
           in zip(dim_cal["ANO_MES"], dim_cal["ROTULO"], dim_cal["ANO"],
                  dim_cal["MES"], dim_cal["TRIMESTRE"], dim_cal["SEMESTRE"],
                  dim_cal["ANO_FISCAL"], dim_cal["ANO_FISCAL_ROTULO"],
                  dim_cal["MES_FISCAL"], dim_cal["TRIMESTRE_FISCAL"],
                  dim_cal["SEMESTRE_FISCAL"], idx_ly)]

    prod = dim_produto.set_index("COD_PRODUTO")
    sku_labels = [[str(s),
                   str(prod.at[s, "DESCRICAO_PRODUTO"]),
                   i_cat.get(prod.at[s, "CATEGORIA"], -1)]
                  for s in skus]

    return {
        "escala": {"R": ESC_RECEITA, "P": ESC_PESO, "C": ESC_CAIXAS},
        "cal": cal,
        "dims": {
            "ban": bans,
            "cat": cats,
            "uf": ufs,
            "head": heads,
            "par": pares,          # [head, gerente]
            "sku": sku_labels,     # [codigo, descricao, indice de categoria]
        },
        "cubo": cubo,
        "cubo_sku": cubo_sku,
        "corte_bandeira": {"top": len(principais), "demais": n_demais,
                           "cobertura": round(cobertura, 6),
                           "rotulo_demais": rotulo_balde},
    }


def reconciliar(pacote: dict, fato: pd.DataFrame) -> list[str]:
    """Cubo x fato, nas três métricas. Camada agregada que não reconcilia com a
    fato não é publicada — o pipeline aborta."""
    alvo = {
        "RECEITA": float(fato["RECEITA"].sum()),
        "PESO_KG": float(fato["PESO_KG"].sum()),
        "CAIXAS": float(fato["CAIXAS"].sum()),
    }
    escalas = (ESC_RECEITA, ESC_PESO, ESC_CAIXAS)
    ruins = []
    for nome, chave, base in (("CUBO_PRINCIPAL", "cubo", 5),
                              ("CUBO_SKU", "cubo_sku", 4)):
        linhas = pacote[chave]
        for k, (metrica, esc) in enumerate(zip(alvo, escalas)):
            soma = sum(l[base + k] for l in linhas) / esc
            esperado = alvo[metrica]
            dif = soma - esperado
            rel = abs(dif) / abs(esperado) if esperado else 0.0
            if rel > _TOL_REL:
                ruins.append(f"{nome} [{metrica}]: cubo {soma:,.4f} x "
                             f"fato {esperado:,.4f} (dif {dif:,.4f}, {rel:.3%})")
    if ruins:
        abortar("cubo NAO reconcilia com a FATO_SELLIN:\n  " + "\n  ".join(ruins))
    log("cubos reconciliados com a FATO_SELLIN nas 3 metricas", "ok")
    return []
