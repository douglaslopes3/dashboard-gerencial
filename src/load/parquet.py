# -*- coding: utf-8 -*-
"""Gravação e leitura da camada curada."""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from ..utils.config import PASTA_CURATED
from ..utils.log import abortar, log


def salvar(df: pd.DataFrame, nome: str) -> Path:
    PASTA_CURATED.mkdir(parents=True, exist_ok=True)
    alvo = PASTA_CURATED / f"{nome}.parquet"
    # B7 (auditoria): zstd le igual e grava ~15% menor que snappy (medido);
    # row groups de 1 Mi evitam a fragmentacao de 110 grupos na fato.
    df.to_parquet(alvo, index=False, compression="zstd",
                  row_group_size=1_000_000)
    log(f"{nome:<22} {len(df):>10,} linhas x {len(df.columns):>2} col  ->  "
        f"{alvo.name} ({alvo.stat().st_size / 1024:,.0f} KB)", "ok")
    return alvo


def _limpar_parquets(pasta: Path) -> None:
    """Apaga os `.parquet` de uma pasta particionada, mantendo os diretórios.

    O projeto mora dentro do OneDrive, e o sincronizador segura o HANDLE DO
    DIRETÓRIO enquanto envia os arquivos — `shutil.rmtree` estoura
    `PermissionError: [WinError 5]` na hora de remover a pasta da partição, mesmo
    com os arquivos já apagados. Apagar só os arquivos resolve: o `partition_cols`
    do pyarrow reaproveita o diretório existente, e o reprocessamento continua
    completo (nenhum Parquet antigo sobrevive).
    """
    if not pasta.exists():
        return
    for arq in pasta.rglob("*.parquet"):
        for tentativa in range(4):
            try:
                arq.unlink()
                break
            except PermissionError:
                if tentativa == 3:
                    # A6: aqui a mensagem padrao ("nenhum Parquet foi
                    # atualizado") seria FALSA — a fato pode ter ficado pela
                    # metade e as dimensoes ja foram regravadas.
                    abortar(f"nao foi possivel apagar {arq}.\n"
                            "  O OneDrive costuma segurar o arquivo durante a "
                            "sincronizacao. Pause a sincronizacao e rode de novo.",
                            situacao="a FATO pode ter ficado PARCIALMENTE "
                            "apagada e as dimensoes ja foram regravadas. "
                            "Rode `python run_pipeline.py` de novo (pausando o "
                            "OneDrive) — o reprocessamento completo regrava tudo.")
                time.sleep(0.5)


def salvar_particionado(df: pd.DataFrame, nome: str, por: str) -> Path:
    """Fato particionada. Hoje são 2 partições (uma por ano); cresce 1 por ano.

    Particionar por ANO_MES daria 24 arquivos de ~130 mil linhas — mais arquivo e
    nenhum ganho medido. Ver `docs/09_ARQUITETURA_SOLUCAO.md §5`.
    """
    alvo = PASTA_CURATED / nome
    _limpar_parquets(alvo)
    d = df.copy()
    d[por] = d[por].astype("string")
    d.to_parquet(alvo, index=False, partition_cols=[por], compression="zstd",
                 row_group_size=1_000_000)
    tam = sum(p.stat().st_size for p in alvo.rglob("*.parquet")) / 1024
    n = len(list(alvo.rglob("*.parquet")))
    log(f"{nome:<22} {len(df):>10,} linhas em {n} particao(oes)  ->  "
        f"{nome}/ ({tam:,.0f} KB)", "ok")
    return alvo


def carregar(nome: str) -> pd.DataFrame:
    alvo = PASTA_CURATED / f"{nome}.parquet"
    if alvo.exists():
        return pd.read_parquet(alvo)
    pasta = PASTA_CURATED / nome
    if pasta.exists():
        return pd.read_parquet(pasta)
    abortar(f"{nome} nao existe em {PASTA_CURATED}. "
            "Rode `python run_pipeline.py` primeiro.")
