# -*- coding: utf-8 -*-
"""Reestruturação da hierarquia (D-50): reatribuição RTM + saneamento.

Duas regras, aplicadas NA DIM_CLIENTE (a fato nunca é tocada — o histórico
segue nas linhas do próprio cliente, e é o join com a dimensão que decide a
quem ele aparece atribuído):

RTM (Step 4, decisões Q2-b/Q3/Q4-a)
    Cliente da base RTM-Transicao passou a ser atendido por distribuidor. O
    sell-in dele — histórico E futuro — carrega a hierarquia (N1..N4), o
    projeto e o canal do DISTRIBUIDOR; bandeira, UF e o próprio código do
    cliente são PRESERVADOS na linha (a aba Bandeiras não perde histórico).
    Cliente RTM sem código de distribuidor (placeholders "NOVO ...") fica
    FORA da hierarquia, com flag e lista de exceção — canal original mantido,
    nada inventado.

SANEAMENTO (Step 5, decisões Q5/Q6/Q7-i)
    Cliente da base Hierarquia_Clientes_Faltando com HIERARQUIA=NÃO e SEM
    sell-in na janela (`saneamento.janela_meses`, ancorada na última
    competência FECHADA — decisão Q6) é INATIVO: os níveis N1..N4 recebem o
    `rotulo_inativo` (balde próprio, a linha síntese "fora da hierarquia" da
    matriz), o histórico permanece em TODOS os totais (Q7-i) e a flag carrega
    motivo e data. HIERARQUIA=NÃO **com** sell-in na janela é o caso NÃO
    COBERTO do prompt: nada é aplicado, o cliente sai listado para decisão
    (Q5). HIERARQUIA=SIM deve estar na Hierarquia_Consolidada — quem não
    estiver vira aviso, nunca vínculo inferido.

Precedência (5.4): cliente presente nas DUAS bases segue a regra RTM e o
conflito é reportado. Medido em 02/09/2026: interseção zero.
"""
from __future__ import annotations

import pandas as pd

from ..utils.config import CFG
from ..utils.log import INICIO, log

_SAN = CFG.get("saneamento") or {}
_ROT_INATIVO = CFG["dimensoes"].get("rotulo_inativo", "INATIVO (SANEAMENTO)")
_NIVEIS = ["HEAD", "GERENTE", "SUPERVISOR", "VENDEDOR"]
_HERDA_DO_DISTRIBUIDOR = _NIVEIS + ["PROJETO", "CANAL", "SUBCANAL",
                                    "NA_ESTRUTURA", "TEM_CANAL"]

_COLS_NOVAS = {
    "ORIGEM_RTM": False,            # cliente veio da base RTM-Transicao
    "COD_DISTRIBUIDOR": pd.NA,      # a quem o sell-in foi reatribuido
    "DISTRIBUIDOR": pd.NA,          # nome reduzido (da base RTM)
    "CANAL_ORIGINAL": pd.NA,        # canal ANTES da reatribuicao (rastreio)
    "INATIVO": False,               # regra 5.2 aplicada
    "MOTIVO_INATIVO": pd.NA,
    "DATA_INATIVACAO": pd.NA,
    "SANEAMENTO_PENDENTE": False,   # HIERARQUIA=NAO com sell-in na janela (Q5)
}


def _mes_menos(am: str, k: int) -> str:
    total = int(am[:4]) * 12 + (int(am[5:7]) - 1) - k
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def _janela(fato: pd.DataFrame, mes_execucao: str) -> list[str]:
    """Os N meses-CALENDARIO da janela de inatividade, ancorados na última
    competência FECHADA (a última do fato ESTRITAMENTE anterior ao mês da
    execução). A janela é de calendário, não de posições na série: um buraco
    de faturamento no meio não a estica para trás."""
    n = int(_SAN.get("janela_meses", 6))
    ancora_cfg = str(_SAN.get("ancora_janela", "ultima_competencia_fechada"))
    meses = sorted(fato["ANO_MES"].dropna().unique())
    if ancora_cfg != "ultima_competencia_fechada":
        # So o modo decidido (Q6) esta implementado — valor estranho no config
        # nao pode escolher outra regra em silencio.
        log(f"saneamento.ancora_janela='{ancora_cfg}' nao implementado — "
            "usando 'ultima_competencia_fechada'", "aviso")
    fechados = [m for m in meses if m < mes_execucao]
    if not fechados:
        return []
    ancora = fechados[-1]
    return [_mes_menos(ancora, k) for k in range(n - 1, -1, -1)]


