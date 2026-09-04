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

from src.extract import sellin                                       # noqa: E402
from src.transform import calendario, dimensoes, fato as fato_mod   # noqa: E402
from src.utils.texto import (ano_mes, digitos, div, numero, pct,     # noqa: E402
                             texto)


# ======================================================== descarte D-36
def test_linha_100_zerada_e_descartada_e_contada():
    """D-36: linha com receita, peso E caixas zerados/nulos sai (e e contada);
    QUALQUER metrica diferente de zero segura a linha — inclusive negativa,
    que e devolucao, nunca ruido."""
    df = pd.DataFrame({
        "RECEITA": [0.0, None, 0.0, 10.0, -5.0],
        "PESO_KG": [0.0, 0.0, None, 0.0, 0.0],
        "CAIXAS":  [None, 0.0, None, None, 0.0],
    })
    out, n = sellin._descartar_zeradas(df)
    assert n == 3
    assert list(out["RECEITA"]) == [10.0, -5.0]


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


def test_codigo_de_bandeira_entra_e_ausencia_fica_nula():
    """D-42: COD_BANDEIRA vem da hierarquia (ponte por codigo com a meta).
    Cliente do complemento (sem as colunas) fica <NA> — nunca inventado — e o
    esquema da DIM e estavel mesmo quando a estrutura inteira nao as traz."""
    est = pd.DataFrame(
        [["1001", "Ademir", "Gerente SP", "Sup 1", "8200475", "MART MINAS"]],
        columns=["COD_CLIENTE", "HEAD", "GERENTE", "SUPERVISOR",
                 "COD_BANDEIRA", "BANDEIRA_ESTRUTURA"])
    d = dimensoes.dim_cliente(_sellin(BASE), est).set_index("COD_CLIENTE")
    assert d.at["1001", "COD_BANDEIRA"] == "8200475"
    assert d.at["1001", "BANDEIRA_ESTRUTURA"] == "MART MINAS"
    assert pd.isna(d.at["1002", "COD_BANDEIRA"])        # fora da estrutura
    # Estrutura SEM as colunas (ex.: so o complemento): colunas existem, nulas.
    d2 = dimensoes.dim_cliente(_sellin(BASE), pd.DataFrame(
        columns=["COD_CLIENTE", "HEAD", "GERENTE", "SUPERVISOR"]))
    assert d2["COD_BANDEIRA"].isna().all()
    assert d2["BANDEIRA_ESTRUTURA"].isna().all()


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


# D-49 (02/09/2026): os testes do leitor de metas (D-43) e do CUBO_META
# (D-44) sairam com a remocao do tema Metas — modulos apagados do build.


# ================================================ D-48 · hierarquia N3 (02/09)
def _mini_modelo():
    """Modelo minimo com 2 heads, 2 gerentes e 3 sup./exec. no mesmo gerente.

    Serve para provar o que a D-48 mudou: o Sup./Exec. entrou no eixo dos DOIS
    cubos e o cubo de SKU passou a carregar tambem a bandeira.
    """
    fato = pd.DataFrame({
        "ANO_MES": ["2026-01"] * 6,
        "COD_CLIENTE": ["1", "2", "3", "4", "5", "6"],
        "COD_PRODUTO": ["10", "10", "20", "20", "30", "30"],
        "RECEITA": [100.0, 200.0, 300.0, 400.0, 500.0, 600.0],
        "PESO_KG": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
        "CAIXAS": [1.0, 2.0, 3.0, 4.0, 5.0, None],
    })
    dim_cli = pd.DataFrame({
        "COD_CLIENTE": ["1", "2", "3", "4", "5", "6"],
        "BANDEIRA": ["REDE A", "REDE B", "REDE A", "REDE B", "REDE A", "REDE B"],
        "UF": ["SP", "SP", "MG", "MG", "SP", "MG"],
        "HEAD": ["10 - H1"] * 4 + ["20 - H2"] * 2,
        "GERENTE": ["1000 - G1"] * 4 + ["2000 - G2"] * 2,
        "SUPERVISOR": ["1100 - S1", "1100 - S1", "1200 - S2", "1200 - S2",
                       "2100 - S3", "2100 - S3"],
        # D-50: o N4 entrou no perfil (posicao 5, sem mexer nas posicoes 0-4).
        "VENDEDOR": ["111 - V1", "111 - V1", "112 - V2", "112 - V2",
                     "221 - V3", "221 - V3"],
        "CANAL": ["VAREJO"] * 6,
        "PROJETO": ["P1"] * 6,
    })
    dim_prod = pd.DataFrame({
        "COD_PRODUTO": ["10", "20", "30"],
        "DESCRICAO_PRODUTO": ["SKU 10", "SKU 20", "SKU 30"],
        "CATEGORIA": ["BALA", "GOMAS", "BALA"],
    })
    dim_cal = calendario.construir(["2026-01"])
    return fato, dim_cli, dim_prod, dim_cal


