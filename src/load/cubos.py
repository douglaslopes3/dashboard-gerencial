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

# D-72 (04/09/2026): posicao da PRIMEIRA metrica (R) em cada cubo. O template
# le as mesmas posicoes (`BASE_MET`/`BASE_SKU`); o gerador e os testes somam
# por estas constantes, nunca por numero solto.
#   cubo principal: [mes, bandeira, categoria, perfil, cliente] + [R, P, C]
#   cubo de SKU:    [mes, sku, perfil] + [R, P, C]
BASE_MET = 5
BASE_MET_SKU = 3
# Chave sintetica do cliente ACUMULADO (clientes RTM somados sob a bandeira
# do distribuidor). O caractere de controle \u0001 garante que nunca colide
# com um codigo real.
RTM_PREFIXO = "\u0001RTM@"


def _indexar(valores) -> tuple[list, dict]:
    lista = list(valores)
    return lista, {v: i for i, v in enumerate(lista)}


def _nome_do_rotulo(rotulo) -> str:
    """Nome de pessoa de um rotulo "codigo - nome" (D-83, cadastros.py).
    Split so no 1o separador: o nome pode conter " - " ("JOSE CARLOS - LUNIER")
    e tem de ficar inteiro. (Ate a D-83 o rotulo era "codigo - papel - nome".)"""
    partes = str(rotulo).split(" - ", 1)
    return partes[-1].strip().upper()


