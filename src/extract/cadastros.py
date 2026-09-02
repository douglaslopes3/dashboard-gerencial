# -*- coding: utf-8 -*-
"""Leitura dos cadastros: produtos e estrutura comercial.

Aqui — e só aqui — as correções DECLARADAS no config são aplicadas. Corrigir num
passo só faria os outros lerem outra verdade: foi assim que o projeto anterior
quebrou o pipeline em 24/08/2026, quando um passo já via o head novo e outro
ainda via o antigo.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from ..utils.config import CFG, PASTA_QUALITY, caminho
from ..utils.log import abortar, log
from ..utils.texto import digitos, texto
from . import cache

_PROD = CFG["fontes"]["produtos"]
_EST = CFG["fontes"]["estrutura_comercial"]
_CAN = CFG["fontes"]["canais"]
_DIMCFG = CFG["dimensoes"]["estrutura_comercial"]


def _ler_aba(arq: Path, aba: str, chave_cfg: str,
             dtype=None) -> pd.DataFrame:
    """C3 (auditoria): aba errada/renomeada vira 'arquivo REJEITADO' com
    diagnostico e a chave do config — nao traceback cru do calamine. A aba da
    estrutura chama 'Planilha1', nome default que muda na primeira vez que
    alguem regravar o arquivo."""
    try:
        df = pd.read_excel(arq, sheet_name=aba, engine="calamine", dtype=dtype)
    except Exception as e:                                   # noqa: BLE001
        abortar(f"arquivo REJEITADO: {arq.name}\n"
                f"  nao foi possivel ler a aba '{aba}': {e}\n"
                f"  (config/config.yaml -> fontes.{chave_cfg}.aba)")
    # A Hierarquia_Consolidada traz QUEBRA DE LINHA dentro dos cabecalhos
    # ("CÓDIGO\nCLIENTE") — todo espacamento vira um espaco antes de validar,
    # e os nomes no config ja estao nessa forma.
    df.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in df.columns]
    return df


def _validar(df: pd.DataFrame, obrig: list[str], arq: Path) -> None:
    faltando = [c for c in obrig if c not in df.columns]
    if faltando:
        abortar(f"arquivo REJEITADO: {arq.name}\n"
                f"  colunas obrigatorias ausentes: {faltando}\n"
                f"  colunas encontradas         : {list(df.columns)}")


# ---------------------------------------------------------------- PRODUTOS
def _ler_produtos(arq: Path) -> tuple[pd.DataFrame, dict]:
    df = _ler_aba(arq, _PROD["aba"], "produtos")
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
    df = _ler_aba(arq, _CAN["aba"], "canais", dtype=str)
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
    avisos += _conferir_assinatura_canais(extra.get("filtro"))
    if extra.get("conflitos"):
        msg = (f"{extra['conflitos']} cliente(s) com DOIS canais no de-para — "
               "vale a 1a linha; confira o arquivo")
        log(msg, "aviso")
        avisos.append(msg)
    log(f"canais: {len(can):,} clientes · {can['CANAL'].nunique()} canais")
    return can, avisos


def _conferir_assinatura_canais(filtro: str | None) -> list[str]:
    """A14: o rodapé do `Canais.xlsx` declara o RECORTE da extração — e nada o
    comparava entre execuções (ao contrário do sell-in). Se o BI reextrair o
    de-para com outro recorte, o universo de canais muda em silêncio e o piso
    de 95% só pega queda grande. A assinatura fica guardada em
    `data/quality/assinatura_extracao_canais.txt`; mudança vira AVISO (o
    arquivo tem dono no BI — a correção é lá, não aqui)."""
    avisos: list[str] = []
    atual = " | ".join(str(filtro or "").split("\n")).strip().casefold()
    alvo = PASTA_QUALITY / "assinatura_extracao_canais.txt"
    PASTA_QUALITY.mkdir(parents=True, exist_ok=True)
    if alvo.exists():
        anterior = alvo.read_text(encoding="utf-8").strip()
        if anterior != atual:
            msg = ("o recorte de extracao do Canais.xlsx MUDOU desde a ultima "
                   f"execucao.\n  anterior: {anterior[:160] or '(vazio)'}\n"
                   f"  atual   : {atual[:160] or '(vazio)'}\n"
                   "  O universo de canais pode ter mudado — confira com o BI.")
            log(msg, "aviso")
            avisos.append(msg)
    alvo.write_text(atual, encoding="utf-8")
    return avisos


# ------------------------------------------------------- ESTRUTURA COMERCIAL
# Cada nivel da Hierarquia_Consolidada vira UM rotulo: codigo + papel + nome,
# unidos por " - " (D-34). A parte vazia e omitida — ha 106 linhas de gerente
# sem nome, e o codigo+papel seguram o rotulo sozinhos.
_NIVEIS = {
    "HEAD": ["(N1) CÓDIGO HEAD", "CRIAR NO BI (N1) HEAD", "(N1) NOME HEAD"],
    "GERENTE": ["(N2) CÓDIGO GERENTE", "(N2) GERENTE", "(N2) NOME GERENTE"],
    "SUPERVISOR": ["(N3) CÓDIGO SUP./EXEC.", "(N3) SUP./EXEC.",
                   "(N3) NOME SUP./EXEC."],
}


def _rotulo_concatenado(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    out: pd.Series | None = None
    for c in cols:
        s = texto(df[c], maiuscula=False)
        out = s.fillna("") if out is None else out + (" - " + s).fillna("")
    return out.str.strip(" -").replace({"": pd.NA})


def _ler_estrutura(arq: Path) -> tuple[pd.DataFrame, dict]:
    df = _ler_aba(arq, _EST["aba"], "estrutura_comercial", dtype=str)
    _validar(df, _EST["colunas_obrigatorias"], arq)

    out = pd.DataFrame(index=df.index)
    # O sell-in traz o numero puro ("1010846") — a base anterior vinha
    # zero-preenchida e a atual nao; `digitos()` cobre as duas.
    out["COD_CLIENTE"] = digitos(df["CÓDIGO CLIENTE"])
    for destino, cols in _NIVEIS.items():
        out[destino] = _rotulo_concatenado(df, cols)
    if "PROJETO" in df.columns:
        out["PROJETO"] = texto(df["PROJETO"], maiuscula=False)
    # D-42: a hierarquia carrega o cadastro de bandeiras do Comercial (serie
    # 82xxxxx). Nasceu como ponte por codigo com a base de metas antiga; desde
    # a D-49 e ATRIBUTO do cadastro, sem funcao de join. O nome vai junto como
    # BANDEIRA_ESTRUTURA para nao colidir com a BANDEIRA do sell-in (grafias
    # divergem em 9% dos clientes — o rotulo de tela continua sendo o do
    # sell-in). Cliente sem as colunas fica <NA>, nunca inventado.
    if "CÓDIGO BANDEIRA" in df.columns:
        out["COD_BANDEIRA"] = digitos(df["CÓDIGO BANDEIRA"])
    if "BANDEIRA" in df.columns:
        out["BANDEIRA_ESTRUTURA"] = texto(df["BANDEIRA"])

    sem_chave = out["COD_CLIENTE"].isna()
    if sem_chave.any():
        # C12 (auditoria): mostrar o valor CRU descartado — o dono do arquivo
        # so corrige o que consegue ver. (Na Hierarquia_Consolidada sao 71
        # linhas de codigo vazio carregando estrutura real da Izabela.)
        crus = sorted(set(df.loc[sem_chave, "CÓDIGO CLIENTE"]
                          .astype("string").fillna("(vazio)")))[:6]
        log(f"de-para de estrutura: {int(sem_chave.sum())} linha(s) sem "
            f"CÓDIGO CLIENTE aproveitavel, descartadas — valores crus: "
            f"{crus}", "aviso")
    # A granularidade do arquivo e cliente x VENDEDOR (nivel N4, nao ingerido):
    # linhas repetidas por cliente sao esperadas e os niveis N1-N3 nao
    # conflitam (medido em 28/08/2026: zero conflitos). A deduplicacao e a
    # checagem de conflito ficam em `ler_estrutura`, depois das correcoes.
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

    # O COMPLEMENTO (D-34) foi aposentado na D-49 (02/09/2026): o arquivo saiu
    # de bases/ em definitivo e os clientes dele viraram as bases RTM-Transicao
    # e Hierarquia_Clientes_Faltando, tratadas na Fase 2 da reestruturacao.

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
    # COD_BANDEIRA entra na checagem (medido em 01/09/2026: zero clientes com
    # dois codigos) — se um dia conflitar, vale a 1a linha COM AVISO, igual aos
    # niveis da estrutura.
    for coluna in ("HEAD", "SUPERVISOR", "COD_BANDEIRA"):
        if coluna not in est.columns:
            continue
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