def test_d48_perfil_tem_os_niveis_na_ordem_declarada():
    """D-48 fixou as posicoes 0-4; a D-50 acrescentou o VENDEDOR na 5 — as
    posicoes que o template le NAO podem mudar."""
    from src.load import cubos
    pac = cubos.construir(*_mini_modelo())
    assert cubos.COLS_PERFIL == ["HEAD", "GERENTE", "SUPERVISOR",
                                 "CANAL", "PROJETO", "VENDEDOR"]
    for p in pac["dims"]["perfil"]:
        assert len(p) == 6, "o perfil tem de carregar os seis componentes"
    sups = {p[2] for p in pac["dims"]["perfil"]}
    assert sups == {"1100 - S1", "1200 - S2", "2100 - S3"}
    vends = {p[5] for p in pac["dims"]["perfil"]}
    assert vends == {"111 - V1", "112 - V2", "221 - V3"}


def test_d48_cubo_de_sku_usa_o_mesmo_perfil_e_o_par_hc_nao_existe_mais():
    from src.load import cubos
    pac = cubos.construir(*_mini_modelo())
    # o par head x canal saiu: era ele que fazia a aba de SKU ignorar filtros
    assert "hc" not in pac["dims"]
    # D-51: sem o eixo UF; D-64: sem a bandeira — [mes, sku, perfil] + [R, P, C]
    assert all(len(l) == 6 for l in pac["cubo_sku"])
    assert all(l[2] < len(pac["dims"]["perfil"]) for l in pac["cubo_sku"])


def test_d48_receita_por_sup_exec_bate_entre_os_dois_cubos():
    """A conferencia que sustenta a fase: o mesmo recorte tem de dar o mesmo
    numero na Visao Geral (cubo principal) e na aba de SKU."""
    from src.load import cubos
    pac = cubos.construir(*_mini_modelo())
    perfil = pac["dims"]["perfil"]
    por_sup_principal, por_sup_sku = {}, {}
    for l in pac["cubo"]:
        k = perfil[l[3]][2]
        por_sup_principal[k] = por_sup_principal.get(k, 0) + l[4]
    for l in pac["cubo_sku"]:
        k = perfil[l[2]][2]
        por_sup_sku[k] = por_sup_sku.get(k, 0) + l[3]      # D-64: receita em 3
    assert set(por_sup_principal) == set(por_sup_sku)
    for k in por_sup_principal:
        # centavos: a diferenca aceita e a do arredondamento por grupo
        assert abs(por_sup_principal[k] - por_sup_sku[k]) <= 2, k
    assert sum(por_sup_principal.values()) == 210000     # R$ 2.100,00 em centavos


def test_d48_recorte_por_head_corta_os_dois_cubos_pelo_perfil():
    # D-52: filtrar_por_head virou filtrar_por_nivel(pacote, 0, head).
    from src.load import cubos
    from run_dashboard import filtrar_por_nivel
    pac = cubos.construir(*_mini_modelo())
    rec = filtrar_por_nivel(pac, 0, "10 - H1")
    perfil = rec["dims"]["perfil"]
    assert rec["dims"]["head"] == ["10 - H1"]
    assert all(perfil[l[3]][0] == "10 - H1" for l in rec["cubo"])
    # o cubo de SKU e cortado pelo MESMO indice de perfil (posicao 2)
    assert all(perfil[l[2]][0] == "10 - H1" for l in rec["cubo_sku"])
    assert sum(l[4] for l in rec["cubo"]) == 100000      # R$ 1.000,00
    assert sum(l[3] for l in rec["cubo_sku"]) == 100000


def test_d52_recorte_por_n3_e_particionamento_do_nivel():
    """Fase 4: o mesmo recorte fisico vale para qualquer nivel do perfil, e
    cada nivel PARTICIONA a base — a soma dos recortes fecha com o total."""
    from src.load import cubos
    from run_dashboard import filtrar_por_nivel
    pac = cubos.construir(*_mini_modelo())
    # N3 (posicao 2): sup "1200 - S2" atende os clientes 3 e 4 (300+400)
    rec = filtrar_por_nivel(pac, 2, "1200 - S2")
    perfil = rec["dims"]["perfil"]
    assert all(perfil[l[3]][2] == "1200 - S2" for l in rec["cubo"])
    assert all(perfil[l[2]][2] == "1200 - S2" for l in rec["cubo_sku"])
    assert sum(l[4] for l in rec["cubo"]) == 70000       # R$ 700,00
    # a lista de heads do arquivo encolhe junto (chips coerentes)
    assert rec["dims"]["head"] == ["10 - H1"]
    # particionamento do nivel N3: soma dos 3 sups = total
    sups = {p[2] for p in pac["dims"]["perfil"]}
    soma = sum(sum(l[4] for l in filtrar_por_nivel(pac, 2, s)["cubo"])
               for s in sups)
    assert soma == sum(l[4] for l in pac["cubo"]) == 210000


