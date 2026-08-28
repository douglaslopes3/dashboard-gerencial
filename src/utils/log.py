# -*- coding: utf-8 -*-
"""Log em console e em arquivo, com identificador de execução.

O `EXECUCAO_ID` carimba a fato, o relatório de qualidade e o nome do arquivo de
log — é ele que amarra "este número veio desta execução".

Dado sensível não vai para o log: nome de cliente e bandeira aparecem só em
contagem e em CSV de exceção dentro de `data/quality/`, nunca no console.
"""
from __future__ import annotations

import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

from .config import CFG, PASTA_LOGS

EXECUCAO_ID = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
INICIO = datetime.now()

_T0 = time.time()
_ARQ = None
_AVISOS: list[str] = []
_ERROS: list[str] = []

_MARCA = {"ok": "  ok  ", "aviso": " aviso", "erro": " ERRO ", "": "      "}


def abrir() -> Path:
    """Abre o arquivo de log da execução e limpa os antigos."""
    global _ARQ
    PASTA_LOGS.mkdir(parents=True, exist_ok=True)
    alvo = PASTA_LOGS / f"pipeline_{EXECUCAO_ID}.log"
    _ARQ = open(alvo, "w", encoding="utf-8")
    _limpar_antigos()
    return alvo


def _limpar_antigos() -> None:
    manter = int(CFG.get("logs", {}).get("manter_ultimos", 30))
    velhos = sorted(PASTA_LOGS.glob("pipeline_*.log"))
    for v in velhos[:-manter] if len(velhos) > manter else []:
        try:
            v.unlink()
        except OSError:
            pass


def log(msg: str = "", nivel: str = "") -> None:
    linha = f"[{time.time() - _T0:6.1f}s]{_MARCA.get(nivel, _MARCA[''])} {msg}"
    print(linha, flush=True)
    if _ARQ:
        _ARQ.write(linha + "\n")
        _ARQ.flush()
    if nivel == "aviso":
        _AVISOS.append(msg)
    elif nivel == "erro":
        _ERROS.append(msg)


def titulo(msg: str) -> None:
    barra = "=" * 78
    for l in (barra, msg, barra):
        log(l)


def abortar(msg: str, situacao: str | None = None) -> None:
    """Erro fatal: registra, fecha o log e sai com exit code 1.

    `situacao` substitui a frase final quando o padrão ("nenhum Parquet foi
    atualizado") não for verdade — auditoria, A6/C16: a mensagem fixa mentia
    quando o aborto acontecia no MEIO da gravação."""
    log(msg, "erro")
    log("")
    log("PIPELINE ABORTADO — "
        + (situacao or "nenhum Parquet foi atualizado nesta execucao."), "erro")
    fechar()
    sys.exit(1)


def avisos() -> list[str]:
    return list(_AVISOS)


def erros() -> list[str]:
    return list(_ERROS)


def fechar() -> None:
    global _ARQ
    if _ARQ:
        _ARQ.close()
        _ARQ = None
