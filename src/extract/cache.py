# -*- coding: utf-8 -*-
"""Cache de leitura de Excel em Parquet.

Ler 95 MB de Excel custa minutos; ler o Parquet equivalente custa segundos. A
chave do cache é (nome, tamanho, data de modificação, VERSAO_CACHE).

------------------------------------------------------------------------------
VERSAO_CACHE — leia antes de mexer em qualquer leitor
------------------------------------------------------------------------------
SUBA a versão sempre que um leitor mudar de colunas ou passar a gravar algo novo
no `extra`.

Isto existe por um erro real, documentado no projeto anterior: uma checagem nova
passou a depender de um campo do `extra`, mas os arquivos já estavam em cache e
o `extra` antigo não tinha o campo. A checagem rodou de mão vazia e o dado errado
entrou no painel com todas as checagens verdes.

Checagem que não roda é pior do que checagem que não existe, porque dá a sensação
de proteção.

v1 (26/08/2026) — versão inicial deste projeto.
v8 (02/10/2026) — D-83: o leitor da estrutura passou a ler a Hierarquia_AAAAMMDD
   (rotulo "codigo - nome", sem PROJETO) e a bandeira do cadastro vem da Estrutura
   de Clientes. Um cache v7 entregaria os rotulos antigos.
v7 (02/09/2026) — D-50: o leitor da estrutura passou a montar o VENDEDOR (N4)
   como quarto nível concatenado. Um cache v6 entregaria a estrutura SEM a
   coluna — e o fillna mascararia todo mundo como NÃO ATRIBUÍDO (aconteceu na
   primeira execução da Fase 2: 1 vendedor distinto no painel inteiro, pego
   pela medição pós-execução).
v6 (01/09/2026) — D-42: o leitor da estrutura comercial passou a ler CÓDIGO
   BANDEIRA/BANDEIRA da Hierarquia_Consolidada (ponte por código com a base
   de metas). Um cache v5 entregaria a estrutura sem as colunas novas.
v5 (28/08/2026) — D-36: o leitor de sell-in passou a descartar (e contar no
   `extra["linhas_zeradas"]`) as linhas com as três métricas zeradas/nulas.
   Um cache v4 entregaria as linhas fantasma e o `extra` sem o campo.
v4 (28/08/2026) — troca da base de estrutura comercial (D-34): o leitor passou
   a montar HEAD/GERENTE/SUPERVISOR como rótulo concatenado da
   Hierarquia_Consolidada (código + papel + nome) e a coluna
   ATENDIMENTO_PONTA deixou de existir. Um cache v3 entregaria as colunas
   antigas.
v3 (27/08/2026) — leitores mudaram de novo: o texto do filtro do sell-in
   passa a ser capturado a partir da linha "Filtros aplicados" (C8) e o
   descarte de linha sem cliente/material passou a ser contado (C7). O `extra`
   de um cache v2 teria o filtro no formato antigo.
v2 (27/08/2026) — a chave passa a incluir o CAMINHO RELATIVO e um hash rápido
   do conteúdo (primeiros + últimos 64 KB). Motivo (auditoria, A11): um restore
   de versão pelo histórico do OneDrive — ou um `robocopy /COPY:DAT` — que
   preserve nome, tamanho e carimbo servia o Parquet ANTIGO como se fosse o
   dado novo, com o log dizendo "(cache)". A versão também sobe porque os
   leitores mudaram: `ano_mes()` ficou estrito (A9) e `numero()` decide o
   decimal pelo último separador (A10).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from ..utils.config import PASTA_STAGING, RAIZ
from ..utils.log import log

VERSAO_CACHE = 8

_KB64 = 65536


def _hash_rapido(arq: Path, tamanho: int) -> str:
    """Hash dos primeiros e últimos 64 KB — barato (2 leituras) e suficiente
    para pegar conteúdo trocado com tamanho+mtime preservados."""
    h = hashlib.md5()
    with open(arq, "rb") as f:
        h.update(f.read(_KB64))
        if tamanho > _KB64:
            f.seek(max(tamanho - _KB64, 0))
            h.update(f.read(_KB64))
    return h.hexdigest()[:8]


def _chave(arq: Path) -> str:
    st = arq.stat()
    try:
        rel = arq.resolve().relative_to(RAIZ)
    except ValueError:                       # fora da raiz do projeto
        rel = arq.resolve()
    crua = (f"v{VERSAO_CACHE}|{rel.as_posix()}|{st.st_size}|{int(st.st_mtime)}"
            f"|{_hash_rapido(arq, st.st_size)}")
    return hashlib.md5(crua.encode()).hexdigest()[:10]


def ler(arq: Path, leitor) -> tuple[pd.DataFrame, dict]:
    """`leitor(caminho) -> (df, extra)`. `extra` é um dict pequeno (gabaritos,
    texto de filtro) guardado num JSON ao lado do Parquet."""
    arq = Path(arq)
    PASTA_STAGING.mkdir(parents=True, exist_ok=True)
    ch = _chave(arq)
    alvo = PASTA_STAGING / f"{arq.stem}.{ch}.parquet"
    lado = PASTA_STAGING / f"{arq.stem}.{ch}.json"

    if alvo.exists() and lado.exists():
        df = pd.read_parquet(alvo)
        with open(lado, encoding="utf-8") as f:
            extra = json.load(f)
        log(f"{arq.name:<40} {len(df):>10,} linhas  (cache)")
        return df, extra

    df, extra = leitor(arq)
    df.to_parquet(alvo, index=False)
    with open(lado, "w", encoding="utf-8") as f:
        json.dump(extra, f, ensure_ascii=False)
    # Versões antigas do MESMO arquivo saem sozinhas.
    for velho in PASTA_STAGING.glob(f"{arq.stem}.*"):
        if velho not in (alvo, lado):
            try:
                velho.unlink()
            except OSError:
                pass
    log(f"{arq.name:<40} {len(df):>10,} linhas  (lido)")
    return df, extra
