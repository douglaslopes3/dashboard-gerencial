# -*- coding: utf-8 -*-
"""Camada analítica — os dois cubos que o painel consome.

REGRA QUE MANDA AQUI: **linha transacional nunca chega ao HTML.**
Entram 3.117.999 linhas de fato; saem 748.119 linhas de agregado
(97.710 no cubo principal + 650.409 no de SKU, medidos em 02/09/2026 com o
eixo da D-48 — antes eram 94.085 + 370.823 com quatro filtros ignorados na
aba de SKU).

Os números vão para o JSON como INTEIROS ESCALADOS — receita em centavos, peso em
gramas, caixas em centésimos. Dois motivos:

  1. inteiro serializa mais curto que float com casas decimais;
  2. e, principalmente, a soma volta exata AO CENTAVO por celula; no total, o
     arredondamento de meio centavo por grupo deriva menos de R$ 1 sobre
     R$ 2,26 bi (medido: R$ 0,36 no pior cubo — 1,6e-10, 6 mil vezes dentro da
     tolerancia). Arredondar para reais, ao contrario, derivaria milhares de
     reais e a reconciliacao nunca fecharia — e reconciliacao que nao fecha
     vira reconciliacao que ninguem olha (auditoria, C11).

Os cortes de cada cubo estão medidos em `docs/09_ARQUITETURA_SOLUCAO.md §4`.
"""
from __future__ import annotations

import pandas as pd

from ..utils.config import CFG
from ..utils.log import abortar, log

_DASH = CFG["dashboard"]
_TOL_REL = float(CFG["validacao"]["tolerancia_cubo_relativa"])

# D-48 (02/09/2026): o eixo comercial dos DOIS cubos. Esta lista e a unica
# fonte da ordem dos componentes do perfil — o template le pelas mesmas
# posicoes (0 head, 1 gerente, 2 sup./exec., 3 canal, 4 projeto).
COLS_PERFIL = ["HEAD", "GERENTE", "SUPERVISOR", "CANAL", "PROJETO"]

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
    # PERDA ASSUMIDA (auditoria A13; docs/06 §2.1): o JSON posicional nao
    # carrega nulo por celula, entao grupo 100% nulo de CAIXAS sai como C=0.
    # Medido em 27/08/2026: 9.519 das 368.699 celulas do CUBO_SKU (2,6%),
    # R$ -7,30 mi de receita associada. A FATO preserva o nulo — quem precisar
    # da distincao le a fato, nao o cubo. O total reconcilia igual (a soma
    # ignora nulos nas duas pontas).
    out["C"] = (g["CAIXAS"].fillna(0.0) * ESC_CAIXAS).round().astype("int64")
    return out


