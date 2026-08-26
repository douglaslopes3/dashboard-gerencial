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
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from ..utils.config import PASTA_STAGING
from ..utils.log import log

VERSAO_CACHE = 1


def _chave(arq: Path) -> str:
    st = arq.stat()
    crua = f"v{VERSAO_CACHE}|{arq.name}|{st.st_size}|{int(st.st_mtime)}"
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
