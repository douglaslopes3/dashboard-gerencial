# -*- coding: utf-8 -*-
"""Leitura dos cadastros: produtos e estrutura comercial.

Aqui — e só aqui — as correções DECLARADAS no config são aplicadas. Corrigir num
passo só faria os outros lerem outra verdade: foi assim que o projeto anterior
quebrou o pipeline em 24/08/2026, quando um passo já via o head novo e outro
ainda via o antigo.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..utils.config import CFG, caminho
from ..utils.log import abortar, log
from ..utils.texto import digitos, texto
from . import cache

_PROD = CFG["fontes"]["produtos"]
_EST = CFG["fontes"]["estrutura_comercial"]
_CAN = CFG["fontes"]["canais"]
_DIMCFG = CFG["dimensoes"]["estrutura_comercial"]


def _validar(df: pd.DataFrame, obrig: list[str], arq: Path) -> None:
    faltando = [c for c in obrig if c not in df.columns]
    if faltando:
        abortar(f"arquivo REJEITADO: {arq.name}\n"
                f"  colunas obrigatorias ausentes: {faltando}\n"
                f"  colunas encontradas         : {list(df.columns)}")


# ---------------------------------------------------------------- PRODUTOS
def _ler_produtos(arq: Path) -> tuple[pd.DataFrame, dict]:
    df = pd.read_excel(arq, sheet_name=_PROD["aba"], engine="calamine")
    df.columns = [str(c).strip() for c in df.columns]
    _validar(df, _PROD["colunas_obrigatorias"], arq)

    out = pd.DataFrame(index=df.index)
    out["COD_PRODUTO"] = digitos(df["Código Produto"])
    out["DESCRICAO_PRODUTO"] = texto(df["Descrição Produto"])
    out["CATEGORIA"] = texto(df["Categoria"])
    # MARCA vem do CADASTRO. Nunca é inferida da descrição: um corte por marca na
    # tela seria indistinguível de um corte por dado de origem, e alguem acabaria
    # cobrando meta em cima de uma marca inventada por regex.
    out["MARCA"] = (texto(df["Marca"]) if "Marca" in df.columns
                    else pd.Series(pd.NA, index=df.index, dtype="string"))
    return out.dropna(subset=["COD_PRODUTO"]).reset_index(drop=True), {}


def ler_produtos() -> pd.DataFrame:
    arq = caminho(_PROD["arquivo"])
    if not arq.exists():
        abortar(f"cadastro de produtos nao encontrado: {arq}\n"
                "  (config/config.yaml -> fontes.produtos.arquivo)")
    d = cache.ler(arq, _ler_produtos)[0]
    if not d["MARCA"].notna().any():
        log("cadastro de produtos sem coluna/valor de marca — MARCA fica vazia "
            "(nao e inferida da descricao)", "aviso")
    return d


# ------------------------------------------------------------------ CANAIS
def _ler_canais(arq: Path) -> tuple[pd.DataFrame, dict]:
    """De-para Cliente -> Canal (`bases/Canais/Canais.xlsx`).

    Duas coisas que este arquivo tem em comum com as outras fontes, e que
    precisam do mesmo tratamento:

      - o `Cód. cliente` vem ZERO-PREENCHIDO (`0001000027`) — sem `digitos()`
        o join casa com zero cliente, em silêncio;
      - há um RODAPÉ de `Filtros aplicados` (linhas com o canal nulo) que não é
        dado. O texto do filtro vai para o `extra`, como no sell-in.
    """
    df = pd.read_excel(arq, sheet_name=_CAN["aba"], engine="calamine", dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    _validar(df, _CAN["colunas_obrigatorias"], arq)

    extra: dict = {}
    rodape = df[df["Canal"].isna()]
    filtros = rodape["Cód. cliente"].dropna()
    if len(filtros):
        extra["filtro"] = "\n".join(str(x).strip() for x in filtros)
    df = df[df["Canal"].notna()]

    out = pd.DataFrame(index=df.index)
    out["COD_CLIENTE"] = digitos(df["Cód. cliente"])
    out["CANAL"] = texto(df["Canal"])
    for origem, destino in (("Cód. canal", "COD_CANAL"), ("Subcanal", "SUBCANAL")):
        if origem in df.columns:
            out[destino] = texto(df[origem], maiuscula=False)
    out = out.dropna(subset=["COD_CLIENTE"])

    # Cliente com dois canais tornaria o join ambíguo — hoje são zero (medido),
    # e se aparecer um, o caso vira aviso e vale a 1a linha.
    conflito = out.groupby("COD_CLIENTE")["CANAL"].nunique()
    n_conf = int((conflito > 1).sum())
    if n_conf:
        extra["conflitos"] = n_conf
    out = out.drop_duplicates("COD_CLIENTE", keep="first")
    return out.reset_index(drop=True), extra


def ler_canais() -> tuple[pd.DataFrame, list[str]]:
    """Devolve (canais, avisos). Ausência do arquivo NÃO derruba o pipeline —
    o painel roda sem o eixo de canal, com o aviso registrado."""
    avisos: list[str] = []
    arq = caminho(_CAN["arquivo"])
    if not arq.exists():
        msg = (f"de-para de canais ausente ({arq}) — o painel fica sem o eixo "
               "de canal")
        if _CAN.get("obrigatorio"):
            abortar(msg)
        log(msg, "aviso")
        return pd.DataFrame(columns=["COD_CLIENTE", "CANAL", "SUBCANAL"]), [msg]

    can, extra = cache.ler(arq, _ler_canais)
    if extra.get("conflitos"):
        msg = (f"{extra['conflitos']} cliente(s) com DOIS canais no de-para — "
               "vale a 1a linha; confira o arquivo")
        log(msg, "aviso")
        avisos.append(msg)
    log(f"canais: {len(can):,} clientes · {can['CANAL'].nunique()} canais")
    return can, avisos


# ------------------------------------------------------- ESTRUTURA COMERCIAL
def _ler_estrutura(arq: Path) -> tuple[pd.DataFrame, dict]:
    df = pd.read_excel(arq, sheet_name=_EST["aba"], engine="calamine", dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    _validar(df, _EST["colunas_obrigatorias"], arq)

    out = pd.DataFrame(index=df.index)
    # O arquivo traz o codigo zero-preenchido ("0001010846") e o sell-in traz o
    # numero puro ("1010846"). Ver `digitos()`.
    out["COD_CLIENTE"] = digitos(df["Cód. cliente"])
    out["HEAD"] = texto(df["Novo Head"], maiuscula=False)
    out["GERENTE"] = texto(df["Novo Gerente"], maiuscula=False)
    out["SUPERVISOR"] = texto(df["Novo Supervisor"], maiuscula=False)
    for origem, destino in (("Atendimento Ponta", "ATENDIMENTO_PONTA"),
                            ("PROJETO", "PROJETO")):
        if origem in df.columns:
            out[destino] = texto(df[origem], maiuscula=False)

    sem_chave = int(out["COD_CLIENTE"].isna().sum())
    if sem_chave:
        log(f"de-para de estrutura: {sem_chave} linha(s) sem Cod. cliente, "
            "descartadas", "aviso")
    return out.dropna(subset=["COD_CLIENTE"]).reset_index(drop=True), {}


def ler_estrutura() -> tuple[pd.DataFrame, list[str]]:
    """Devolve (estrutura, avisos). Ausência do arquivo NÃO derruba o pipeline."""
    avisos: list[str] = []
    arq = caminho(_EST["arquivo"])
    if not arq.exists():
        msg = (f"de-para de estrutura comercial ausente ({arq.name}) — todos os "
               "clientes ficam sem head/gerente/supervisor")
        if _EST.get("obrigatorio"):
            abortar(msg)
        log(msg, "aviso")
        return pd.DataFrame(columns=["COD_CLIENTE", "HEAD", "GERENTE",
                                     "SUPERVISOR"]), [msg]

    est = cache.ler(arq, _ler_estrutura)[0]

    # ---- correcoes DECLARADAS -------------------------------------------
    for coluna, chave in (("HEAD", "correcoes_head"),
                          ("GERENTE", "correcoes_gerente"),
                          ("SUPERVISOR", "correcoes_supervisor")):
        mapa = _DIMCFG.get(chave) or {}
        if mapa and coluna in est.columns:
            antes = est[coluna].copy()
            est[coluna] = est[coluna].replace(mapa)
            n = int((est[coluna] != antes).sum())
            if n:
                msg = (f"{n} linha(s) tiveram {coluna} corrigido por "
                       f"`dimensoes.estrutura_comercial.{chave}`: {mapa}")
                log(msg, "ok")
                avisos.append(msg)

    # ---- desempate DECLARADO --------------------------------------------
    desempate = {str(k): v for k, v in (_DIMCFG.get("desempate_cliente") or {}).items()}
    for cod, sup in desempate.items():
        alvo = est["COD_CLIENTE"] == cod
        if not alvo.any():
            msg = (f"desempate declarado para o cliente {cod}, que nao esta no "
                   "de-para — regra ociosa, pode sair do config")
            log(msg, "aviso")
            avisos.append(msg)
            continue
        if not (alvo & (est["SUPERVISOR"] == sup)).any():
            # Aplicar aqui apagaria o cliente inteiro, em silencio.
            msg = (f"desempate do cliente {cod} pede '{sup}', mas o de-para so "
                   f"tem {sorted(est.loc[alvo, 'SUPERVISOR'].dropna().unique())} "
                   "— regra IGNORADA para nao apagar o cliente")
            log(msg, "aviso")
            avisos.append(msg)
            continue
        est = est[~(alvo & (est["SUPERVISOR"] != sup))]

    # ---- conflito NAO resolvido ------------------------------------------
    for coluna in ("HEAD", "SUPERVISOR"):
        n_por_cli = est.groupby("COD_CLIENTE")[coluna].nunique()
        conflito = n_por_cli[n_por_cli > 1]
        if len(conflito):
            msg = (f"{len(conflito)} cliente(s) com {coluna} conflitante no "
                   f"de-para (ex.: {list(conflito.index[:5])}) — vale a 1a linha. "
                   "Declare o desempate em "
                   "`dimensoes.estrutura_comercial.desempate_cliente`")
            log(msg, "aviso")
            avisos.append(msg)

    est = est.drop_duplicates("COD_CLIENTE", keep="first").reset_index(drop=True)
    log(f"estrutura comercial: {len(est):,} clientes")
    return est, avisos
