# -*- coding: utf-8 -*-
"""Configuração e caminhos do projeto.

Uma única fonte para "onde fica a raiz" e "o que diz o config". Todo caminho é
resolvido a partir da raiz do projeto, nunca de `os.getcwd()` — rodar o pipeline
de dentro de `src/` tem de dar o mesmo resultado que rodar da raiz.
"""
from __future__ import annotations

from pathlib import Path

import yaml

# src/utils/config.py -> src/utils -> src -> raiz
RAIZ = Path(__file__).resolve().parents[2]

PASTA_CONFIG = RAIZ / "config"


def _ler_yaml(nome: str) -> dict:
    alvo = PASTA_CONFIG / nome
    if not alvo.exists():
        raise SystemExit(
            f"config nao encontrado: {alvo}\n"
            f"  raiz do projeto : {RAIZ}\n"
            f"  a pasta existe? : {'sim' if PASTA_CONFIG.exists() else 'NAO'}"
        )
    with open(alvo, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


CFG = _ler_yaml("config.yaml")
GEO = _ler_yaml("geografia.yaml")


def caminho(relativo: str | Path) -> Path:
    """Resolve um caminho relativo ao projeto. Absoluto passa direto."""
    p = Path(str(relativo))
    return p if p.is_absolute() else RAIZ / p


PASTA_DADOS = caminho(CFG["projeto"]["pasta_dados"])
PASTA_RAW = PASTA_DADOS / "raw"
PASTA_STAGING = PASTA_DADOS / "staging"
PASTA_CURATED = PASTA_DADOS / "curated"
PASTA_QUALITY = PASTA_DADOS / "quality"
PASTA_LOGS = caminho(CFG["projeto"]["pasta_logs"])


def preparar_pastas() -> None:
    for p in (PASTA_RAW / "sell_in", PASTA_STAGING, PASTA_CURATED,
              PASTA_QUALITY, PASTA_LOGS):
        p.mkdir(parents=True, exist_ok=True)


def mapa_regiao() -> dict[str, str]:
    return {uf: reg for reg, ufs in (GEO.get("regiao") or {}).items() for uf in ufs}


def nome_uf() -> dict[str, str]:
    return dict(GEO.get("nome_uf") or {})