def test_d52_pasta_usuario_sanitiza_caracteres_invalidos():
    from run_dashboard import _pasta_usuario
    assert _pasta_usuario("2320 - Superv_RS/SC - ALITSON") ==         "2320 - Superv_RS-SC - ALITSON"
    assert _pasta_usuario('a<b>c:d"e|f?g*h\i') == "a-b-c-d-e-f-g-h-i"


# ==================================== D-50 · RTM + saneamento (02/09, Fase 2)
def _dim_saneamento():
    """DIM minima: um distribuidor com estrutura completa (800), um cliente
    RTM com distribuidor (900), um RTM sem distribuidor (901) e tres clientes
    da lista Faltando (910 NAO sem sell-in recente, 911 NAO com sell-in
    recente, 912 SIM ja na consolidada)."""
    na = "NÃO ATRIBUÍDO"
    dim = pd.DataFrame({
        "COD_CLIENTE": ["800", "900", "901", "910", "911", "912"],
        "NOME_CLIENTE": ["DISTRIB X", "CLI RTM", "CLI RTM 2", "CLI 910",
                         "CLI 911", "CLI 912"],
        "BANDEIRA": ["DISTRIB X", "MERCADO Y", "MERCADO Z", "B1", "B2", "B3"],
        "UF": ["SP", "MG", "MG", "SP", "SP", "SP"],
        "HEAD": ["10 - H1", na, na, na, na, "10 - H1"],
        "GERENTE": ["1000 - G1", na, na, na, na, "1000 - G1"],
        "SUPERVISOR": ["1100 - S1", na, na, na, na, "1100 - S1"],
        "VENDEDOR": ["111 - V1", na, na, na, na, "111 - V1"],
        "PROJETO": ["P1", na, na, na, na, "P1"],
        "CANAL": ["DISTRIBUIDOR", "VAREJO", "VAREJO", "VAREJO", "VAREJO",
                  "VAREJO"],
        "SUBCANAL": ["D1", "V1", "V1", "V1", "V1", "V1"],
        "NA_ESTRUTURA": [True, False, False, False, False, True],
        "TEM_CANAL": [True] * 6,
    })
    fato = pd.DataFrame({
        # 910: so sell-in ANTIGO (2026-01). 911: sell-in dentro da janela.
        "ANO_MES": ["2026-08", "2026-08", "2026-08", "2026-01", "2026-08",
                    "2026-08"],
        "COD_CLIENTE": ["800", "900", "901", "910", "911", "912"],
        "COD_PRODUTO": ["10"] * 6,
        "RECEITA": [100.0] * 6,
        "PESO_KG": [10.0] * 6,
        "CAIXAS": [1.0] * 6,
    })
    rtm = pd.DataFrame({
        "COD_CLIENTE": ["900", "901"],
        "BANDEIRA_ANTIGA": ["MERCADO Y", "MERCADO Z"],
        "DISTRIBUIDOR": ["DISTRIB X", "NOVO ALGUM LUGAR"],
        "COD_DISTRIBUIDOR": pd.array(["800", None], dtype="string"),
    })
    faltando = pd.DataFrame({
        "COD_CLIENTE": ["910", "911", "912"],
        "NOME_FALTANDO": ["CLI 910", "CLI 911", "CLI 912"],
        "HIERARQUIA": ["NÃO", "NÃO", "SIM"],
    })
    return dim, rtm, faltando, fato


def test_d50_rtm_herda_hierarquia_e_canal_do_distribuidor():
    """D-50/Q4-a: hierarquia, projeto e canal vem do distribuidor; a UF e o
    proprio codigo do cliente NAO mudam. (A bandeira saiu deste teste na D-59
    — virou parametro, com teste proprio dos dois modos.)"""
    from src.transform import saneamento
    dim, rtm, falt, fato = _dim_saneamento()
    d, med, _ = saneamento.aplicar(dim, rtm, falt, fato, mes_execucao="2026-09")
    c = d.set_index("COD_CLIENTE").loc["900"]
    assert c["HEAD"] == "10 - H1" and c["VENDEDOR"] == "111 - V1"
    assert c["CANAL"] == "DISTRIBUIDOR" and c["CANAL_ORIGINAL"] == "VAREJO"
    assert bool(c["NA_ESTRUTURA"]) is True
    assert c["UF"] == "MG"                     # UF segue do cliente
    assert bool(c["ORIGEM_RTM"]) and c["COD_DISTRIBUIDOR"] == "800"
    # o distribuidor em si nao e tocado
    assert d.set_index("COD_CLIENTE").loc["800", "CANAL"] == "DISTRIBUIDOR"
    assert med["rtm_reatribuidos"] == 1