def aplicar(dim_cli: pd.DataFrame, rtm: pd.DataFrame, faltando: pd.DataFrame,
            fato: pd.DataFrame,
            mes_execucao: str | None = None) -> tuple[pd.DataFrame, dict, list[str]]:
    """Devolve (dim_cliente ajustada, medidas p/ o relatório, avisos)."""
    avisos: list[str] = []
    d = dim_cli.copy()
    for col, padrao in _COLS_NOVAS.items():
        d[col] = padrao
        if padrao is pd.NA:
            d[col] = d[col].astype("string")
    if mes_execucao is None:
        mes_execucao = pd.Timestamp(INICIO).strftime("%Y-%m")

    medidas: dict = {"janela": [], "ancora": None}

    # ---------------------------------------------- precedencia RTM x Step 5
    cods_rtm = set(rtm["COD_CLIENTE"].dropna()) if len(rtm) else set()
    if len(faltando):
        conflito = sorted(cods_rtm & set(faltando["COD_CLIENTE"].dropna()))
        if conflito:
            msg = (f"{len(conflito)} cliente(s) nas DUAS bases (RTM-Transicao "
                   f"e Faltando) — vale a regra RTM; ex.: {conflito[:5]}")
            log(msg, "aviso")
            avisos.append(msg)
            faltando = faltando[~faltando["COD_CLIENTE"].isin(cods_rtm)]
        medidas["conflito_rtm_saneamento"] = len(conflito)

    # -------------------------------------------------- RTM (Step 4, D-50)
    if len(rtm):
        idx_cli = d.set_index("COD_CLIENTE").index
        rtm_no_painel = rtm[rtm["COD_CLIENTE"].isin(idx_cli)]
        fora = len(rtm) - len(rtm_no_painel)
        if fora:
            msg = (f"{fora} cliente(s) da base RTM sem nenhuma linha de "
                   "sell-in — nada a reatribuir para eles")
            log(msg, "aviso")
            avisos.append(msg)

        dist = d.set_index("COD_CLIENTE")
        com_dist = rtm_no_painel.dropna(subset=["COD_DISTRIBUIDOR"])
        # Distribuidor precisa existir na DIM (ter sell-in) para ceder o
        # perfil; quem nao existe vira excecao junto com os sem-codigo.
        existe = com_dist["COD_DISTRIBUIDOR"].isin(idx_cli)
        if (~existe).any():
            perdidos = sorted(com_dist.loc[~existe, "DISTRIBUIDOR"].unique())
            msg = (f"{int((~existe).sum())} cliente(s) RTM apontam para "
                   f"distribuidor SEM sell-in ({perdidos[:5]}) — tratados "
                   "como sem distribuidor (excecao)")
            log(msg, "aviso")
            avisos.append(msg)
        sem_dist = pd.concat([rtm_no_painel[rtm_no_painel["COD_DISTRIBUIDOR"].isna()],
                              com_dist[~existe]])
        com_dist = com_dist[existe]

        mapa = com_dist.set_index("COD_CLIENTE")
        alvo = d["COD_CLIENTE"].isin(mapa.index)
        d.loc[alvo, "CANAL_ORIGINAL"] = d.loc[alvo, "CANAL"]
        cod_dist = d.loc[alvo, "COD_CLIENTE"].map(mapa["COD_DISTRIBUIDOR"])
        for col in _HERDA_DO_DISTRIBUIDOR:
            d.loc[alvo, col] = cod_dist.map(dist[col]).values
        d.loc[alvo, "ORIGEM_RTM"] = True
        d.loc[alvo, "COD_DISTRIBUIDOR"] = cod_dist.values
        d.loc[alvo, "DISTRIBUIDOR"] = d.loc[alvo, "COD_CLIENTE"].map(
            mapa["DISTRIBUIDOR"]).values

        alvo_sem = d["COD_CLIENTE"].isin(set(sem_dist["COD_CLIENTE"]))
        d.loc[alvo_sem, "ORIGEM_RTM"] = True
        d.loc[alvo_sem, "DISTRIBUIDOR"] = d.loc[alvo_sem, "COD_CLIENTE"].map(
            rtm.set_index("COD_CLIENTE")["DISTRIBUIDOR"]).values

        medidas["rtm_reatribuidos"] = int(alvo.sum())
        medidas["rtm_sem_distribuidor"] = int(alvo_sem.sum())
        medidas["rtm_distribuidores"] = int(mapa["COD_DISTRIBUIDOR"].nunique())
        log(f"RTM: {int(alvo.sum()):,} clientes reatribuidos a "
            f"{medidas['rtm_distribuidores']} distribuidores · "
            f"{int(alvo_sem.sum()):,} sem distribuidor ficam FORA da "
            "hierarquia (excecao listada)", "ok")

    # -------------------------------------------- saneamento (Step 5, D-50)
    if len(faltando):
        janela = _janela(fato, mes_execucao)
        medidas["janela"] = janela
        medidas["ancora"] = janela[-1] if janela else None
        ativos = set(fato.loc[fato["ANO_MES"].isin(janela), "COD_CLIENTE"]) \
            if janela else set()

        h = faltando.set_index("COD_CLIENTE")["HIERARQUIA"].fillna("")
        sim = set(h[h == "SIM"].index)
        nao = set(h[h.isin(["NÃO", "NAO"])].index)

        # SIM: tem de estar na consolidada (NA_ESTRUTURA). Vinculo NUNCA e
        # inferido aqui — quem faltar e pendencia do Comercial.
        na_est = d.set_index("COD_CLIENTE")["NA_ESTRUTURA"]
        sim_ok = {c for c in sim if bool(na_est.get(c, False))}
        sim_pend = sim - sim_ok
        if sim_pend:
            msg = (f"{len(sim_pend)} cliente(s) HIERARQUIA=SIM ainda SEM "
                   "vinculo na Hierarquia_Consolidada — pendencia do "
                   "Comercial, nada foi inferido")
            log(msg, "aviso")
            avisos.append(msg)
        medidas["sim_total"] = len(sim)
        medidas["sim_pendentes"] = len(sim_pend)

        # NAO: as DUAS condicoes ao mesmo tempo (5.2). Presenca na janela e
        # presenca em QUALQUER linha do fato — devolucao tambem e atividade.
        inativar = (nao - ativos) & set(d["COD_CLIENTE"])
        pendentes = (nao & ativos) & set(d["COD_CLIENTE"])
        al_in = d["COD_CLIENTE"].isin(inativar)
        for col in _NIVEIS:
            d.loc[al_in, col] = _ROT_INATIVO
        d.loc[al_in, "INATIVO"] = True
        d.loc[al_in, "MOTIVO_INATIVO"] = (
            f"HIERARQUIA=NAO e sem sell-in em "
            f"{janela[0] if janela else '?'}..{janela[-1] if janela else '?'}")
        d.loc[al_in, "DATA_INATIVACAO"] = pd.Timestamp(INICIO).strftime("%Y-%m-%d")
        d.loc[d["COD_CLIENTE"].isin(pendentes), "SANEAMENTO_PENDENTE"] = True

        medidas["inativados"] = len(inativar)
        medidas["nao_cobertos"] = len(pendentes)
        log(f"saneamento (janela {janela[0] if janela else '?'}.."
            f"{janela[-1] if janela else '?'}): {len(inativar):,} inativados "
            f"(fora da matriz; historico permanece nos totais) · "
            f"{len(pendentes):,} HIERARQUIA=NAO COM sell-in na janela — caso "
            "nao coberto, listado para decisao", "ok")

    return d, medidas, avisos
