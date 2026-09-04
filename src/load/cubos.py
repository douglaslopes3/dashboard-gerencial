# -*- coding: utf-8 -*-
"""Camada analítica — os dois cubos que o painel consome.

REGRA QUE MANDA AQUI: **linha transacional nunca chega ao HTML.**
Entram 3.127.196 linhas de fato; saem 989.928 linhas de agregado
(123.900 no cubo principal + 866.028 no de SKU, medidos em 03/09/2026 com o
eixo da D-48/D-50 e sem UF desde a D-51 — em 02/09, com UF, eram 97.710 +
650.409; antes da D-48, 94.085 + 370.823 com quatro filtros ignorados na aba
de SKU).

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
# D-50 (Fase 2): o VENDEDOR (N4) entra NO FIM, posicao 5 — as posicoes 0-4
# que o template v3 le nao mudam; a matriz hierarquica da Fase 3 le a 5.
COLS_PERFIL = ["HEAD", "GERENTE", "SUPERVISOR", "CANAL", "PROJETO", "VENDEDOR"]

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
        dim_cliente[["COD_CLIENTE", "BANDEIRA", "HEAD", "GERENTE",
                     "SUPERVISOR", "VENDEDOR", "CANAL", "PROJETO"]],
        on="COD_CLIENTE", how="left", validate="m:1")
    d = d.merge(dim_produto[["COD_PRODUTO", "CATEGORIA"]],
                on="COD_PRODUTO", how="left", validate="m:1")

    # ---------------------------------------------------------------- eixos
    # D-51 (Fase 3, Q10): o eixo UF saiu dos dois cubos — a aba Geografia e o
    # filtro de UF sairam do painel, e manter o eixo so inflaria o arquivo.
    # UF segue na DIM_CLIENTE (atributo do cliente, curated).
    meses, i_mes = _indexar(dim_cal["ANO_MES"].tolist())
    cats, i_cat = _indexar(sorted(d["CATEGORIA"].dropna().unique()))
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
    log(f"perfis (head x gerente x sup./exec. x canal x projeto x vendedor): "
        f"{len(perfis)}", "ok")

    # ---------------------------------------- bandeira: TODAS no cubo (D-65)
    # Ate a D-64 o cubo agregava as bandeiras fora do top N corporativo numa
    # linha "DEMAIS BANDEIRAS" AQUI, na geracao — e o que ficava fora do top
    # nunca mais era individualizavel em arquivo nenhum. Medido em 03/09/2026:
    # o executivo RS/SC via 13 bandeiras nominais e 2.917 dentro do Σ (89% do
    # faturamento dele); 14 dos 55 executivos e 4 dos 13 gerentes tinham mais
    # escondido do que exibido. Decisao do Douglas: cada nivel ve as SUAS
    # bandeiras, todas, com busca. Entao o cubo carrega todas (495.037 linhas
    # medidas na base inteira, contra 123.900 com corte; cabe porque a D-64
    # tirou o eixo morto do cubo de SKU), e o corte passa a ser de EXIBICAO:
    # o template do Full e do N1 mostra as N maiores DO PROPRIO ARQUIVO e soma
    # o resto numa linha Σ na tela; N2 e N3 exibem tudo (config
    # `dashboard.exibir_todas_bandeiras_em`). A ordem dos indices e o ranking
    # global por receita — util para desempate, nao e mais um corte.
    topn = int(_DASH["top_bandeiras"])
    rotulo_demais = _DASH["rotulo_demais_bandeiras"]
    ranking = d.groupby("BANDEIRA", observed=True)["RECEITA"].sum().sort_values(ascending=False)
    bans, i_ban = _indexar(list(ranking.index))
    cobertura = float(ranking.head(topn).sum() / ranking.sum()) if len(ranking) else 1.0
    log(f"bandeiras: {len(bans):,} no cubo (todas); corte de EXIBICAO {topn} "
        f"= {cobertura:.1%} da receita no Full", "ok")

    # -------------------------------------------------------- CUBO PRINCIPAL
    g = (d.groupby(["ANO_MES", "BANDEIRA", "CATEGORIA"] + COLS_PERFIL,
                   observed=True, dropna=False)[["RECEITA", "PESO_KG", "CAIXAS"]]
          .sum(min_count=1).reset_index())
    esc = _escalar(g)
    cubo = [[i_mes[am], i_ban[bn], i_cat[ct], i_perf[(hd, gr, sp, cn, pj, vd)],
             r, p, c]
            for am, bn, ct, hd, gr, sp, cn, pj, vd, r, p, c
            in zip(g["ANO_MES"], g["BANDEIRA"], g["CATEGORIA"], g["HEAD"],
                   g["GERENTE"], g["SUPERVISOR"], g["CANAL"], g["PROJETO"],
                   g["VENDEDOR"], esc["R"], esc["P"], esc["C"])]
    log(f"CUBO_PRINCIPAL         {len(cubo):>10,} linhas "
        f"(ANO_MES x BANDEIRA x CATEGORIA x PERFIL)", "ok")

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
    #
    # D-64 (03/09/2026): a BANDEIRA SAIU deste cubo. Ela entrou na D-48 para
    # o filtro de bandeira valer na aba de SKU; a D-51 tirou esse filtro e a
    # matriz Categoria > SKU nunca leu o eixo (medido no template v4: `BANDE`
    # so estava definido). Era peso morto: 866.028 -> ~680.530 linhas na base
    # inteira, e e o que paga a D-65 (todas as bandeiras no cubo principal).
    # Linha: [mes, sku, perfil, R, P, C] — 3 indices + 3 metricas.
    gs = (d.groupby(["ANO_MES", "COD_PRODUTO"] + COLS_PERFIL,
                    observed=True, dropna=False)[["RECEITA", "PESO_KG", "CAIXAS"]]
           .sum(min_count=1).reset_index())
    skus, i_sku = _indexar(dim_produto["COD_PRODUTO"].tolist())
    escs = _escalar(gs)
    cubo_sku = [[i_mes[am], i_sku[sk], i_perf[(hd, gr, sp, cn, pj, vd)],
                 r, p, c]
                for am, sk, hd, gr, sp, cn, pj, vd, r, p, c
                in zip(gs["ANO_MES"], gs["COD_PRODUTO"], gs["HEAD"],
                       gs["GERENTE"], gs["SUPERVISOR"], gs["CANAL"],
                       gs["PROJETO"], gs["VENDEDOR"],
                       escs["R"], escs["P"], escs["C"])]
    log(f"CUBO_SKU               {len(cubo_sku):>10,} linhas "
        f"(ANO_MES x SKU x PERFIL)", "ok")

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
            "head": heads,
            "canal": canais,
            # [head, gerente, sup./exec., canal, projeto, vendedor] — o MESMO
            # eixo nos dois cubos desde a D-48; o vendedor (N4) entrou na
            # posicao 5 na D-50, sem mexer nas posicoes que o template le.
            "perfil": perfis,
            "sku": sku_labels,     # [codigo, descricao, indice de categoria]
        },
        "cubo": cubo,
        "cubo_sku": cubo_sku,
        # D-65: corte de EXIBICAO. `top` e quantas o Full/N1 mostram
        # nominalmente; `universo` e quantas bandeiras o arquivo carrega
        # (filtrar_por_nivel reconta); `exibir_todas` e decidido por nivel no
        # gerador; `rotulo_base` nomeia a linha Σ montada NA TELA.
        "corte_bandeira": {"top": topn, "universo": len(bans),
                           "cobertura_top_full": round(cobertura, 6),
                           "rotulo_base": rotulo_demais,
                           "exibir_todas": False},
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
    # D-51: sem o eixo UF, o cubo principal tem 4 indices antes das metricas.
    # D-64: o de SKU tem 3 (a bandeira saiu dele).
    for nome, chave, base in (("CUBO_PRINCIPAL", "cubo", 4),
                              ("CUBO_SKU", "cubo_sku", 3)):
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
