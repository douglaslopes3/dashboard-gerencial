# -*- coding: utf-8 -*-
"""Testes das regras críticas.

    python -m pytest tests/ -v          (se pytest estiver instalado)
    python tests/test_regras.py         (sem pytest, roda direto)

O foco é o que quebra em silêncio: normalização de chave, ano fiscal, pareamento
LY, divisão por zero e o grão da fato. Não testa o pandas.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.transform import calendario, dimensoes, fato as fato_mod   # noqa: E402
from src.utils.texto import (ano_mes, digitos, div, numero, pct,     # noqa: E402
                             texto)


# ============================================================ normalizacao
def test_digitos_tira_zeros_a_esquerda():
    """A armadilha que faz o join casar com ZERO cliente, em silêncio."""
    s = pd.Series(["0001010846", "1010846", "1010846.0", 1010846])
    assert list(digitos(s)) == ["1010846"] * 4


def test_digitos_vazio_vira_nulo():
    assert digitos(pd.Series(["", "abc", "0000", None])).isna().all()


def test_texto_normaliza_formato_mas_nao_corrige_grafia():
    s = pd.Series(["  atacadao  ", "MART   MINAS", "", "nan"])
    r = texto(s)
    assert r[0] == "ATACADAO"
    assert r[1] == "MART MINAS"          # espaco duplo colapsado
    assert pd.isna(r[2]) and pd.isna(r[3])
    # E o principal: erro de grafia NAO e corrigido.
    assert texto(pd.Series(["CHOLOCATE"]))[0] == "CHOLOCATE"


def test_numero_aceita_formato_br_e_ja_numerico():
    assert numero(pd.Series(["1.234,56"]))[0] == 1234.56
    assert numero(pd.Series([1234.56]))[0] == 1234.56


def test_ano_mes_normaliza_os_tres_formatos():
    r = ano_mes(pd.Series(["2026/08", "2026-08", "2026/AGO", "lixo"]))
    assert list(r[:3]) == ["2026-08"] * 3
    assert pd.isna(r[3])


def test_ano_mes_estrito_rejeita_mes_invalido_e_formato_colado():
    """A9: `202512` fatiado virava `2025-02` (mes errado, em silencio) e
    `2025/13` passava. Formato nao reconhecido tem de virar NA — e o leitor
    de sell-in aborta quando isso acontece numa linha de dado."""
    r = ano_mes(pd.Series(["202512", "2025/13", "2025/00", "07/2025",
                           "2025/XYZ", "2025-1"]))
    assert r.isna()[:5].all()
    assert r[5] == "2025-01"          # mes sem zero a esquerda continua valendo


def test_numero_decide_o_decimal_pelo_ultimo_separador():
    """A10: o `.replace(".", "")` rodava antes de olhar a virgula — `"1234.56"`
    virava 123456.0 (100x) e `"1,234.56"` virava 1.23456."""
    s = pd.Series(["1234.56", "1,234.56", "1.234,56",
                   "1.234.567", "1,234,567", "1,23", "-1.234,5"])
    assert list(numero(s)) == [1234.56, 1234.56, 1234.56,
                               1234567.0, 1234567.0, 1.23, -1234.5]


# ================================================== divisao por zero / LY
def test_pct_base_zero_ou_nula_devolve_none():
    assert pct(100, 0) is None
    assert pct(100, None) is None
    assert pct(100, float("nan")) is None


def test_pct_base_negativa_usa_modulo_e_nao_inverte_o_sinal():
    """LY negativo (devolução líquida) não pode virar queda quando houve alta."""
    assert pct(100, -50) == 3.0          # subiu: positivo
    assert pct(-100, -50) == -1.0        # piorou: negativo


def test_pct_normal():
    assert round(pct(110, 100), 4) == 0.1
    assert pct(0, 100) == -1.0           # -100%


def test_div_denominador_zero_devolve_none():
    assert div(10, 0) is None
    assert div(10, 2) == 5.0


def test_paridade_formulas_com_o_template():
    """C10: pct/div sao o espelho de varPct/razao do dashboard/template.html.
    Esta tabela reproduz os casos-limite do JS; se um lado mudar sem o outro,
    este teste e o alarme."""
    casos_pct = [((110, 100), 0.1),     # normal
                 ((100, 0), None),      # base zero -> n/d, nunca infinito
                 ((100, None), None),   # base nula
                 ((None, 100), None),   # atual nulo (A2) — era o furo do JS
                 ((100, -50), 3.0),     # base negativa: modulo no denominador
                 ((0, 100), -1.0)]      # -100%
    for (a, b), esperado in casos_pct:
        r = pct(a, b)
        assert (r is None and esperado is None) or round(r, 10) == esperado, \
            f"pct{(a, b)} = {r}, esperado {esperado}"
    casos_div = [((9, 3), 3.0), ((10, 0), None), ((10, None), None)]
    for (a, b), esperado in casos_div:
        r = div(a, b)
        assert (r is None and esperado is None) or r == esperado, \
            f"div{(a, b)} = {r}, esperado {esperado}"


# ============================================================== calendario
def _cal(meses):
    return calendario.construir(meses)


def test_ano_fiscal_setembro_a_agosto():
    d = _cal(["2024-09", "2026-08"]).set_index("ANO_MES")
    assert d.at["2025-08", "ANO_FISCAL"] == 2025      # ago/25 fecha o FY2025
    assert d.at["2025-09", "ANO_FISCAL"] == 2026      # set/25 abre o FY2026
    assert d.at["2026-08", "ANO_FISCAL"] == 2026      # ago/26 fecha o FY2026
    assert d.at["2025-09", "ANO_FISCAL_ROTULO"] == "FY2026"


def test_mes_fiscal_setembro_e_um():
    d = _cal(["2024-09", "2026-08"]).set_index("ANO_MES")
    assert d.at["2025-09", "MES_FISCAL"] == 1
    assert d.at["2026-08", "MES_FISCAL"] == 12
    assert d.at["2026-01", "MES_FISCAL"] == 5


def test_ly_e_pareamento_explicito_e_some_quando_nao_existe():
    d = _cal(["2024-09", "2026-08"]).set_index("ANO_MES")
    assert d.at["2025-09", "ANO_MES_LY"] == "2024-09"
    # O primeiro mes da serie nao tem ano anterior: fica NULO, nao aponta para
    # o mes errado por deslocamento posicional.
    assert pd.isna(d.at["2024-09", "ANO_MES_LY"])


def test_calendario_nao_grava_flag_de_ytd():
    """YTD depende do periodo escolhido na tela. Gravado, seria falso amanha."""
    cols = set(_cal(["2024-09", "2026-08"]).columns)
    assert not any("YTD" in c.upper() for c in cols)


def test_calendario_cobre_o_intervalo_sem_buraco():
    d = _cal(["2024-09", "2026-08"])
    assert len(d) == 24
    assert d["ANO_MES"].is_monotonic_increasing


# ============================================================== dimensoes
def _sellin(linhas):
    return pd.DataFrame(linhas, columns=[
        "ANO_MES", "COD_CLIENTE", "NOME_CLIENTE", "BANDEIRA", "UF",
        "COD_PRODUTO", "CATEGORIA_SELLIN", "DESCRICAO_SELLIN",
        "RECEITA", "PESO_KG", "CAIXAS", "ARQUIVO_ORIGEM"])


BASE = [
    ["2025-01", "1001", "CLIENTE A", "REDE X", "SP", "9001", "BALA", "BALA 1", 100.0, 10.0, 2.0, "a.xlsx"],
    ["2025-02", "1001", "CLIENTE A NOVO NOME", "REDE X", "SP", "9001", "BALA", "BALA 1", 50.0, 5.0, 1.0, "a.xlsx"],
    ["2025-01", "1002", "CLIENTE B", "REDE Y", "MG", "9002", "GOMAS", "GOMA 1", 200.0, 20.0, 4.0, "a.xlsx"],
]


def test_cliente_sem_estrutura_entra_e_nao_e_descartado():
    est = pd.DataFrame([["1001", "Ademir", "Gerente SP", "Sup 1"]],
                       columns=["COD_CLIENTE", "HEAD", "GERENTE", "SUPERVISOR"])
    d = dimensoes.dim_cliente(_sellin(BASE), est)
    assert len(d) == 2                            # os DOIS clientes existem
    b = d.set_index("COD_CLIENTE").loc["1002"]
    assert b["NA_ESTRUTURA"] is False or b["NA_ESTRUTURA"] == False   # noqa: E712
    assert b["HEAD"] == "NÃO ATRIBUÍDO"


def test_nome_do_cliente_mais_recente_vence():
    """Cliente renomeado no meio da série apareceria duas vezes no ranking."""
    d = dimensoes.dim_cliente(_sellin(BASE), pd.DataFrame(
        columns=["COD_CLIENTE", "HEAD", "GERENTE", "SUPERVISOR"]))
    assert d.set_index("COD_CLIENTE").at["1001", "NOME_CLIENTE"] == "CLIENTE A NOVO NOME"


def test_sku_fora_do_cadastro_entra_marcado_e_sem_marca():
    prod = pd.DataFrame([["9001", "BALA OFICIAL", "BALA", "DORI"]],
                        columns=["COD_PRODUTO", "DESCRICAO_PRODUTO", "CATEGORIA", "MARCA"])
    d = dimensoes.dim_produto(_sellin(BASE), prod).set_index("COD_PRODUTO")
    assert len(d) == 2
    assert d.at["9001", "FORA_DO_CADASTRO"] == False        # noqa: E712
    assert d.at["9002", "FORA_DO_CADASTRO"] == True         # noqa: E712
    assert d.at["9002", "CATEGORIA"] == "GOMAS"             # veio do sell-in
    assert pd.isna(d.at["9002", "MARCA"])                   # marca NAO e inferida


def test_cliente_ganha_canal_e_o_sem_canal_vira_excecao():
    """O aceite da devolutiva de 26/08: 100% classificado, e quem sobrar vai
    para a lista de exceções — nunca escondido num 'Outros'."""
    canais = pd.DataFrame([["1001", "CASH & CARRY", "Atacarejo"]],
                          columns=["COD_CLIENTE", "CANAL", "SUBCANAL"])
    d = dimensoes.dim_cliente(_sellin(BASE), pd.DataFrame(
        columns=["COD_CLIENTE", "HEAD", "GERENTE", "SUPERVISOR"]), canais)
    d = d.set_index("COD_CLIENTE")
    assert d.at["1001", "CANAL"] == "CASH & CARRY"
    assert bool(d.at["1001", "TEM_CANAL"]) is True
    # O 1002 nao esta no de-para: entra marcado, nao descartado.
    assert d.at["1002", "CANAL"] == "SEM CANAL"
    assert bool(d.at["1002", "TEM_CANAL"]) is False


def test_sem_base_de_canais_o_pipeline_segue():
    d = dimensoes.dim_cliente(_sellin(BASE), pd.DataFrame(
        columns=["COD_CLIENTE", "HEAD", "GERENTE", "SUPERVISOR"]), None)
    assert (d["CANAL"] == "SEM CANAL").all()
    assert not d["TEM_CANAL"].any()


# =================================================================== fato
def test_caixas_preserva_nulo_e_receita_preserva_sinal():
    linhas = list(BASE)
    linhas.append(["2025-03", "1001", "CLIENTE A", "REDE X", "SP", "9001",
                   "BALA", "BALA 1", -30.0, -3.0, None, "a.xlsx"])
    f = fato_mod.construir(_sellin(linhas))
    assert f["CAIXAS"].isna().sum() == 1        # nulo NAO virou zero
    assert (f["RECEITA"] < 0).sum() == 1        # devolucao NAO foi filtrada
    assert f["RECEITA"].sum() == 320.0


def test_fato_carrega_linhagem():
    f = fato_mod.construir(_sellin(BASE))
    for c in ("ARQUIVO_ORIGEM", "EXECUCAO_ID", "PROCESSADO_EM"):
        assert c in f.columns and f[c].notna().all()


def test_grao_sem_duplicidade_passa():
    f = fato_mod.construir(_sellin(BASE))
    assert fato_mod.conferir_grao(f) == []


def test_grao_com_duplicidade_aborta():
    """Duplicidade no grão tem de DERRUBAR o pipeline, não somar em silêncio."""
    linhas = list(BASE) + [BASE[0]]
    f = fato_mod.construir(_sellin(linhas))
    try:
        fato_mod.conferir_grao(f)
    except SystemExit as e:
        assert e.code == 1
        return
    raise AssertionError("duplicidade no grao NAO abortou o pipeline")


def test_integridade_referencial_aborta_com_orfao():
    f = fato_mod.construir(_sellin(BASE))
    cal = _cal(["2025-01", "2025-02"])
    cli = pd.DataFrame({"COD_CLIENTE": ["1001", "1002"]})
    prod = pd.DataFrame({"COD_PRODUTO": ["9001"]})       # falta o 9002
    try:
        fato_mod.conferir_integridade(f, cli, prod, cal)
    except SystemExit as e:
        assert e.code == 1
        return
    raise AssertionError("FK orfa NAO abortou o pipeline")


def test_reconciliacao_pega_divergencia_com_a_origem():
    f = fato_mod.construir(_sellin(BASE))
    meta = {"gabaritos": {"a.xlsx": {"receita": 999.0, "peso_kg": 35.0,
                                     "caixas": 7.0}}}
    try:
        fato_mod.reconciliar_origem(f, meta)
    except SystemExit as e:
        assert e.code == 1
        return
    raise AssertionError("divergencia com o gabarito NAO abortou o pipeline")


def test_reconciliacao_passa_quando_bate():
    f = fato_mod.construir(_sellin(BASE))
    meta = {"gabaritos": {"a.xlsx": {"receita": 350.0, "peso_kg": 35.0,
                                     "caixas": 7.0}}}
    assert fato_mod.reconciliar_origem(f, meta) == []


# ================================================================== runner
def _rodar_sem_pytest() -> int:
    testes = [(n, o) for n, o in sorted(globals().items())
              if n.startswith("test_") and callable(o)]
    falhas = 0
    for nome, fn in testes:
        try:
            fn()
            print(f"  ok   {nome}")
        except Exception as e:                            # noqa: BLE001
            falhas += 1
            print(f" FALHA {nome}: {type(e).__name__}: {e}")
    print(f"\n{len(testes) - falhas} de {len(testes)} passaram.")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(_rodar_sem_pytest())
