# -*- coding: utf-8 -*-
"""ANALISE da bandeira dos clientes reatribuidos pelo RTM (03/09/2026, D-59).

    python ferramentas/analise_bandeira_rtm.py

Ferramenta de medicao (nao e etapa do pipeline). NAO altera base, config,
cubo, Parquet nem painel: so le, mede e imprime. Escreve UMA lista em
data/quality/ para consulta. Foi a medida que embasou a D-59; fica como
rollback de medida (rodar com `rtm_herda_bandeira: false` reproduz o "antes").
Nota: a simulacao daqui usa a bandeira do CADASTRO ("DIST. X"); a
implementacao usa a do distribuidor na DIM (sell-in). Os dois caminhos deram
66 bandeiras para o head de Distribuicao.

A PERGUNTA
----------
A decisao Q4-a da D-50 diz que, na reatribuicao RTM, o cliente herda do
DISTRIBUIDOR a hierarquia, o projeto e o canal — mas a BANDEIRA e a UF sao
PRESERVADAS do cliente original. O motivo declarado: "a aba Bandeiras nao
perde historico".

Efeito colateral observado pelo Douglas em 03/09: o painel do head de
Distribuicao mostra as bandeiras dos PONTOS FINAIS (mercadinhos, padarias),
nao os distribuidores que sao os clientes dele. Medido nas bases: 89 clientes
proprios contra 1.596 clientes RTM, que trazem 1.054 bandeiras.

O QUE ESTE SCRIPT MEDE
----------------------
  1. quanto do faturamento de cada head vem de cliente proprio e quanto vem
     de cliente RTM — e se isso e historico ou corrente (a reatribuicao pega
     o passado; o cliente RTM nao compra mais direto da Dori);
  2. quantas bandeiras cada head ve hoje, e quanto do faturamento dele fica
     na linha sintese Σ em vez de aparecer nominalmente;
  3. a SIMULACAO da alternativa: e se o cliente RTM herdasse tambem a
     bandeira do distribuidor? O cadastro do Comercial ja nomeia cada
     distribuidor ("DIST. CLAUMAR", "DIST. CHUA") — nada precisaria ser
     inventado;
  4. o CUSTO dessa alternativa no painel corporativo: quais bandeiras de
     ponto final perderiam faturamento, e quanto.

Nada e decidido aqui. O script produz os numeros; a decisao e de negocio.
"""
from __future__ import annotations

import sys
from pathlib import Path

# O script mora em ferramentas/, fora da raiz: a raiz entra no path para os
# imports de src/ funcionarem de qualquer pasta.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

for _fluxo in (sys.stdout, sys.stderr):
    try:
        _fluxo.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

import pandas as pd

from src.extract import cadastros, sellin
from src.transform import calendario, dimensoes, fato as fato_mod, saneamento
from src.utils import log as L
from src.utils.config import CFG, caminho
from src.utils.log import log, titulo

PASTA_Q = caminho(CFG["projeto"]["pasta_dados"]) / "quality"
TOP = int(CFG["dashboard"]["top_bandeiras"])
ROT_DEMAIS = CFG["dashboard"]["rotulo_demais_bandeiras"]


def br(v: float, c: int = 2) -> str:
    return f"{v:,.{c}f}".replace(",", "@").replace(".", ",").replace("@", ".")


def _cobertura_nominal(rec_por_ban: pd.Series, top: int) -> tuple[int, float]:
    """Quantas bandeiras entram nominalmente e que fatia da receita elas
    cobrem, sob o MESMO corte que o cubo aplica (as N maiores da base)."""
    n = min(top, len(rec_por_ban))
    return n, float(rec_por_ban.nlargest(n).sum() / rec_por_ban.sum()) \
        if rec_por_ban.sum() else (n, 1.0)