def _com_flag_bandeira(valor: bool):
    """Roda o saneamento com `rtm_herda_bandeira` forcado, para exercitar os
    DOIS caminhos independentemente do que o config traz hoje."""
    from src.transform import saneamento
    dim, rtm, falt, fato = _dim_saneamento()
    original = saneamento._SAN
    saneamento._SAN = {**original, "rtm_herda_bandeira": valor}
    try:
        return saneamento.aplicar(dim, rtm, falt, fato,
                                  mes_execucao="2026-09")
    finally:
        saneamento._SAN = original


def test_d59_cliente_rtm_herda_a_bandeira_do_distribuidor():
    """D-59 (03/09/2026): com o parametro ligado, o cliente RTM passa a
    carregar a bandeira do DISTRIBUIDOR — e os dois caem na MESMA linha da aba
    Bandeiras, que e o objetivo. A bandeira vem do distribuidor na DIM (a do
    sell-in dele), nunca do nome do cadastro: usar o cadastro aqui partiria
    cada distribuidor em duas bandeiras."""
    d, med, avisos = _com_flag_bandeira(True)
    i = d.set_index("COD_CLIENTE")
    assert i.loc["900", "BANDEIRA"] == "DISTRIB X"      # herdada
    assert i.loc["800", "BANDEIRA"] == "DISTRIB X"      # a MESMA do distribuidor
    # nada se perde: a bandeira de origem fica registrada
    assert i.loc["900", "BANDEIRA_ORIGINAL"] == "MERCADO Y"
    assert med["rtm_bandeira_herdada"] == 1
    assert any("BANDEIRA do distribuidor" in a for a in avisos), \
        "a regra tem de sair no log — nada acontece em silencio"
    # UF continua do cliente; a D-59 nao a toca
    assert i.loc["900", "UF"] == "MG"


def test_d59_desligado_volta_ao_comportamento_da_q4a():
    """O parametro e o caminho de rollback: `false` no config devolve a regra
    antiga sem tocar em uma linha de codigo."""
    d, med, _ = _com_flag_bandeira(False)
    i = d.set_index("COD_CLIENTE")
    assert i.loc["900", "BANDEIRA"] == "MERCADO Y"      # preservada (Q4-a)
    assert i.loc["900", "BANDEIRA_ORIGINAL"] == "MERCADO Y"
    assert "rtm_bandeira_herdada" not in med


def test_d59_distribuidor_sem_bandeira_nao_piora_o_cliente():
    """Guarda: herdar 'SEM BANDEIRA' trocaria um rotulo real por um balde de
    ausencia — o oposto do objetivo. Nesse caso o cliente mantem a propria."""
    from src.transform import saneamento
    from src.utils.config import CFG
    sem = CFG["dimensoes"]["rotulo_sem_bandeira"]
    dim, rtm, falt, fato = _dim_saneamento()
    dim = dim.copy()
    dim.loc[dim["COD_CLIENTE"] == "800", "BANDEIRA"] = sem
    original = saneamento._SAN
    saneamento._SAN = {**original, "rtm_herda_bandeira": True}
    try:
        d, med, _ = saneamento.aplicar(dim, rtm, falt, fato,
                                       mes_execucao="2026-09")
    finally:
        saneamento._SAN = original
    assert d.set_index("COD_CLIENTE").loc["900", "BANDEIRA"] == "MERCADO Y"
    assert med["rtm_bandeira_herdada"] == 0


def test_d59_nao_mexe_em_receita_nenhuma():
    """A D-59 troca um rotulo na DIM_CLIENTE. A fato nao e tocada, entao o
    total nao muda — o que muda e sob qual bandeira ele aparece."""
    ligado, _, _ = _com_flag_bandeira(True)
    desligado, _, _ = _com_flag_bandeira(False)
    assert len(ligado) == len(desligado)
    assert set(ligado["COD_CLIENTE"]) == set(desligado["COD_CLIENTE"])
    # so a coluna BANDEIRA difere, e so nas linhas de cliente RTM
    dif = ligado.set_index("COD_CLIENTE")["BANDEIRA"].ne(
        desligado.set_index("COD_CLIENTE")["BANDEIRA"])
    assert set(dif[dif].index) == {"900"}


def test_d50_rtm_sem_distribuidor_fica_fora_da_hierarquia_com_flag():
    from src.transform import saneamento
    dim, rtm, falt, fato = _dim_saneamento()
    d, med, _ = saneamento.aplicar(dim, rtm, falt, fato, mes_execucao="2026-09")
    c = d.set_index("COD_CLIENTE").loc["901"]
    assert c["HEAD"] == "NÃO ATRIBUÍDO"          # nada inventado
    assert c["CANAL"] == "VAREJO"                # canal original mantido
    assert bool(c["ORIGEM_RTM"]) and pd.isna(c["COD_DISTRIBUIDOR"])
    assert med["rtm_sem_distribuidor"] == 1


