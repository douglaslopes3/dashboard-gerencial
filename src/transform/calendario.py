# -*- coding: utf-8 -*-
"""DIM_CALENDARIO — um mês por linha, os DOIS calendários na mesma tabela.

Adaptado de `etl/04_dim_data.py` do projeto anterior (item A13 da matriz de
reaproveitamento), simplificado: saíram dias úteis, feriados e o pareamento
mês-a-mês, que não têm uso neste MVP.

DUAS DECISÕES QUE VALEM O COMENTÁRIO
------------------------------------
1. **O ano fiscal é COLUNA, não tabela paralela.** Duas tabelas de data obrigam
   a uma junção dupla, e é assim que o total fiscal deixa de bater com o do
   calendário.

2. **`ANO_MES_LY` é junção, não deslocamento.** Deslocar por posição erra sempre
   que falta um mês na série. Como coluna, o LY que não existe simplesmente
   fica nulo — a comparação some, em vez de mentir.

NENHUMA flag de YTD é gravada. YTD depende do período que o usuário escolhe na
tela; gravado, seria falso amanhã.
"""
from __future__ import annotations

import pandas as pd

from ..utils.config import CFG

MES_NOME = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
            "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MES_ABREV = ["jan", "fev", "mar", "abr", "mai", "jun",
             "jul", "ago", "set", "out", "nov", "dez"]

_CAL = CFG["calendario"]


def _mes_inicio() -> int:
    return int(_CAL["fiscal_mes_inicio"])


def ano_fiscal(data: pd.Series) -> pd.Series:
    """Ano de FECHAMENTO. Com início em setembro: set/25..ago/26 = 2026."""
    ini = _mes_inicio()
    return (data.dt.year + (data.dt.month >= ini).astype(int)).astype("int64")


def mes_fiscal(data: pd.Series) -> pd.Series:
    """Posição do mês dentro do ano fiscal: setembro = 1 ... agosto = 12."""
    return ((data.dt.month - _mes_inicio()) % 12 + 1).astype("int64")


def construir(meses: list[str]) -> pd.DataFrame:
    """`meses` = todos os `ANO_MES` presentes na fato. A dimensão cobre do menor
    ao maior, sem buraco, mesmo que a fato tenha."""
    ini, fim = min(meses), max(meses)
    datas = pd.date_range(f"{ini}-01", f"{fim}-01", freq="MS")

    d = pd.DataFrame({"DATA_INICIO": datas})
    d["ANO_MES"] = d["DATA_INICIO"].dt.strftime("%Y-%m")
    d["DATA_FIM"] = d["DATA_INICIO"] + pd.offsets.MonthEnd(0)
    d["ANO"] = d["DATA_INICIO"].dt.year.astype("int64")
    d["MES"] = d["DATA_INICIO"].dt.month.astype("int64")
    d["MES_NOME"] = d["MES"].map(lambda m: MES_NOME[m - 1]).astype("string")
    d["MES_ABREV"] = d["MES"].map(lambda m: MES_ABREV[m - 1]).astype("string")
    d["ROTULO"] = d["MES_ABREV"] + "/" + d["ANO"].astype("string").str.slice(2)

    d["TRIMESTRE"] = d["DATA_INICIO"].dt.quarter.astype("int64")
    d["SEMESTRE"] = ((d["MES"] - 1) // 6 + 1).astype("int64")
    d["TRIMESTRE_ROTULO"] = d["ANO"].astype("string") + "-T" + d["TRIMESTRE"].astype("string")
    d["SEMESTRE_ROTULO"] = d["ANO"].astype("string") + "-S" + d["SEMESTRE"].astype("string")

    d["ANO_FISCAL"] = ano_fiscal(d["DATA_INICIO"])
    d["ANO_FISCAL_ROTULO"] = (_CAL["fiscal_prefixo"] + d["ANO_FISCAL"].astype("string"))
    d["MES_FISCAL"] = mes_fiscal(d["DATA_INICIO"])
    d["TRIMESTRE_FISCAL"] = ((d["MES_FISCAL"] - 1) // 3 + 1).astype("int64")
    d["SEMESTRE_FISCAL"] = ((d["MES_FISCAL"] - 1) // 6 + 1).astype("int64")
    d["TRIMESTRE_FISCAL_ROTULO"] = (d["ANO_FISCAL_ROTULO"] + "-T"
                                    + d["TRIMESTRE_FISCAL"].astype("string"))
    d["SEMESTRE_FISCAL_ROTULO"] = (d["ANO_FISCAL_ROTULO"] + "-S"
                                   + d["SEMESTRE_FISCAL"].astype("string"))

    validos = set(d["ANO_MES"])
    ly = (d["DATA_INICIO"] - pd.DateOffset(years=1)).dt.strftime("%Y-%m")
    d["ANO_MES_LY"] = ly.where(ly.isin(validos)).astype("string")

    d["ORDEM"] = range(len(d))
    return d
