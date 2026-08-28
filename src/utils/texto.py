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
    """Float tolerando o formato brasileiro (1.234,56) E o americano (1,234.56).

    O separador DECIMAL é o último que aparece (auditoria, A10): a versão
    anterior removia todo `.` antes de olhar a `,`, então `"1234.56"` virava
    123456.0 (100×) e `"1,234.56"` virava 1.23456 — latente enquanto a fonte
    entregar float64, fatal no dia em que a extração mudar de locale.
    Um único tipo de separador repetido (`1.234.567`) é milhar. O ambíguo de
    verdade (`1.234` sozinho) é lido como DECIMAL; se a fonte um dia entregar
    milhar pt-BR como texto, a reconciliação contra o gabarito acusa na hora.
    """
    if pd.api.types.is_numeric_dtype(s):
        return pd.to_numeric(s, errors="coerce")
    txt = s.astype("string").str.strip()
    pos_p = txt.str.rfind(".").fillna(-1)
    pos_v = txt.str.rfind(",").fillna(-1)
    n_p = txt.str.count(r"\.").fillna(0)
    n_v = txt.str.count(",").fillna(0)
    milhar_p = (pos_v < 0) & (n_p > 1)          # 1.234.567
    milhar_v = (pos_p < 0) & (n_v > 1)          # 1,234,567
    dec_v = (pos_v >= 0) & (pos_v > pos_p) & ~milhar_v   # virgula decimal
    dec_p = (pos_p >= 0) & (pos_p > pos_v) & ~milhar_p   # ponto decimal
    out = txt.copy()
    out = out.mask(dec_v, txt.str.replace(".", "", regex=False)
                             .str.replace(",", ".", regex=False))
    out = out.mask(dec_p, txt.str.replace(",", "", regex=False))
    out = out.mask(milhar_p, txt.str.replace(".", "", regex=False))
    out = out.mask(milhar_v, txt.str.replace(",", "", regex=False))
    return pd.to_numeric(out, errors="coerce")


_RE_ANO_MES = re.compile(r"^(\d{4})[/-](\d{1,2}|[A-Z]{3})$")


def ano_mes(s: pd.Series) -> pd.Series:
    """Normaliza para `AAAA-MM`. Aceita SOMENTE `AAAA/MM`, `AAAA-MM` e `AAAA/MMM`.

    Estrita de propósito (auditoria, A9): a versão anterior fatiava posições
    fixas, então `202512` virava `2025-02` (mês errado, em silêncio) e
    `2025/13` passava. Agora o padrão é full-match e o mês é validado em 1..12;
    o que não casar vira <NA> — e o leitor de sell-in ABORTA quando uma linha
    de dado traz `Ano mês` não reconhecido, em vez de descartá-la no dropna.
    """
    txt = s.astype("string").str.strip().str.upper()
    m = txt.str.extract(_RE_ANO_MES)
    ano, resto = m[0], m[1]
    mes = resto.map(_MESES_PT).fillna(pd.to_numeric(resto, errors="coerce"))
    ok = ano.notna() & mes.notna() & (mes >= 1) & (mes <= 12)
    mes_txt = mes.astype("Float64").astype("Int64").astype("string").str.zfill(2)
    return (ano + "-" + mes_txt).where(ok.fillna(False))


def pct(atual, ly):
    """Variação percentual segura — ESPELHO de `varPct()` do template.

    Base zero ou nula devolve `None` — que a interface mostra como `n/d`, nunca
    como infinito. Base negativa usa o MÓDULO no denominador, para que uma
    devolução líquida no LY não inverta o sinal da variação. `atual` nulo
    também devolve `None` (paridade com o A2 do template).

    C10 (auditoria): esta função e `div()` não são chamadas pelo pipeline —
    existem como referência das fórmulas do JS, e a paridade é garantida pela
    tabela de casos em `tests/test_regras.py::test_paridade_formulas_com_o_template`.
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