def construir(fato: pd.DataFrame, dim_cliente: pd.DataFrame,
              dim_produto: pd.DataFrame, dim_cal: pd.DataFrame) -> dict:
    # validate="m:1" (A15): uma duplicata futura em DIM_CLIENTE/DIM_PRODUTO
    # multiplicaria o cubo — a reconciliacao pegaria, mas com o diagnostico
    # errado ("cubo nao reconcilia"). Aqui o erro nasce com o nome certo.
    d = fato.merge(
        dim_cliente[["COD_CLIENTE", "BANDEIRA", "UF", "HEAD", "GERENTE",
                     "SUPERVISOR", "CANAL", "PROJETO"]],
        on="COD_CLIENTE", how="left", validate="m:1")
    d = d.merge(dim_produto[["COD_PRODUTO", "CATEGORIA"]],
                on="COD_PRODUTO", how="left", validate="m:1")

    # ---------------------------------------------------------------- eixos
    meses, i_mes = _indexar(dim_cal["ANO_MES"].tolist())
    cats, i_cat = _indexar(sorted(d["CATEGORIA"].dropna().unique()))
    ufs, i_uf = _indexar(sorted(d["UF"].dropna().unique()))
    heads, i_head = _indexar(sorted(dim_cliente["HEAD"].dropna().unique()))
    canais, i_can = _indexar(sorted(dim_cliente["CANAL"].dropna().unique()))

    # HEAD, GERENTE, SUPERVISOR, CANAL e PROJETO viajam como UM eixo (o PERFIL
    # do cliente), nao como cinco — guardar cada um como indice separado
    # multiplicaria o cubo por combinacoes que nao existem, e guardar so um
    # perderia os outros filtros. O perfil mantem os cinco filtros exatos ao
    # custo de UM indice por linha.
    # D-48 (02/09/2026): o SUPERVISOR (N3 Sup./Exec.) entrou aqui. Medido antes
    # de decidir: 123 -> 223 perfis e 94.085 -> 97.710 linhas no cubo principal
    # (+3,9%), 110 KB de JSON. A cardinalidade do eixo cresce; o cubo quase nao.
    perfis = (d[COLS_PERFIL].drop_duplicates()
               .sort_values(COLS_PERFIL)
               .values.tolist())
    i_perf = {tuple(p): i for i, p in enumerate(perfis)}
    log(f"perfis (head x gerente x sup./exec. x canal x projeto): "
        f"{len(perfis)}", "ok")

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
    g = (d.groupby(["ANO_MES", "BAN_CUBO", "CATEGORIA"] + COLS_PERFIL + ["UF"],
                   observed=True, dropna=False)[["RECEITA", "PESO_KG", "CAIXAS"]]
          .sum(min_count=1).reset_index())
    esc = _escalar(g)
    cubo = [[i_mes[am], i_ban[bn], i_cat[ct], i_perf[(hd, gr, sp, cn, pj)],
             i_uf[uf], r, p, c]
            for am, bn, ct, hd, gr, sp, cn, pj, uf, r, p, c
            in zip(g["ANO_MES"], g["BAN_CUBO"], g["CATEGORIA"], g["HEAD"],
                   g["GERENTE"], g["SUPERVISOR"], g["CANAL"], g["PROJETO"],
                   g["UF"], esc["R"], esc["P"], esc["C"])]
    log(f"CUBO_PRINCIPAL         {len(cubo):>10,} linhas "
        f"(ANO_MES x BANDEIRA x CATEGORIA x PERFIL x UF)", "ok")

    # -------------------------------------------------------------- CUBO SKU
    # D-48 (02/09/2026) — o eixo comercial deste cubo era o par (HEAD, CANAL),
    # e por isso a aba de SKU IGNORAVA gerente, projeto e bandeira (D-09).
    # Filtro que a tela avisa que esta ignorando e filtro que alguem le errado:
    # o cubo passa a carregar o MESMO perfil do cubo principal (head, gerente,
    # sup./exec., canal, projeto) MAIS a bandeira. Nenhum filtro fica de fora.
    #
    # O custo foi medido antes (working/medir_n3b.py, 02/09/2026):
    #   370.823 -> 650.409 linhas (+75,4%) e 11,2 -> 22,5 MB de JSON cru.
    # Em texto puro isso levaria o painel a 25,8 MB (acima do teto de 25 MB);
    # e por isso que run_dashboard.py grava os cubos COMPACTADOS — medido:
    # 7,44 MB no arquivo final, metade do painel anterior. As duas mudancas
    # (eixo e compactacao) andam juntas de proposito.
    gs = (d.groupby(["ANO_MES", "COD_PRODUTO"] + COLS_PERFIL + ["UF", "BAN_CUBO"],
                    observed=True, dropna=False)[["RECEITA", "PESO_KG", "CAIXAS"]]
           .sum(min_count=1).reset_index())
    skus, i_sku = _indexar(dim_produto["COD_PRODUTO"].tolist())
    escs = _escalar(gs)
    cubo_sku = [[i_mes[am], i_sku[sk], i_perf[(hd, gr, sp, cn, pj)],
                 i_uf[uf], i_ban[bn], r, p, c]
                for am, sk, hd, gr, sp, cn, pj, uf, bn, r, p, c
                in zip(gs["ANO_MES"], gs["COD_PRODUTO"], gs["HEAD"],
                       gs["GERENTE"], gs["SUPERVISOR"], gs["CANAL"],
                       gs["PROJETO"], gs["UF"], gs["BAN_CUBO"],
                       escs["R"], escs["P"], escs["C"])]
    log(f"CUBO_SKU               {len(cubo_sku):>10,} linhas "
        f"(ANO_MES x SKU x PERFIL x UF x BANDEIRA)", "ok")

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
            "canal": canais,
            # [head, gerente, sup./exec., canal, projeto] — o MESMO eixo nos
            # dois cubos desde a D-48; o par "hc" deixou de existir.
            "perfil": perfis,
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
    # D-48: os dois cubos passaram a ter 5 indices antes das metricas.
    for nome, chave, base in (("CUBO_PRINCIPAL", "cubo", 5),
                              ("CUBO_SKU", "cubo_sku", 5)):
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
