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

    # D-57 (03/09/2026): quantas bandeiras a linha Σ agrega EM CADA NIVEL.
    #
    # O rotulo do balde carrega uma contagem ("DEMAIS BANDEIRAS (11.008
    # bandeiras)") e, ate aqui, essa contagem era a GLOBAL — a mesma string
    # viajava para dentro dos 73 arquivos. No painel de um head ela era
    # simplesmente falsa: a linha Σ dele nao agrega 11.008 bandeiras, agrega
    # so as que tem faturamento no squad dele. Pior, a mesma nota dizia "as
    # outras 11.008" e, duas linhas abaixo, "neste recorte" — misturando o
    # universo Dori com o do leitor.
    #
    # A contagem TEM de ser feita aqui: depois do groupby a identidade das
    # bandeiras do balde se perde (viram todas o mesmo rotulo), e nem
    # `filtrar_por_nivel` nem o template conseguem recupera-la.
    #
    # Sao ~72 inteiros no pacote (4 heads + 13 gerentes + 55 sup./exec.).
    # O CORTE em si continua global e declarado como tal na tela: o conjunto
    # das N maiores e o mesmo em todos os arquivos, senao uma bandeira
    # nominal no painel de um head apareceria no balde do painel corporativo
    # e os arquivos deixariam de ser comparaveis.
    niveis_arquivo = ((_DASH.get("por_nivel") or {}).get("niveis") or {})
    demais_por_nivel: dict[str, dict[str, int]] = {}
    if n_demais:
        no_balde = d.loc[d["BAN_CUBO"] == rotulo_balde, ["BANDEIRA"] + COLS_PERFIL]
        for nome_nivel, pos in niveis_arquivo.items():
            coluna = COLS_PERFIL[int(pos)]
            demais_por_nivel[str(nome_nivel)] = {
                str(k): int(v) for k, v in
                no_balde.groupby(coluna, observed=True)["BANDEIRA"]
                        .nunique().items()}

    # -------------------------------------------------------- CUBO PRINCIPAL
    g = (d.groupby(["ANO_MES", "BAN_CUBO", "CATEGORIA"] + COLS_PERFIL,
                   observed=True, dropna=False)[["RECEITA", "PESO_KG", "CAIXAS"]]
          .sum(min_count=1).reset_index())
    esc = _escalar(g)
    cubo = [[i_mes[am], i_ban[bn], i_cat[ct], i_perf[(hd, gr, sp, cn, pj, vd)],
             r, p, c]
            for am, bn, ct, hd, gr, sp, cn, pj, vd, r, p, c
            in zip(g["ANO_MES"], g["BAN_CUBO"], g["CATEGORIA"], g["HEAD"],
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
    gs = (d.groupby(["ANO_MES", "COD_PRODUTO"] + COLS_PERFIL + ["BAN_CUBO"],
                    observed=True, dropna=False)[["RECEITA", "PESO_KG", "CAIXAS"]]
           .sum(min_count=1).reset_index())
    skus, i_sku = _indexar(dim_produto["COD_PRODUTO"].tolist())
    escs = _escalar(gs)
    cubo_sku = [[i_mes[am], i_sku[sk], i_perf[(hd, gr, sp, cn, pj, vd)],
                 i_ban[bn], r, p, c]
                for am, sk, hd, gr, sp, cn, pj, vd, bn, r, p, c
                in zip(gs["ANO_MES"], gs["COD_PRODUTO"], gs["HEAD"],
                       gs["GERENTE"], gs["SUPERVISOR"], gs["CANAL"],
                       gs["PROJETO"], gs["VENDEDOR"], gs["BAN_CUBO"],
                       escs["R"], escs["P"], escs["C"])]
    log(f"CUBO_SKU               {len(cubo_sku):>10,} linhas "
        f"(ANO_MES x SKU x PERFIL x BANDEIRA)", "ok")

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
        # D-57: `rotulo_base` e `demais_por_nivel` existem para que
        # `filtrar_por_nivel` remonte o rotulo do balde com a contagem DO
        # ARQUIVO. `top` e `cobertura` seguem globais de proposito — o corte
        # e global, e a tela diz isso.
        "corte_bandeira": {"top": len(principais), "demais": n_demais,
                           "cobertura": round(cobertura, 6),
                           "rotulo_base": rotulo_demais,
                           "rotulo_demais": rotulo_balde},
        "demais_por_nivel": demais_por_nivel,
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
    # D-51: sem o eixo UF, os dois cubos tem 4 indices antes das metricas.
    for nome, chave, base in (("CUBO_PRINCIPAL", "cubo", 4),
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
