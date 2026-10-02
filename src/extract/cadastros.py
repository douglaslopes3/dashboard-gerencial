# -*- coding: utf-8 -*-
"""Leitura dos cadastros: produtos e estrutura comercial.

Aqui — e só aqui — as correções DECLARADAS no config são aplicadas. Corrigir num
passo só faria os outros lerem outra verdade: foi assim que o projeto anterior
quebrou o pipeline em 24/08/2026, quando um passo já via o head novo e outro
ainda via o antigo.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from ..utils.config import CFG, PASTA_QUALITY, caminho
from ..utils.log import abortar, log
from ..utils.texto import digitos, texto
from . import cache

_PROD = CFG["fontes"]["produtos"]
_EST = CFG["fontes"]["estrutura_comercial"]
_CAN = CFG["fontes"]["canais"]
_RTM = CFG["fontes"].get("rtm_transicao") or {}
_FALT = CFG["fontes"].get("hierarquia_faltando") or {}
_ECL = CFG["fontes"].get("estrutura_clientes") or {}
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
# D-83 (02/10/2026): a hierarquia oficial e a Hierarquia_AAAAMMDD.xlsx da pasta
# compartilhada com o DN e o ROTA; a bandeira do cadastro vem da Estrutura de
# Clientes_AAAAMMDD.xlsx da mesma pasta. Vale o arquivo de data mais recente no
# NOME; arquivo do padrao sem data AAAAMMDD valida ABORTA (uma copia de conflito
# do OneDrive, "Hierarquia_20261001 (1).xlsx", nao vira desempate silencioso).
def arquivo_datado(cfg: dict, chave_cfg: str) -> Path | None:
    pasta = caminho(cfg["pasta"])
    if not pasta.is_dir():
        return None
    rx = re.compile(cfg["data_regex"])
    datas: dict[datetime, Path] = {}
    fora: list[str] = []
    for a in sorted(pasta.glob(cfg["padrao"])):
        if a.name.startswith("~$"):
            continue
        m = rx.match(a.name)
        try:
            d = datetime.strptime(m.group(1), "%Y%m%d") if m else None
        except ValueError:
            d = None
        if d is None:
            fora.append(a.name)
        else:
            datas[d] = a
    if fora:
        abortar(f"arquivo(s) fora do padrao {cfg['data_regex']} em {pasta}:\n    "
                + "\n    ".join(fora) + "\n  Renomeie para o padrao com a data "
                f"AAAAMMDD ou tire da pasta (config/config.yaml -> fontes.{chave_cfg}).")
    return datas[max(datas)] if datas else None


# Cada nivel vira UM rotulo "codigo - nome" (D-83, mesmo formato do DN e do
# ROTA). O nome e limpo so quando termina com "(codigo)" igual ao codigo da
# linha: sai o "(codigo)" e o "_" inicial. Fora disso entra como veio (ex.:
# "(5000 ) SUP. SPC (KA/VJ)", "KAN_VAGO").
def _nome_limpo(cod: pd.Series, nome: pd.Series) -> tuple[pd.Series, pd.Series]:
    partes = nome.str.extract(r"^_?(.+?)\s*\(\s*(\d+)\s*\)$")
    casa = partes[0].notna() & (partes[1] == cod)
    return nome.where(~casa, partes[0].str.strip()), casa.fillna(False)


def _ler_estrutura(arq: Path) -> tuple[pd.DataFrame, dict]:
    df = _ler_aba(arq, _EST["aba"], "estrutura_comercial", dtype=str)
    niveis = _EST["niveis"]
    _validar(df, [_EST["coluna_cliente"]] + [c for cols in niveis.values() for c in cols], arq)

    out = pd.DataFrame(index=df.index)
    # O sell-in traz o numero puro ("1010846"); `digitos()` cobre zero-preenchido.
    out["COD_CLIENTE"] = digitos(df[_EST["coluna_cliente"]])
    fora_padrao = {}
    for destino, (c_cod, c_nome) in niveis.items():
        cod = texto(df[c_cod], maiuscula=False)
        nome, limpo = _nome_limpo(cod, texto(df[c_nome], maiuscula=False))
        out[destino] = (cod.fillna("") + (" - " + nome).fillna("")).str.strip(" -").replace({"": pd.NA})
        fora_padrao[destino] = int(out.loc[~limpo, destino].dropna().nunique())

    sem_chave = out["COD_CLIENTE"].isna()
    if sem_chave.any():
        # C12 (auditoria): mostrar o valor CRU descartado.
        crus = sorted(set(df.loc[sem_chave, _EST["coluna_cliente"]]
                          .astype("string").fillna("(vazio)")))[:6]
        log(f"hierarquia: {int(sem_chave.sum())} linha(s) sem codigo de cliente "
            f"aproveitavel, descartadas — valores crus: {crus}", "aviso")
    # Medido em 02/10/2026: 1 linha por cliente. A deduplicacao e a checagem de
    # conflito continuam em `ler_estrutura`, depois das correcoes.
    return out.dropna(subset=["COD_CLIENTE"]).reset_index(drop=True), {"fora_padrao_nome": fora_padrao}


def _ler_estrutura_clientes(arq: Path) -> tuple[pd.DataFrame, dict]:
    df = _ler_aba(arq, _ECL["aba"], "estrutura_clientes", dtype=str)
    _validar(df, [_ECL["coluna_cliente"], _ECL["coluna_cod_bandeira"], _ECL["coluna_bandeira"]], arq)
    out = pd.DataFrame(index=df.index)
    out["COD_CLIENTE"] = digitos(df[_ECL["coluna_cliente"]])
    # D-42: cadastro de bandeiras do Comercial. O nome vai como BANDEIRA_ESTRUTURA
    # para nao colidir com a BANDEIRA do sell-in (o rotulo de tela segue o sell-in).
    out["COD_BANDEIRA"] = digitos(df[_ECL["coluna_cod_bandeira"]])
    out["BANDEIRA_ESTRUTURA"] = texto(df[_ECL["coluna_bandeira"]])
    out = out.dropna(subset=["COD_CLIENTE"])
    return out.drop_duplicates("COD_CLIENTE", keep="first").reset_index(drop=True), {}


def ler_estrutura() -> tuple[pd.DataFrame, list[str]]:
    """Devolve (estrutura, avisos). Ausência do arquivo NÃO derruba o pipeline."""
    avisos: list[str] = []
    arq = arquivo_datado(_EST, "estrutura_comercial")
    if arq is None:
        msg = (f"hierarquia ausente ({_EST['padrao']} em {_EST['pasta']}) — todos os "
               "clientes ficam sem head/gerente/supervisor")
        if _EST.get("obrigatorio"):
            abortar(msg)
        log(msg, "aviso")
        return pd.DataFrame(columns=["COD_CLIENTE", "HEAD", "GERENTE",
                                     "SUPERVISOR"]), [msg]
    log(f"hierarquia vigente: {arq.name} (data mais recente em {arq.parent.name})", "ok")
    est, extra = cache.ler(arq, _ler_estrutura)
    fp = {k: v for k, v in (extra.get("fora_padrao_nome") or {}).items() if v}
    if fp:
        log(f"hierarquia: rotulos com nome fora do padrao 'NOME (codigo)', usados como vieram: {fp}", "ok")

    # D-83: bandeira do cadastro pela Estrutura de Clientes (ligacao por codigo do cliente)
    arq_c = arquivo_datado(_ECL, "estrutura_clientes") if _ECL else None
    if arq_c is None:
        msg = "Estrutura de Clientes ausente — COD_BANDEIRA/BANDEIRA_ESTRUTURA ficam <NA>"
        if _ECL.get("obrigatorio"):
            abortar(msg)
        log(msg, "aviso")
        avisos.append(msg)
    else:
        ecl = cache.ler(arq_c, _ler_estrutura_clientes)[0]
        antes = len(est)
        est = est.merge(ecl, on="COD_CLIENTE", how="left", validate="m:1")
        assert len(est) == antes, "o merge da Estrutura de Clientes multiplicou clientes"
        sem = int(est["COD_BANDEIRA"].isna().sum())
        log(f"Estrutura de Clientes: {arq_c.name} · {len(ecl):,} clientes · "
            f"{sem:,} cliente(s) da hierarquia sem linha (bandeira do cadastro <NA>)", "ok")

    # O COMPLEMENTO (D-34) foi aposentado na D-49 (02/09/2026): o arquivo saiu
    # de bases/ em definitivo e os clientes dele viraram as bases RTM-Transicao
    # e Hierarquia_Clientes_Faltando, tratadas na Fase 2 da reestruturacao.

    # ---- correcoes DECLARADAS -------------------------------------------
    for coluna, chave in (("HEAD", "correcoes_head"),
                          ("GERENTE", "correcoes_gerente"),
                          ("SUPERVISOR", "correcoes_supervisor"),
                          ("VENDEDOR", "correcoes_vendedor")):
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
    # niveis da estrutura. VENDEDOR entrou na D-50: medido em 02/09/2026,
    # 13 clientes com DOIS codigos N4 (mesmo representante, codigos de filial)
    # — vale a 1a linha com aviso; desempate declarado resolve caso a caso.
    for coluna in ("HEAD", "SUPERVISOR", "VENDEDOR", "COD_BANDEIRA"):
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


# ------------------------------------------------- RTM — TRANSICAO (D-50)
def _ler_rtm(arq: Path) -> tuple[pd.DataFrame, dict]:
    """De-para cliente RTM -> distribuidor que passou a atende-lo.

    Medido em 02/09/2026: 1.762 clientes, zero duplicado, zero cliente com
    dois distribuidores; 166 linhas SEM codigo de distribuidor (placeholders
    "NOVO ...") — essas ficam com COD_DISTRIBUIDOR <NA> e viram excecao no
    saneamento, nunca sao descartadas aqui."""
    df = _ler_aba(arq, _RTM["aba"], "rtm_transicao", dtype=str)
    _validar(df, _RTM["colunas_obrigatorias"], arq)

    out = pd.DataFrame(index=df.index)
    out["COD_CLIENTE"] = digitos(df["Cód. Cliente [Antigo]"])
    out["BANDEIRA_ANTIGA"] = texto(df["Bandeira cliente [Antigo]"])
    # "Dsitribuidor" e a grafia DA ORIGEM (nao corrigida — fonte unica).
    out["DISTRIBUIDOR"] = texto(df["Dsitribuidor Nome Reduzido"])
    out["COD_DISTRIBUIDOR"] = digitos(df["Cód. Cliente [Distribuidor]"])
    out = out.dropna(subset=["COD_CLIENTE"]).reset_index(drop=True)

    extra: dict = {}
    n_multi = int((out.groupby("COD_CLIENTE")["COD_DISTRIBUIDOR"]
                   .nunique(dropna=True) > 1).sum())
    if n_multi:
        extra["multi_distribuidor"] = n_multi
    return out.drop_duplicates("COD_CLIENTE", keep="first"), extra


def ler_rtm() -> tuple[pd.DataFrame, list[str]]:
    """Devolve (rtm, avisos). Ausência do arquivo NÃO derruba o pipeline —
    o painel roda sem a reatribuição, com o aviso registrado."""
    vazio = pd.DataFrame(columns=["COD_CLIENTE", "BANDEIRA_ANTIGA",
                                  "DISTRIBUIDOR", "COD_DISTRIBUIDOR"])
    avisos: list[str] = []
    if not _RTM:
        return vazio, avisos
    arq = caminho(_RTM["arquivo"])
    if not arq.exists():
        msg = (f"base RTM-Transicao ausente ({arq.name}) — nenhum cliente e "
               "reatribuido a distribuidor")
        log(msg, "aviso")
        return vazio, [msg]
    rtm, extra = cache.ler(arq, _ler_rtm)
    if extra.get("multi_distribuidor"):
        # 4.2 do prompt da reestruturacao: caso novo, NAO decidir sozinho.
        msg = (f"{extra['multi_distribuidor']} cliente(s) RTM com MAIS de um "
               "distribuidor no de-para — vale a 1a linha; caso novo, decidir "
               "com o Comercial")
        log(msg, "aviso")
        avisos.append(msg)
    sem = int(rtm["COD_DISTRIBUIDOR"].isna().sum())
    log(f"RTM-Transicao: {len(rtm):,} clientes · "
        f"{rtm['COD_DISTRIBUIDOR'].nunique():,} distribuidores · "
        f"{sem:,} sem codigo de distribuidor (excecao)", "ok")
    return rtm, avisos


# --------------------------------------- HIERARQUIA FALTANDO (D-50, Step 5)
def _ler_faltando(arq: Path) -> tuple[pd.DataFrame, dict]:
    df = _ler_aba(arq, _FALT["aba"], "hierarquia_faltando", dtype=str)
    _validar(df, _FALT["colunas_obrigatorias"], arq)
    out = pd.DataFrame(index=df.index)
    out["COD_CLIENTE"] = digitos(df["CÓDIGO CLIENTE"])
    out["NOME_FALTANDO"] = texto(df["CLIENTE"])
    out["HIERARQUIA"] = texto(df["Hierarquia"])
    out = out.dropna(subset=["COD_CLIENTE"]).reset_index(drop=True)
    extra: dict = {}
    fora = sorted(set(out["HIERARQUIA"].dropna()) - {"SIM", "NÃO", "NAO"})
    if fora:
        extra["valores_estranhos"] = fora
    return out.drop_duplicates("COD_CLIENTE", keep="first"), extra


def ler_faltando() -> tuple[pd.DataFrame, list[str]]:
    """Devolve (faltando, avisos). Ausência do arquivo NÃO derruba o pipeline."""
    vazio = pd.DataFrame(columns=["COD_CLIENTE", "NOME_FALTANDO", "HIERARQUIA"])
    avisos: list[str] = []
    if not _FALT:
        return vazio, avisos
    arq = caminho(_FALT["arquivo"])
    if not arq.exists():
        msg = (f"base Hierarquia_Clientes_Faltando ausente ({arq.name}) — "
               "saneamento da hierarquia NAO executado")
        log(msg, "aviso")
        return vazio, [msg]
    falt, extra = cache.ler(arq, _ler_faltando)
    if extra.get("valores_estranhos"):
        msg = (f"coluna Hierarquia com valor(es) fora de SIM/NAO: "
               f"{extra['valores_estranhos']} — tratados como NAO COBERTOS "
               "(nada e inativado por eles)")
        log(msg, "aviso")
        avisos.append(msg)
    h = falt["HIERARQUIA"].fillna("")
    log(f"Hierarquia_Clientes_Faltando: {len(falt):,} clientes · "
        f"SIM {int((h == 'SIM').sum()):,} · "
        f"NAO {int(h.isin(['NÃO', 'NAO']).sum()):,}", "ok")
    return falt, avisos
