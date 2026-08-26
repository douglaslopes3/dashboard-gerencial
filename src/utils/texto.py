# -*- coding: utf-8 -*-
"""Normalização de tipos vindos do Excel.

Adaptado de `etl/_comum.py` do projeto anterior (ver
`docs/03_MATRIZ_REAPROVEITAMENTO_ETL.md`, itens A1–A4 e A6).

O que estas funções fazem: tirar sujeira de FORMATO (espaço duplo, `.0` de float,
máscara de pontuação, célula vazia que vira a string "nan").

O que elas NÃO fazem: corrigir grafia, mapear valor ou decidir precedência. Isso
é decisão de negócio e vive no config.
"""
from __future__ import annotations

import re

import pandas as pd

_RE_ESPACO = re.compile(r"\s+")

_MESES_PT = {"JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
             "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12}


def texto(s: pd.Series, maiuscula: bool = True) -> pd.Series:
    """Trim + colapsa espaços + (opcional) MAIÚSCULA. Vazio vira <NA>."""
    out = (s.astype("string").str.strip()
            .str.replace(_RE_ESPACO, " ", regex=True))
    if maiuscula:
        out = out.str.upper()
    return out.replace({"": pd.NA, "NAN": pd.NA, "NONE": pd.NA,
                        "nan": pd.NA, "-": pd.NA})


def digitos(s: pd.Series) -> pd.Series:
    """Só os dígitos, sem zeros à esquerda.

    Tolera o que o Excel entrega: float (`1010846.0`), int, texto zero-preenchido
    (`0001010846`) e máscara (`01.978.813/0001-13`).

    O `lstrip("0")` NÃO é cosmético. O de-para de estrutura traz o código
    zero-preenchido e o sell-in traz o número puro; sem tirar os zeros o join
    casa com ZERO cliente — e casa em silêncio, com todo o resultado nulo.
    """
    out = (s.astype("string")
            .str.replace(r"\.0+$", "", regex=True)
            .str.replace(r"\D", "", regex=True)
            .str.lstrip("0"))
    return out.replace({"": pd.NA})


def numero(s: pd.Series) -> pd.Series:
    """Float tolerando o formato brasileiro (1.234,56)."""
    if pd.api.types.is_numeric_dtype(s):
        return pd.to_numeric(s, errors="coerce")
    txt = (s.astype("string").str.strip()
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False))
    return pd.to_numeric(txt, errors="coerce")


def ano_mes(s: pd.Series) -> pd.Series:
    """Normaliza para `AAAA-MM`. Aceita `2025/07`, `2025-07` e `2025/JUL`."""
    txt = s.astype("string").str.strip().str.upper()
    ano = txt.str.slice(0, 4)
    resto = txt.str.slice(5, 8).str.strip()
    mes = resto.map(_MESES_PT).fillna(
        pd.to_numeric(resto.str.slice(0, 2), errors="coerce"))
    ok = ano.str.fullmatch(r"\d{4}").fillna(False) & mes.notna()
    mes_txt = mes.astype("Float64").astype("Int64").astype("string").str.zfill(2)
    return (ano + "-" + mes_txt).where(ok)


def pct(atual, ly):
    """Variação percentual segura.

    Base zero ou nula devolve `None` — que a interface mostra como `n/d`, nunca
    como infinito. Base negativa usa o MÓDULO no denominador, para que uma
    devolução líquida no LY não inverta o sinal da variação.
    """
    try:
        a, b = float(atual), float(ly)
    except (TypeError, ValueError):
        return None
    if b == 0 or b != b:
        return None
    return (a - b) / abs(b)


def div(a, b):
    """Divisão segura: denominador zero devolve `None`, nunca infinito."""
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return None
    if b == 0 or b != b:
        return None
    return a / b