def main() -> int:
    L.abrir()
    titulo("ANALISE · bandeira dos clientes reatribuidos pelo RTM")

    bruto, meta = sellin.ler()
    estrutura, _ = cadastros.ler_estrutura()
    canais, _ = cadastros.ler_canais()
    rtm, _ = cadastros.ler_rtm()
    faltando, _ = cadastros.ler_faltando()

    f = fato_mod.construir(bruto)
    dim_cli = dimensoes.dim_cliente(bruto, estrutura, canais)
    del bruto
    dim_cli, _, _ = saneamento.aplicar(dim_cli, rtm, faltando, f)

    d = dim_cli.set_index("COD_CLIENTE")
    f = f.copy()
    for col in ("HEAD", "BANDEIRA", "ORIGEM_RTM", "COD_DISTRIBUIDOR"):
        f[col] = f["COD_CLIENTE"].map(d[col])
    f["ORIGEM_RTM"] = f["ORIGEM_RTM"].fillna(False)

    total = float(f["RECEITA"].sum())
    meses = sorted(f["ANO_MES"].dropna().unique())
    ult6 = meses[-7:-1] if len(meses) > 6 else meses     # 6 fechados

    # ------------------------------------------------ 1. proprio x RTM
    titulo("1 · de onde vem o faturamento de cada head")
    log(f"janela 'recente' = {ult6[0]} a {ult6[-1]} (6 competencias fechadas)")
    log("")
    log(f"{'HEAD':<38} {'TOTAL':>18} {'RTM':>18} {'RTM %':>7} {'RTM recente':>16}")
    for head, g in f.groupby("HEAD", dropna=False):
        t = float(g["RECEITA"].sum())
        r = float(g.loc[g["ORIGEM_RTM"], "RECEITA"].sum())
        rec = float(g.loc[g["ORIGEM_RTM"] & g["ANO_MES"].isin(ult6),
                          "RECEITA"].sum())
        log(f"{str(head)[:38]:<38} {br(t):>18} {br(r):>18} "
            f"{(r / t if t else 0):>6.1%} {br(rec):>16}")
    log("")
    log("A coluna 'RTM recente' responde se a poluicao e historica: o cliente")
    log("RTM nao compra mais direto da Dori — o sell-in dele so cresce pelo")
    log("distribuidor. Valor baixo aqui = as bandeiras dos pontos finais sao")
    log("passado congelado dentro do painel do head.")

    # ------------------------------------- 2. quantas bandeiras cada head ve
    titulo("2 · bandeiras por head HOJE (regra atual, Q4-a)")
    log(f"{'HEAD':<38} {'BANDEIRAS':>10} {'NOMINAIS':>9} {'COBERTURA':>10} "
        f"{'NO BALDE Σ':>18}")
    for head, g in f.groupby("HEAD", dropna=False):
        rp = g.groupby("BANDEIRA")["RECEITA"].sum()
        rp = rp[rp.notna()]
        n, cob = _cobertura_nominal(rp, TOP)
        balde = float(rp.sum() - rp.nlargest(n).sum())
        log(f"{str(head)[:38]:<38} {len(rp):>10,} {n:>9,} {cob:>9.1%} "
            f"{br(balde):>18}")
    log("")
    log(f"'NOMINAIS' e o corte de {TOP} do config aplicado ao recorte do head;")
    log("no painel real o corte e GLOBAL (as mesmas N maiores da base em todo")
    log("arquivo), entao o numero de nominais de um head e menor que este.")

    # ------------------------------- 3. simulacao: bandeira do distribuidor
    titulo("3 · SIMULACAO — e se o cliente RTM herdasse a bandeira do distribuidor?")
    # O cadastro do Comercial ja nomeia o distribuidor ("DIST. X") na coluna
    # BANDEIRA da Hierarquia_Consolidada, lida como BANDEIRA_ESTRUTURA.
    ban_est = d["BANDEIRA_ESTRUTURA"] if "BANDEIRA_ESTRUTURA" in d.columns \
        else pd.Series(dtype="object")
    f["BAN_SIM"] = f["BANDEIRA"]
    tem_dist = f["ORIGEM_RTM"] & f["COD_DISTRIBUIDOR"].notna()
    nova = f.loc[tem_dist, "COD_DISTRIBUIDOR"].map(ban_est)
    # Sem bandeira de cadastro para o distribuidor, mantem a do ponto final —
    # nunca inventar rotulo.
    f.loc[tem_dist, "BAN_SIM"] = nova.fillna(f.loc[tem_dist, "BANDEIRA"])
    sem_cad = int(nova.isna().sum())
    if sem_cad:
        log(f"aviso: {sem_cad:,} linha(s) de cliente RTM cujo distribuidor NAO "
            "tem bandeira no cadastro — ficam com a bandeira atual", "aviso")

    log("")
    log(f"{'HEAD':<38} {'HOJE':>10} {'SIMULADO':>10} {'DIFERENCA':>11}")
    for head, g in f.groupby("HEAD", dropna=False):
        a = g["BANDEIRA"].nunique()
        b = g["BAN_SIM"].nunique()
        log(f"{str(head)[:38]:<38} {a:>10,} {b:>10,} {b - a:>+11,}")
    log("")
    log(f"universo de bandeiras da base: {f['BANDEIRA'].nunique():,} hoje -> "
        f"{f['BAN_SIM'].nunique():,} simulado")

    # ------------------------------------------------ 4. o custo da mudanca
    titulo("4 · CUSTO — bandeiras de ponto final que perderiam faturamento")
    hoje = f.groupby("BANDEIRA")["RECEITA"].sum()
    sim = f.groupby("BAN_SIM")["RECEITA"].sum()
    perda = (hoje - sim.reindex(hoje.index).fillna(0)).sort_values(
        ascending=False)
    perda = perda[perda > 0]
    log(f"{len(perda):,} bandeiras perderiam faturamento para os rotulos "
        f"'DIST. ...'")
    log(f"receita que muda de rotulo: R$ {br(float(perda.sum()))} "
        f"({perda.sum() / total:.2%} do total)")
    log("")
    log("as 20 maiores perdas (o que o painel corporativo deixaria de ver):")
    log(f"  {'BANDEIRA':<40} {'PERDE':>18} {'FICA':>18}")
    for ban, v in perda.head(20).items():
        fica = float(hoje[ban] - v)
        log(f"  {str(ban)[:40]:<40} {br(float(v)):>18} {br(fica):>18}")

    alvo = PASTA_Q / "analise_bandeira_rtm_perdas.csv"
    pd.DataFrame({"BANDEIRA": perda.index, "RECEITA_QUE_MUDA_DE_ROTULO": perda.values,
                  "RECEITA_QUE_PERMANECE": (hoje.reindex(perda.index) - perda).values
                  }).to_csv(alvo, sep=";", index=False, encoding="utf-8-sig",
                            decimal=",", float_format="%.2f")
    log("")
    log(f"lista completa -> {alvo}", "ok")

    # ------------------------------------------------------- 5. o resumo
    titulo("5 · o que decidir")
    log("MANTER (Q4-a como esta):")
    log("  + nenhuma bandeira perde historico; o painel corporativo continua")
    log("    somando cada ponto final sob o proprio nome")
    log("  - o head de Distribuicao ve os pontos finais, nao os clientes dele")
    log("")
    log("HERDAR a bandeira do distribuidor:")
    log("  + o painel do head passa a falar dos clientes REAIS dele")
    log("  + o rotulo ja existe no cadastro do Comercial ('DIST. X')")
    log("  - a receita medida no item 4 sai das bandeiras de ponto final em")
    log("    TODOS os paineis, inclusive o corporativo — quem acompanha uma")
    log("    rede especifica deixa de ver a parte vendida via distribuidor")
    log("")
    log("Os numeros acima dizem o tamanho de cada lado. Nada foi alterado.")
    L.fechar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