def test_d50_inativacao_exige_as_duas_condicoes():
    from src.transform import saneamento
    from src.utils.config import CFG
    rot = CFG["dimensoes"]["rotulo_inativo"]
    dim, rtm, falt, fato = _dim_saneamento()
    d, med, _ = saneamento.aplicar(dim, rtm, falt, fato, mes_execucao="2026-09")
    i = d.set_index("COD_CLIENTE")
    # 910: NAO + sem sell-in na janela -> INATIVO no balde proprio
    assert bool(i.loc["910", "INATIVO"]) and i.loc["910", "HEAD"] == rot
    assert i.loc["910", "VENDEDOR"] == rot
    # Q7-i: canal/bandeira ficam — o historico permanece nos totais
    assert i.loc["910", "CANAL"] == "VAREJO"
    # 911: NAO + COM sell-in -> caso nao coberto, NADA aplicado (Q5)
    assert not bool(i.loc["911", "INATIVO"])
    assert bool(i.loc["911", "SANEAMENTO_PENDENTE"])
    assert i.loc["911", "HEAD"] == "NÃO ATRIBUÍDO"
    # 912: SIM ja na consolidada -> intocado, sem pendencia
    assert i.loc["912", "HEAD"] == "10 - H1"
    assert med["inativados"] == 1 and med["nao_cobertos"] == 1
    assert med["sim_pendentes"] == 0


def test_d50_janela_ancora_na_ultima_competencia_fechada():
    from src.transform import saneamento
    fato = pd.DataFrame({"ANO_MES": ["2026-03", "2026-04", "2026-05",
                                     "2026-06", "2026-07", "2026-08",
                                     "2026-09"],
                         "COD_CLIENTE": ["1"] * 7})
    # execucao em setembro: set/26 (parcial) fica FORA; a janela fecha em ago.
    jan = saneamento._janela(fato, "2026-09")
    assert jan == ["2026-03", "2026-04", "2026-05",
                   "2026-06", "2026-07", "2026-08"]
    # a janela e de CALENDARIO: serie esparsa nao a estica para tras
    esparso = pd.DataFrame({"ANO_MES": ["2026-01", "2026-08", "2026-09"],
                            "COD_CLIENTE": ["1"] * 3})
    assert saneamento._janela(esparso, "2026-09") == [
        "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08"]
    # e atravessa a virada do ano sem erro de aritmetica
    assert saneamento._mes_menos("2026-02", 5) == "2025-09"


def test_d50_precedencia_rtm_sobre_saneamento():
    """5.4: cliente nas duas bases segue a regra RTM e o conflito e reportado."""
    from src.transform import saneamento
    dim, rtm, falt, fato = _dim_saneamento()
    falt2 = pd.concat([falt, pd.DataFrame({
        "COD_CLIENTE": ["900"], "NOME_FALTANDO": ["CLI RTM"],
        "HIERARQUIA": ["NÃO"]})], ignore_index=True)
    d, med, avisos = saneamento.aplicar(dim, rtm, falt2, fato,
                                        mes_execucao="2026-09")
    c = d.set_index("COD_CLIENTE").loc["900"]
    assert c["HEAD"] == "10 - H1" and not bool(c["INATIVO"])
    assert med["conflito_rtm_saneamento"] == 1
    assert any("DUAS bases" in a for a in avisos)


# ============================== D-51 · Fase 3: cubos sem o eixo UF (02/09)
def test_d51_cubos_sem_eixo_uf_e_posicoes_do_template():
    """Q10: o eixo UF saiu dos dois cubos. As posicoes que o template v4 le
    (metricas a partir da coluna 4; perfil em 3/2; bandeira em 1/3) sao o
    contrato — mudar exige mudar o template junto."""
    from src.load import cubos
    pac = cubos.construir(*_mini_modelo())
    assert "uf" not in pac["dims"]
    assert all(len(l) == 7 for l in pac["cubo"])
    # soma da receita na posicao 4 = total do mini modelo (R$ 2.100 em centavos)
    assert sum(l[4] for l in pac["cubo"]) == 210000
    assert sum(l[3] for l in pac["cubo_sku"]) == 210000    # D-64: 3 indices
    # bandeira do cubo principal segue na posicao 1
    assert all(l[1] < len(pac["dims"]["ban"]) for l in pac["cubo"])



# =========================================== D-54 / D-55 (03/09/2026)
def _modelo_dois_canais():
    """`_mini_modelo` com os dois heads em canais DIFERENTES — e o unico jeito
    de provar que o recorte encolhe a lista de canais do arquivo."""
    fato, dim_cli, dim_prod, dim_cal = _mini_modelo()
    dim_cli = dim_cli.copy()
    dim_cli["CANAL"] = ["VAREJO"] * 4 + ["ATACADO"] * 2
    return fato, dim_cli, dim_prod, dim_cal


