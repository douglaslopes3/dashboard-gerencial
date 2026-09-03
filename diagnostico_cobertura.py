# -*- coding: utf-8 -*-
"""DIAGNOSTICO da queda de cobertura da estrutura comercial (03/09/2026).

    python diagnostico_cobertura.py

Script TEMPORARIO de investigacao. NAO altera base, config, cubo nem Parquet:
so le, mede e escreve DUAS listas novas em data/quality/ para o Comercial.
Pode ser apagado depois — nada do pipeline depende dele.

POR QUE ELE EXISTE
------------------
Na execucao 20260903-134305 o pipeline abortou:

    cobertura de estrutura comercial sobre a receita: 75.40% (piso: 95%)

A execucao anterior (20260902-220859) media 97,65% sobre a MESMA fato. Entre
as duas so mudou a Hierarquia_Consolidada.xlsx (14.054 -> 13.427 linhas). O
abort e o piso funcionando: ele existe exatamente para nao publicar um painel
com 22% da receita caida num balde de "NAO ATRIBUIDO".

O que este script responde, em ordem:

  1. quanto vale a receita que ficou fora e quantos clientes sao;
  2. QUAIS clientes sao, ordenados por receita (top 30 na tela, lista
     completa em CSV);
  3. se a causa e a CASCATA DO RTM — a hipotese principal. O saneamento faz o
     cliente RTM herdar a hierarquia do DISTRIBUIDOR que o atende
     (`_HERDA_DO_DISTRIBUIDOR` inclui NA_ESTRUTURA). Se um distribuidor saiu
     da Hierarquia_Consolidada, TODOS os clientes que apontam para ele caem
     junto — e um punhado de codigos removidos derruba centenas de milhoes;
  4. se algum cliente perdeu a chave por formato (o caso classico do codigo
     zero-preenchido), que seria uma causa tecnica, nao de negocio.

Ele repete exatamente o caminho do `run_pipeline.py` ate a DIM_CLIENTE, com as
mesmas funcoes — nenhuma regra e reimplementada aqui.
"""
from __future__ import annotations

import sys

for _fluxo in (sys.stdout, sys.stderr):
    try:
        _fluxo.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

import pandas as pd

from src.extract import cadastros, sellin
from src.transform import calendario, dimensoes, fato as fato_mod, saneamento
from src.utils import log as L
from src.utils.config import CFG, caminho, preparar_pastas
from src.utils.log import log, titulo

PASTA_Q = caminho(CFG["projeto"]["pasta_dados"]) / "quality"


def br(v: float, casas: int = 2) -> str:
    return f"{v:,.{casas}f}".replace(",", "@").replace(".", ",").replace("@", ".")