def _mesma_pessoa(sup, vend) -> bool:
    """D-71: Sup./Exec. e Vend./RCA sao a mesma pessoa quando o NOME e o
    mesmo. Rotulos de ausencia (NAO ATRIBUIDO, INATIVO...) nunca contam."""
    if pd.isna(sup) or pd.isna(vend) or " - " not in str(sup) or " - " not in str(vend):
        return False
    return _nome_do_rotulo(sup) == _nome_do_rotulo(vend)


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
              dim_produto: pd.DataFrame, dim_cal: pd.DataFrame,
              fato_meta: pd.DataFrame | None = None) -> dict:
    # validate="m:1" (A15): uma duplicata futura em DIM_CLIENTE/DIM_PRODUTO
    # multiplicaria o cubo — a reconciliacao pegaria, mas com o diagnostico
    # errado ("cubo nao reconcilia"). Aqui o erro nasce com o nome certo.
    # D-72: NOME_CLIENTE e BANDEIRA_HERDADA sao OBRIGATORIAS na DIM_CLIENTE
    # (nome para o rotulo do nivel Cliente; a flag decide o acumulado RTM).
    # Faltar coluna aborta com o nome certo em vez de sair um painel com
    # clientes sem nome.
    for col in ("NOME_CLIENTE", "BANDEIRA_HERDADA"):
        if col not in dim_cliente.columns:
            abortar(f"DIM_CLIENTE sem a coluna {col} (D-72): rode o pipeline "
                    "inteiro — o cubo de cliente precisa dela.")
    d = fato.merge(
        dim_cliente[["COD_CLIENTE", "NOME_CLIENTE", "BANDEIRA",
                     "BANDEIRA_HERDADA", "HEAD", "GERENTE",
                     "SUPERVISOR", "VENDEDOR", "CANAL", "PROJETO"]],
        on="COD_CLIENTE", how="left", validate="m:1")
    d = d.merge(dim_produto[["COD_PRODUTO", "CATEGORIA"]],
                on="COD_PRODUTO", how="left", validate="m:1")

    # D-74 (08/09/2026): a META por cliente x categoria x mes cruza pela
    # CHAVE DO CLIENTE com a MESMA DIM_CLIENTE — herda bandeira, hierarquia,
    # canal e a regra RTM sem nenhuma atribuicao propria. Os eixos abaixo sao
    # a UNIAO do realizado com a meta: um par que so existe na meta (cliente
    # que ainda nao faturou na categoria) precisa de indice como qualquer
    # outro. `dm` e a meta ja com o perfil do cliente.
    tem_meta = fato_meta is not None and len(fato_meta) > 0
    if tem_meta:
        dm = fato_meta.merge(
            dim_cliente[["COD_CLIENTE", "BANDEIRA", "BANDEIRA_HERDADA", "HEAD",
                         "GERENTE", "SUPERVISOR", "VENDEDOR", "CANAL", "PROJETO"]],
            on="COD_CLIENTE", how="left", validate="m:1")
        orfaos = dm["HEAD"].isna()
        if orfaos.any():
            abortar(f"metas: {int(orfaos.sum()):,} par(es) de cliente que nao "
                    "existe na DIM_CLIENTE (ex.: "
                    f"{sorted(dm.loc[orfaos, 'COD_CLIENTE'].unique())[:5]}). "
                    "O pipeline deveria te-los incluido (D-74/Q4-a).")
    else:
        dm = None

    # ---------------------------------------------------------------- eixos
    # D-51 (Fase 3, Q10): o eixo UF saiu dos dois cubos — a aba Geografia e o
    # filtro de UF sairam do painel, e manter o eixo so inflaria o arquivo.
    # UF segue na DIM_CLIENTE (atributo do cliente, curated).
    meses, i_mes = _indexar(dim_cal["ANO_MES"].tolist())
    cats_universo = set(d["CATEGORIA"].dropna().unique())
    if tem_meta:
        cats_universo |= set(dm["CATEGORIA"].dropna().unique())
    cats, i_cat = _indexar(sorted(cats_universo))
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
    fontes_perfil = [d[COLS_PERFIL]] + ([dm[COLS_PERFIL]] if tem_meta else [])
    perfis = (pd.concat(fontes_perfil).drop_duplicates()
               .sort_values(COLS_PERFIL)
               .values.tolist())
    i_perf = {tuple(p): i for i, p in enumerate(perfis)}
    # D-71 (04/09/2026): quando o Vend./RCA E o proprio Sup./Exec., nao ha
    # nivel a descer. Medido: 37 dos 55 Sup./Exec. tem um unico vendedor
    # abaixo, e e ele mesmo com outro codigo ("1150 - Superv_SPC+Litoral -
    # DEODATO CARMO" -> "972 - TT Superv_SPC+Litora - DEODATO CARMO"); 43 dos
    # 203 pares sao a mesma pessoa. A igualdade e pelo NOME (ultima parte do
    # rotulo "codigo - papel - nome"; codigo e papel sempre diferem). A flag
    # viaja como 7o elemento do perfil — as posicoes 0-5 que o template le nao
    # mudam. O template usa a flag para nao expandir a linha na matriz e para
    # nao oferecer essa pessoa como opcao de Vend./RCA.
    pos_sup, pos_vend = COLS_PERFIL.index("SUPERVISOR"), COLS_PERFIL.index("VENDEDOR")
    perfis_out = [p + [1 if _mesma_pessoa(p[pos_sup], p[pos_vend]) else 0]
                  for p in perfis]
    n_mesma = sum(p[-1] for p in perfis_out)
    log(f"perfis em que o Vend./RCA e o proprio Sup./Exec.: {n_mesma} "
        f"(nao descem um nivel na matriz, D-71)", "ok")
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
    lista_ban = list(ranking.index)
    if tem_meta:
        # D-74: bandeira que so existe pela meta entra DEPOIS do ranking (sem
        # receita, nao tem posicao a disputar).
        lista_ban += sorted(set(dm["BANDEIRA"].dropna().unique()) - set(lista_ban))
    bans, i_ban = _indexar(lista_ban)
    cobertura = float(ranking.head(topn).sum() / ranking.sum()) if len(ranking) else 1.0
    log(f"bandeiras: {len(bans):,} no cubo (todas); corte de EXIBICAO {topn} "
        f"= {cobertura:.1%} da receita no Full", "ok")

    # ------------------------------------------- cliente: eixo do cubo (D-72)
    # Decisao do Douglas (04/09/2026): a aba Bandeiras abre por CLIENTE
    # (Bandeira > Cliente > Categoria). Ate aqui cliente nao era eixo de cubo
    # nenhum (D-30). Medido antes: 9.611 das 10.350 bandeiras tem UM cliente
    # (a bandeira e o proprio cliente) — o template nao desce esse nivel
    # quando ele e redundante (mesma logica da D-71).
    #
    # Regra dele para o RTM: "os clientes RTM nao devem aparecer na matriz de
    # bandeira do canal de Distribuicao; trazer acumulado". Cliente RTM que
    # HERDOU a bandeira do distribuidor (DIM_CLIENTE.BANDEIRA_HERDADA, D-59 +
    # D-72) vira UMA chave sintetica por bandeira; o rotulo de leitor vem do
    # config (`rotulos_exibicao.rtm_acumulado`) com a contagem de clientes.
    # Medido: 831.155 linhas com todos nominais -> 724.744 acumulando.
    # `dashboard.cliente_rtm_acumulado: false` volta a mostrar cada RTM.
    acumular = bool(_DASH.get("cliente_rtm_acumulado", True))
    herdou = d["BANDEIRA_HERDADA"].fillna(False).astype(bool) if acumular \
        else pd.Series(False, index=d.index)
    d["CLI_KEY"] = d["COD_CLIENTE"].astype(str)
    d.loc[herdou, "CLI_KEY"] = RTM_PREFIXO + d.loc[herdou, "BANDEIRA"].astype(str)
    # rotulo por chave: [codigo, nome, n_rtm]; n_rtm > 0 marca o acumulado
    # (n = clientes RTM distintos com sell-in atras da linha, contagem fixa)
    nomes = (d.loc[~herdou, ["CLI_KEY", "NOME_CLIENTE"]]
              .drop_duplicates("CLI_KEY").set_index("CLI_KEY")["NOME_CLIENTE"])
    n_rtm = d.loc[herdou].groupby("CLI_KEY")["COD_CLIENTE"].nunique()
    universo_cli = set(d["CLI_KEY"].unique())
    if tem_meta:
        # D-74: a MESMA regra de chave para a meta — o cliente RTM que herdou
        # a bandeira acumula a meta na linha Σ do distribuidor, como o
        # realizado. Cliente so com meta ganha indice proprio (nome vem da
        # DIM: ausente se nunca faturou).
        herdou_m = dm["BANDEIRA_HERDADA"].fillna(False).astype(bool) if acumular \
            else pd.Series(False, index=dm.index)
        dm["CLI_KEY"] = dm["COD_CLIENTE"].astype(str)
        dm.loc[herdou_m, "CLI_KEY"] = RTM_PREFIXO + dm.loc[herdou_m, "BANDEIRA"].astype(str)
        universo_cli |= set(dm["CLI_KEY"].unique())
        nomes_dim = dim_cliente.set_index("COD_CLIENTE")["NOME_CLIENTE"]
        for k in set(dm.loc[~herdou_m, "CLI_KEY"]) - set(nomes.index):
            nomes[k] = nomes_dim.get(k, pd.NA)
        # linha Σ que so existe pela meta: a contagem vem dos clientes da meta
        n_rtm_meta = dm.loc[herdou_m].groupby("CLI_KEY")["COD_CLIENTE"].nunique()
        n_rtm = n_rtm.combine_first(n_rtm_meta)
    clis, i_cli = _indexar(sorted(universo_cli))
    cli_labels = [["", "", int(n_rtm.get(k, 0))] if k.startswith(RTM_PREFIXO)
                  else [k, (n if isinstance(n := nomes.get(k), str) else ""), 0]
                  for k in clis]
    log(f"clientes: {len(clis) - len(n_rtm):,} nominais + {len(n_rtm):,} "
        f"linha(s) RTM acumulada(s) somando {int(n_rtm.sum()):,} clientes "
        f"(D-72; `cliente_rtm_acumulado`={acumular})", "ok")

    # -------------------------------------------------------- CUBO PRINCIPAL
    # D-72: o CLIENTE entrou como 5o indice, DEPOIS do perfil — as posicoes
    # 1 (bandeira), 2 (categoria) e 3 (perfil) que o template le nao mudaram;
    # as metricas deslocaram uma casa (BASE_MET 4 -> 5).
    g = (d.groupby(["ANO_MES", "BANDEIRA", "CATEGORIA"] + COLS_PERFIL + ["CLI_KEY"],
                   observed=True, dropna=False)[["RECEITA", "PESO_KG", "CAIXAS"]]
          .sum(min_count=1).reset_index())
    esc = _escalar(g)
    cubo = [[i_mes[am], i_ban[bn], i_cat[ct], i_perf[(hd, gr, sp, cn, pj, vd)],
             i_cli[cl], r, p, c]
            for am, bn, ct, hd, gr, sp, cn, pj, vd, cl, r, p, c
            in zip(g["ANO_MES"], g["BANDEIRA"], g["CATEGORIA"], g["HEAD"],
                   g["GERENTE"], g["SUPERVISOR"], g["CANAL"], g["PROJETO"],
                   g["VENDEDOR"], g["CLI_KEY"], esc["R"], esc["P"], esc["C"])]
    log(f"CUBO_PRINCIPAL         {len(cubo):>10,} linhas "
        f"(ANO_MES x BANDEIRA x CATEGORIA x PERFIL x CLIENTE)", "ok")

    # ------------------------------------------------------------ CUBO META
    # D-74 (08/09/2026): a meta viaja num cubo IRMAO do principal, com os
    # MESMOS cinco indices [mes, bandeira, categoria, perfil, cliente] e duas
    # metricas [META_R$ em centavos, META_KG em gramas] — as mesmas escalas
    # do realizado (ESC_RECEITA/ESC_PESO), para o template dividir os dois
    # pela mesma constante e nunca somar kg com t. Cubo separado, e nao duas
    # colunas a mais no principal, porque 95% dos pares com meta nao tem
    # sell-in no mes (medido em set/26 parcial: 69.260 de 73.397) e porque
    # o realizado nao pode ganhar linha por causa da meta. Mes sem meta nao
    # tem linha: ausencia e ausencia, nunca zero. Custo medido: 0,96 MB
    # (gzip+base64) por mes de meta no Full.
    if tem_meta:
        gm = (dm.groupby(["ANO_MES", "BANDEIRA", "CATEGORIA"] + COLS_PERFIL + ["CLI_KEY"],
                         observed=True, dropna=False)[["META_RECEITA", "META_PESO_KG"]]
                .sum(min_count=1).reset_index())
        mr = (gm["META_RECEITA"].fillna(0.0) * ESC_RECEITA).round().astype("int64")
        mp = (gm["META_PESO_KG"].fillna(0.0) * ESC_PESO).round().astype("int64")
        cubo_meta = [[i_mes[am], i_ban[bn], i_cat[ct],
                      i_perf[(hd, gr, sp, cn, pj, vd)], i_cli[cl], r, p]
                     for am, bn, ct, hd, gr, sp, cn, pj, vd, cl, r, p
                     in zip(gm["ANO_MES"], gm["BANDEIRA"], gm["CATEGORIA"],
                            gm["HEAD"], gm["GERENTE"], gm["SUPERVISOR"],
                            gm["CANAL"], gm["PROJETO"], gm["VENDEDOR"],
                            gm["CLI_KEY"], mr, mp)]
        meses_meta = sorted(set(gm["ANO_MES"]))
        log(f"CUBO_META              {len(cubo_meta):>10,} linhas "
            f"(mesmos indices; meses {meses_meta[0]} a {meses_meta[-1]}, "
            f"{len(meses_meta)}) — D-74", "ok")
    else:
        cubo_meta = []

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
            # [head, gerente, sup./exec., canal, projeto, vendedor,
            #  vend_e_o_sup] — o MESMO eixo nos dois cubos desde a D-48; o
            # vendedor (N4) entrou na posicao 5 na D-50 e a flag da D-71 na
            # posicao 6, sem mexer nas posicoes que o template le.
            "perfil": perfis_out,
            "sku": sku_labels,     # [codigo, descricao, indice de categoria]
            # D-72: [codigo, nome, n_rtm]. n_rtm > 0 = linha acumulada dos
            # clientes RTM sob a bandeira (codigo e nome vazios; o rotulo
            # vem de DB.rotulos_exibicao.rtm_acumulado no template).
            "cli": cli_labels,
        },
        "cubo": cubo,
        "cubo_sku": cubo_sku,
        # D-74: [mes, bandeira, categoria, perfil, cliente, META_R$, META_KG]
        # nas escalas R e P. Lista vazia = painel sem meta.
        "cubo_meta": cubo_meta,
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
    # D-51: sem o eixo UF, o cubo principal tinha 4 indices antes das
    # metricas; D-72: 5 (o cliente entrou). D-64: o de SKU tem 3.
    for nome, chave, base in (("CUBO_PRINCIPAL", "cubo", BASE_MET),
                              ("CUBO_SKU", "cubo_sku", BASE_MET_SKU)):
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