def test_d54_recorte_encolhe_canal_categoria_e_sku_do_arquivo():
    """D-54: o arquivo de um nivel so carrega as dimensoes que existem NELE.

    E a causa do problema relatado em 03/09: o painel do head exibia o chip de
    um canal em que o squad dele nao tem uma unica linha, porque `dims.canal`
    viajava do tamanho da empresa inteira. Ate a D-52 so `perfil` e `head`
    encolhiam. Nao ha lista de nomes em lugar nenhum — quem decide e o cubo."""
    from src.load import cubos
    from run_dashboard import filtrar_por_nivel
    pac = cubos.construir(*_modelo_dois_canais())
    assert set(pac["dims"]["canal"]) == {"ATACADO", "VAREJO"}
    assert set(pac["dims"]["cat"]) == {"BALA", "GOMAS"}

    h1 = filtrar_por_nivel(pac, 0, "10 - H1")
    assert h1["dims"]["head"] == ["10 - H1"]
    assert h1["dims"]["canal"] == ["VAREJO"]      # ATACADO nao esta no arquivo
    h2 = filtrar_por_nivel(pac, 0, "20 - H2")
    assert h2["dims"]["canal"] == ["ATACADO"]
    # H2 so movimenta o SKU 30, da categoria BALA
    assert h2["dims"]["cat"] == ["BALA"]
    assert [s[0] for s in h2["dims"]["sku"]] == ["30"]
    # e a regra vale em QUALQUER nivel, nao so no head (aqui o N3)
    s3 = filtrar_por_nivel(pac, 2, "2100 - S3")
    assert s3["dims"]["canal"] == ["ATACADO"] and s3["dims"]["cat"] == ["BALA"]


def test_d54_reindexacao_de_categoria_e_sku_aponta_para_o_rotulo_certo():
    """Encolher a lista sem remapear os indices apontaria para a categoria
    errada — o erro mais silencioso possivel, porque a soma continuaria
    fechando. Os DOIS cubos sao conferidos, e o dinheiro tem de ser o mesmo."""
    from src.load import cubos
    from run_dashboard import filtrar_por_nivel
    pac = cubos.construir(*_mini_modelo())
    rec = filtrar_por_nivel(pac, 0, "20 - H2")
    cats, skus = rec["dims"]["cat"], rec["dims"]["sku"]
    assert all(cats[l[2]] == "BALA" for l in rec["cubo"])
    assert all(cats[skus[l[1]][2]] == "BALA" for l in rec["cubo_sku"])
    assert all(skus[l[1]][0] == "30" for l in rec["cubo_sku"])
    assert sum(l[4] for l in rec["cubo"]) == 110000          # R$ 1.100,00
    assert sum(l[3] for l in rec["cubo_sku"]) == 110000


def test_d54_recorte_preserva_o_calendario():
    """`cal` fica intacto DE PROPOSITO: remapear mes reindexaria os dois cubos
    e os ponteiros de LY (mes sem faturamento e resolvido na interface)."""
    from src.load import cubos
    from run_dashboard import filtrar_por_nivel
    pac = cubos.construir(*_mini_modelo())
    rec = filtrar_por_nivel(pac, 0, "20 - H2", "N1")
    assert rec["cal"] == pac["cal"]


# ============================================ D-65 (03/09/2026): bandeiras
def _modelo_tres_bandeiras():
    """H1 (clientes 1-4) fatura em REDE A e REDE B; H2 (5-6) so em REDE C —
    assim o recorte tem o que encolher."""
    fato, dim_cli, dim_prod, dim_cal = _mini_modelo()
    dim_cli = dim_cli.copy()
    dim_cli["BANDEIRA"] = ["REDE A", "REDE B", "REDE A", "REDE B",
                           "REDE C", "REDE C"]
    return fato, dim_cli, dim_prod, dim_cal


def test_d65_cubo_carrega_todas_as_bandeiras_sem_balde():
    """D-65: o gerador nao agrega mais 'DEMAIS BANDEIRAS' na origem — toda
    bandeira com sell-in e uma linha do cubo, e o corte e so de exibicao
    (`top`, lido pelo template). Nada chega ao template com o rotulo do
    balde, nem a contagem por nivel da D-57 (superada)."""
    from src.load import cubos
    from src.utils.config import CFG
    pac = cubos.construir(*_modelo_tres_bandeiras())
    assert set(pac["dims"]["ban"]) == {"REDE A", "REDE B", "REDE C"}
    assert not any("DEMAIS" in b for b in pac["dims"]["ban"])
    c = pac["corte_bandeira"]
    assert c["top"] == int(CFG["dashboard"]["top_bandeiras"])
    assert c["universo"] == 3 and c["exibir_todas"] is False
    assert "rotulo_base" in c and "rotulo_demais" not in c
    assert "demais_por_nivel" not in pac
    assert sum(l[4] for l in pac["cubo"]) == 210000