def main() -> int:
    preparar_pastas()
    L.abrir()
    titulo("DIAGNOSTICO · cobertura da estrutura comercial")

    bruto, meta = sellin.ler()
    estrutura, _ = cadastros.ler_estrutura()
    canais, _ = cadastros.ler_canais()
    rtm, _ = cadastros.ler_rtm()
    faltando, _ = cadastros.ler_faltando()

    f = fato_mod.construir(bruto)
    dim_cal = calendario.construir(sorted(f["ANO_MES"].unique()))
    dim_cli = dimensoes.dim_cliente(bruto, estrutura, canais)
    dim_prod = dimensoes.dim_produto(bruto, cadastros.ler_produtos())
    del bruto
    dim_cli, san, _ = saneamento.aplicar(dim_cli, rtm, faltando, f)

    receita = f.groupby("COD_CLIENTE", as_index=False)["RECEITA"].sum()
    total = float(f["RECEITA"].sum())

    # ------------------------------------------------------------- 1. tamanho
    titulo("1 · tamanho do buraco")
    d = dim_cli.set_index("COD_CLIENTE")
    receita["NA_ESTRUTURA"] = receita["COD_CLIENTE"].map(
        d["NA_ESTRUTURA"]).fillna(False)
    fora = receita[~receita["NA_ESTRUTURA"]].sort_values(
        "RECEITA", ascending=False)
    r_fora = float(fora["RECEITA"].sum())
    log(f"receita total .......... R$ {br(total)}")
    log(f"FORA da estrutura ...... R$ {br(r_fora)}  "
        f"({r_fora / total:.2%} da receita, {len(fora):,} clientes)")
    log(f"cobertura .............. {1 - r_fora / total:.2%}  "
        f"(piso {float(CFG['validacao']['cobertura_minima_head']):.0%})")
    log(f"na execucao de 02/09 ... 97,65% — a fato NAO mudou, "
        f"so a Hierarquia_Consolidada")

    # ---------------------------------------------------- 2. quem esta fora
    titulo("2 · os 30 maiores que ficaram fora")
    nomes = dim_cli.set_index("COD_CLIENTE")["NOME_CLIENTE"]
    fora = fora.copy()
    fora["CLIENTE"] = fora["COD_CLIENTE"].map(nomes)
    fora["CANAL"] = fora["COD_CLIENTE"].map(d["CANAL"])
    fora["ORIGEM_RTM"] = fora["COD_CLIENTE"].map(d["ORIGEM_RTM"]).fillna(False)
    fora["DISTRIBUIDOR"] = fora["COD_CLIENTE"].map(d["DISTRIBUIDOR"])
    fora["INATIVO"] = fora["COD_CLIENTE"].map(d["INATIVO"]).fillna(False)
    fora["PCT_RECEITA"] = fora["RECEITA"] / total
    for _, l in fora.head(30).iterrows():
        marca = ("RTM->" + str(l["DISTRIBUIDOR"])) if l["ORIGEM_RTM"] else (
            "inativo" if l["INATIVO"] else "sem linha na hierarquia")
        log(f"  {l['COD_CLIENTE']:>10}  R$ {br(l['RECEITA']):>18}  "
            f"{l['PCT_RECEITA']:>6.2%}  {str(l['CLIENTE'])[:34]:<34} {marca}")

    alvo = PASTA_Q / "diagnostico_fora_da_estrutura.csv"
    fora.to_csv(alvo, sep=";", index=False, encoding="utf-8-sig",
                decimal=",", float_format="%.2f")
    log(f"lista completa ({len(fora):,} clientes) -> {alvo}", "ok")

    # -------------------------------------------- 3. hipotese: cascata RTM
    titulo("3 · o RTM e a causa? (hipotese principal)")
    if len(rtm):
        cods_estrutura = set(estrutura["COD_CLIENTE"].dropna())
        dist = (rtm.dropna(subset=["COD_DISTRIBUIDOR"])
                   .drop_duplicates("COD_DISTRIBUIDOR")
                   [["COD_DISTRIBUIDOR", "DISTRIBUIDOR"]])
        dist["NA_HIERARQUIA"] = dist["COD_DISTRIBUIDOR"].isin(cods_estrutura)
        orfaos = dist[~dist["NA_HIERARQUIA"]]
        log(f"distribuidores no de-para RTM ......... {len(dist):,}")
        log(f"deles, SEM linha na hierarquia nova ... {len(orfaos):,}")
        if len(orfaos):
            # Quanto cada distribuidor orfao arrasta: o proprio faturamento
            # mais o de todos os clientes que apontam para ele.
            r = receita.set_index("COD_CLIENTE")["RECEITA"]
            log("")
            log("  DISTRIBUIDOR ORFAO -> quanto ele derruba (clientes RTM + ele proprio)")
            linhas = []
            for _, o in orfaos.iterrows():
                cod = o["COD_DISTRIBUIDOR"]
                filhos = rtm.loc[rtm["COD_DISTRIBUIDOR"] == cod, "COD_CLIENTE"]
                arrasta = float(r.reindex(list(filhos) + [cod]).fillna(0).sum())
                linhas.append((cod, o["DISTRIBUIDOR"], len(filhos), arrasta))
            linhas.sort(key=lambda x: -x[3])
            for cod, nome, n, v in linhas:
                log(f"  {cod:>10}  {str(nome)[:30]:<30} {n:>4} cliente(s)  "
                    f"R$ {br(v):>18}  ({v / total:.2%})")
            soma = sum(x[3] for x in linhas)
            log("")
            log(f"  SUBTOTAL DA CASCATA: R$ {br(soma)} ({soma / total:.2%} "
                f"da receita) — de {len(orfaos)} codigo(s) removido(s)", "ok")
            pd.DataFrame(linhas, columns=["COD_DISTRIBUIDOR", "DISTRIBUIDOR",
                                          "CLIENTES_RTM", "RECEITA_ARRASTADA"]
                         ).to_csv(PASTA_Q / "diagnostico_distribuidores_orfaos.csv",
                                  sep=";", index=False, encoding="utf-8-sig",
                                  decimal=",", float_format="%.2f")
            log(f"  -> {PASTA_Q / 'diagnostico_distribuidores_orfaos.csv'}", "ok")
        else:
            log("todos os distribuidores do RTM estao na hierarquia — "
                "a cascata NAO explica a queda", "ok")

    # ------------------------------------------ 4. a chave ainda bate?
    titulo("4 · a queda e real ou e a chave que parou de casar?")
    # O modo classico de falhar em silencio: codigo zero-preenchido de um lado
    # e numero puro do outro. `digitos()` cobre os dois — se ele estivesse
    # falhando, a cobertura cairia para perto de ZERO, nao para 75%.
    cods_fato = set(f["COD_CLIENTE"].dropna())
    cods_est = set(estrutura["COD_CLIENTE"].dropna())
    inter = cods_fato & cods_est
    log(f"clientes distintos na fato ............ {len(cods_fato):,}")
    log(f"clientes na Hierarquia_Consolidada .... {len(cods_est):,}")
    log(f"casam pela chave ...................... {len(inter):,} "
        f"({len(inter) / max(len(cods_fato), 1):.1%} dos que faturam)")
    if len(inter) / max(len(cods_fato), 1) > 0.5:
        log("a chave esta casando normalmente — a queda e de CONTEUDO da "
            "base (linhas removidas), nao de formato de codigo", "ok")
    else:
        log("a chave NAO esta casando — investigar `digitos()` antes de "
            "qualquer decisao de negocio", "erro")

    titulo("FIM — nada foi alterado")
    log("Nenhum Parquet, cubo, base ou config foi tocado por este script.")
    log("As duas listas novas estao em data/quality/ e podem ser apagadas.")
    L.fechar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