# D-74: posicao da primeira metrica no cubo de meta (mesmos 5 indices do
# principal). O template le `BASE_META`.
BASE_MET_META = 5


def reconciliar_meta(pacote: dict, fato_meta: pd.DataFrame | None) -> None:
    """CUBO_META x FATO_META, por MES e nas duas metricas — a meta de um mes
    nao pode vazar para outro nem somar em dobro (RTM acumulado). Aborta."""
    linhas = pacote.get("cubo_meta") or []
    if fato_meta is None or fato_meta.empty:
        if linhas:
            abortar("CUBO_META tem linhas sem FATO_META por tras")
        return
    meses = [c[0] for c in pacote["cal"]]
    alvo = fato_meta.groupby("ANO_MES")[["META_RECEITA", "META_PESO_KG"]].sum()
    soma: dict[int, list[float]] = {}
    for l in linhas:
        s = soma.setdefault(l[0], [0.0, 0.0])
        s[0] += l[BASE_MET_META]
        s[1] += l[BASE_MET_META + 1]
    ruins = []
    for am, esperado in alvo.iterrows():
        i = meses.index(am) if am in meses else -1
        got = soma.get(i, [0.0, 0.0])
        for k, (metrica, esc) in enumerate((("META_RECEITA", ESC_RECEITA),
                                            ("META_PESO_KG", ESC_PESO))):
            v = got[k] / esc
            e = float(esperado[metrica])
            rel = abs(v - e) / abs(e) if e else abs(v)
            if rel > _TOL_REL:
                ruins.append(f"{am} [{metrica}]: cubo {v:,.4f} x fato "
                             f"{e:,.4f} ({rel:.3%})")
    extras = sorted(set(soma) - {meses.index(am) for am in alvo.index if am in meses})
    if extras:
        ruins.append(f"meses no CUBO_META sem FATO_META: {[meses[i] for i in extras]}")
    if ruins:
        abortar("CUBO_META NAO reconcilia com a FATO_META:\n  " + "\n  ".join(ruins))
    log(f"CUBO_META reconciliado com a FATO_META nos {len(alvo)} mes(es), "
        "2 metricas", "ok")