def test_d65_recorte_leva_so_as_bandeiras_do_escopo_reindexadas():
    """O arquivo de um colaborador carrega SO as bandeiras do escopo dele
    (nem o nome das outras viaja), com os indices do cubo remapeados, e o
    dinheiro nao muda. N1 recebe o corte de exibicao; N2/N3 exibem todas
    (config `exibir_todas_bandeiras_em`)."""
    from src.load import cubos
    from run_dashboard import filtrar_por_nivel
    pac = cubos.construir(*_modelo_tres_bandeiras())
    h2 = filtrar_por_nivel(pac, 0, "20 - H2", "N1")
    assert h2["dims"]["ban"] == ["REDE C"]
    assert all(l[1] < len(h2["dims"]["ban"]) for l in h2["cubo"])
    assert sum(l[4] for l in h2["cubo"]) == 110000            # R$ 1.100,00
    assert h2["corte_bandeira"]["universo"] == 1
    assert h2["corte_bandeira"]["exibir_todas"] is False      # N1: corte
    h1 = filtrar_por_nivel(pac, 0, "10 - H1", "N1")
    assert set(h1["dims"]["ban"]) == {"REDE A", "REDE B"}
    s3 = filtrar_por_nivel(pac, 2, "2100 - S3", "N3")
    assert s3["dims"]["ban"] == ["REDE C"]
    assert s3["corte_bandeira"]["exibir_todas"] is True       # N3: todas
    g2 = filtrar_por_nivel(pac, 1, "2000 - G2", "N2") if any(
        p[1] == "2000 - G2" for p in pac["dims"]["perfil"]) else None
    if g2:
        assert g2["corte_bandeira"]["exibir_todas"] is True
    # o pacote global nao e mutado pelos recortes
    assert len(pac["dims"]["ban"]) == 3
    # particionamento por nivel continua fechando
    heads = {p[0] for p in pac["dims"]["perfil"]}
    assert sum(sum(l[4] for l in filtrar_por_nivel(pac, 0, h, "N1")["cubo"])
               for h in heads) == 210000


def test_d66_template_tem_busca_de_bandeira_e_sku_persistida():
    """D-66: campos #bBan e #bSku, busca sem acento (semAcento), estado
    qBan/qSku gravado no recorte e ignorando o corte de exibicao."""
    corpo = _sem_comentarios(_ler_templates()["template_v4.html"])
    for termo in ('id="bBan"', 'id="bSku"', "function semAcento",
                  "qBan:F.qBan", "F.qSku=r.qSku", "busca:{nivel:0",
                  "busca:{nivel:1"):
        assert termo in corpo, f"template v4 perdeu a busca (D-66): {termo}"


def test_d68_rotulos_de_exibicao_vem_do_config_e_nao_do_template():
    """D-68: o texto de leitor das linhas Σ mora em
    `dashboard.rotulos_exibicao` e chega ao template por DB.rotulos_exibicao;
    o template nao carrega o texto (nem a chave de dado) escrito."""
    from src.utils.config import CFG
    exib = CFG["dashboard"].get("rotulos_exibicao") or {}
    assert exib.get("sem_estrutura") and exib.get("inativo")
    corpo = _sem_comentarios(_ler_templates()["template_v4.html"])
    assert "DB.rotulos_exibicao" in corpo and "EXIBE(" in corpo
    assert exib["sem_estrutura"] not in corpo and exib["inativo"] not in corpo


def test_d67_colunas_de_decisao_antes_da_serie():
    """D-67: nas tres matrizes o cabecalho e nome | ATUAL | ANT. | Δ | Δ% |
    Part. % | serie... | TOTAL — e a exportacao segue a mesma ordem."""
    corpo = _sem_comentarios(_ler_templates()["template_v4.html"])
    assert '{v:"ATUAL"},{v:"ANT."},{v:"Δ"},{v:"Δ%"},{v:"Part. %"}]' in corpo
    assert '.concat([{v:"TOTAL",c:"serie corte"}])' in corpo
    assert '["Item","ATUAL","ANT.","Δ","Δ%","Part. %"].concat(cols.map(rotCol))' in corpo


def test_d65_template_monta_o_corte_na_tela():
    """O template nao procura mais o balde pelo rotulo (`D.ban.indexOf`), monta
    a linha Σ do corte de exibicao ele mesmo (`__resto__`) e respeita
    `exibir_todas`."""
    corpo = _sem_comentarios(_ler_templates()["template_v4.html"])
    assert "__resto__" in corpo and "exibir_todas" in corpo
    assert "rotulo_demais" not in corpo and "D.ban.indexOf" not in corpo


def test_d63_periodo_inicial_no_ultimo_mes_fechado():
    """D-63 (03/09/2026): o v4 abre no FY corrente ate o ultimo mes fechado,
    caindo para o FY anterior quando o corrente nao tem mes fechado. A guarda
    e textual (o motor e JS): a funcao e a chave v5 do recorte salvo — sem a
    chave nova o padrao antigo ("set/26") continuaria vindo do localStorage."""
    txt = _ler_templates()["template_v4.html"]
    corpo = _sem_comentarios(txt)
    assert "function periodoInicial" in corpo
    assert "periodoInicial();" in corpo, "iniciar() tem de chamar o periodo inicial"
    assert "dashDoriCanais.recorte.v5" in corpo
    assert "dashDoriCanais.recorte.v4" not in corpo


def _ler_templates():
    from src.utils.config import caminho
    raiz = Path(__file__).resolve().parents[1]
    achados = {}
    for nome in ("template_v4.html", "template_v3.html"):
        arq = raiz / "dashboard" / nome
        if arq.exists():
            achados[nome] = arq.read_text(encoding="utf-8")
    assert achados, "nenhum template encontrado em dashboard/"
    return achados


def test_d54_template_decide_visibilidade_pelo_dado_e_nao_por_lista_de_nomes():
    """Guarda de regressao lida no TEMPLATE, como texto. A visibilidade tem de
    sair do cubo: um nome de head, de pessoa ou de canal escrito no template
    seria a correcao pontual que a governanca proibe."""
    proibidos = ["MICHEL", "ADEMIR", "IZABELA", "MAYKON",
                 "CASH & CARRY", "ATACADO GENERALISTA", "VAREJO ESPECIALIZADO"]
    for nome, txt in _ler_templates().items():
        alto = _sem_comentarios(txt).upper()
        for termo in proibidos:
            assert termo not in alto, f"{nome} carrega o valor de negocio {termo!r}"
        assert "atualizarOpcoes" in txt or "opcoesComDado" in txt, \
            f"{nome} perdeu a funcao de visibilidade dinamica (D-54)"


def _sem_comentarios(txt: str) -> str:
    """Tira comentarios /* */ e // do template.

    Existe porque a 1a versao desta guarda dava FALSO POSITIVO: os templates
    documentam, em comentario, que `.chip.semdado` e `marcarChipsVazios`
    SAIRAM — e o teste acusava a propria documentacao da remocao. O que
    interessa e o codigo: a regra CSS e a funcao, nao a mencao a elas.
    """
    fora, i, n = [], 0, len(txt)
    while i < n:
        j = txt.find("/*", i)
        if j < 0:
            fora.append(txt[i:])
            break
        fora.append(txt[i:j])
        k = txt.find("*/", j + 2)
        i = n if k < 0 else k + 2
    limpo = "".join(fora)
    return "\n".join(l for l in limpo.split("\n")
                     if not l.lstrip().startswith("//"))


def test_d51_nada_cinza_continua_valendo_depois_da_d54():
    """A D-54 esconde, nunca esmaece: o estado cinza segue proibido.

    Lido no CODIGO (comentarios fora): a regra CSS `.chip.semdado{`, a funcao
    `marcarChipsVazios` e qualquer `[disabled]` nao podem voltar."""
    for nome, txt in _ler_templates().items():
        codigo = _sem_comentarios(txt)
        assert ".chip.semdado{" not in codigo.replace(" ", ""), \
            f"{nome} reintroduziu a regra do chip esmaecido"
        assert "marcarChipsVazios" not in codigo, \
            f"{nome} voltou a marcar em vez de esconder"
        assert "[disabled]" not in codigo, \
            f"{nome} reintroduziu elemento desabilitado"
        # a marca de ausencia de dado agora e um CONTADOR, nao um estado cinza
        assert "opacity:.38" not in codigo.replace(" ", ""), \
            f"{nome} reintroduziu esmaecimento por opacidade"


def test_d55_template_tem_uma_unica_escada_de_formatacao():
    """D-55: `abrev` e a unica formatacao de metrica. As duas concorrentes
    (`rotCurto` no grafico e `escalaFixa` nas matrizes) nao podem voltar —
    era delas a divergencia "112,7 mi" no rotulo x "R$ 112,74 mi" no tooltip."""
    for nome, txt in _ler_templates().items():
        corpo = _sem_comentarios(txt)
        for morto in ("const rotCurto", "function escalaFixa"):
            assert morto not in corpo, f"{nome} reintroduziu {morto}"
        assert "const ESCALAS" in corpo, f"{nome} perdeu a tabela unica de escala"
        # o prefixo de moeda nunca e literal: sai da unidade da metrica
        assert 'un==="R$"' in corpo, f"{nome} perdeu o prefixo dirigido pela metrica"


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
