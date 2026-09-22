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
        # D-72: o cubo exige nome e a flag de bandeira herdada (RTM)
        "NOME_CLIENTE": ["CLI 1", "CLI 2", "CLI 3", "CLI 4", "CLI 5", "CLI 6"],
        "BANDEIRA_HERDADA": [False] * 6,
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
        # D-71: a posicao 6 e a flag "vendedor e o proprio sup./exec."
        assert len(p) == 7, "o perfil carrega os seis componentes + a flag da D-71"
        assert p[6] in (0, 1)
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
        por_sup_principal[k] = por_sup_principal.get(k, 0) + l[cubos.BASE_MET]
    for l in pac["cubo_sku"]:
        k = perfil[l[2]][2]
        por_sup_sku[k] = por_sup_sku.get(k, 0) + l[cubos.BASE_MET_SKU]
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
    assert sum(l[cubos.BASE_MET] for l in rec["cubo"]) == 100000      # R$ 1.000,00
    assert sum(l[cubos.BASE_MET_SKU] for l in rec["cubo_sku"]) == 100000


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
    assert sum(l[cubos.BASE_MET] for l in rec["cubo"]) == 70000       # R$ 700,00
    # a lista de heads do arquivo encolhe junto (chips coerentes)
    assert rec["dims"]["head"] == ["10 - H1"]
    # particionamento do nivel N3: soma dos 3 sups = total
    sups = {p[2] for p in pac["dims"]["perfil"]}
    soma = sum(sum(l[cubos.BASE_MET] for l in filtrar_por_nivel(pac, 2, s)["cubo"])
               for s in sups)
    assert soma == sum(l[cubos.BASE_MET] for l in pac["cubo"]) == 210000


def test_d73_full_publica_na_subpasta_do_config_ou_na_raiz():
    """D-73 (04/09/2026): o Full vai para `publicacao.pasta_full`; vazia ou
    ausente = raiz (Q13). O config atual aponta para uma subpasta."""
    from pathlib import Path
    from run_dashboard import pasta_do_full
    from src.utils.config import CFG
    d = Path("X")
    assert pasta_do_full(d, {"pasta_full": "Dashboard - Full"}) == d / "Dashboard - Full"
    assert pasta_do_full(d, {"pasta_full": "  "}) == d
    assert pasta_do_full(d, {}) == d
    assert str(CFG["dashboard"]["publicacao"].get("pasta_full") or "").strip(), \
        "o config tem de declarar a pasta do Full (decisao do Douglas, D-73)"


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
    (perfil em 3/2; bandeira em 1; metricas a partir de cubos.BASE_MET, que
    era 4 e virou 5 na D-72 com o cliente na posicao 4) sao o contrato —
    mudar exige mudar o template junto."""
    from src.load import cubos
    pac = cubos.construir(*_mini_modelo())
    assert "uf" not in pac["dims"]
    assert all(len(l) == 8 for l in pac["cubo"])       # D-72: + cliente
    # soma da receita em BASE_MET = total do mini modelo (R$ 2.100 em centavos)
    assert sum(l[cubos.BASE_MET] for l in pac["cubo"]) == 210000
    assert sum(l[cubos.BASE_MET_SKU] for l in pac["cubo_sku"]) == 210000    # D-64: 3 indices
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
    assert sum(l[cubos.BASE_MET] for l in rec["cubo"]) == 110000          # R$ 1.100,00
    assert sum(l[cubos.BASE_MET_SKU] for l in rec["cubo_sku"]) == 110000


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
    assert sum(l[cubos.BASE_MET] for l in pac["cubo"]) == 210000


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
    assert sum(l[cubos.BASE_MET] for l in h2["cubo"]) == 110000            # R$ 1.100,00
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
    assert sum(sum(l[cubos.BASE_MET] for l in filtrar_por_nivel(pac, 0, h, "N1")["cubo"])
               for h in heads) == 210000


def test_d66_template_tem_busca_de_bandeira_e_sku_persistida():
    """D-66: campos #bBan e #bSku, busca sem acento (semAcento), estado
    qBan/qSku gravado no recorte e ignorando o corte de exibicao."""
    corpo = _sem_comentarios(_ler_templates()["template_v4.html"])
    for termo in ('id="bBan"', 'id="bSku"', "function semAcento",
                  "qBan:F.qBan", "F.qSku=r.qSku", "busca:{nivel:0",
                  "busca:{nivel:1"):
        assert termo in corpo, f"template v4 perdeu a busca (D-66): {termo}"
    # D-78: a busca da aba Bandeiras acha a bandeira tambem pelo CLIENTE
    # (codigo ou nome), decidido na carga (BAN_CLIS); bandeira achada por um
    # cliente abre mostrando so os clientes que casam
    for termo in ("BAN_CLIS[b].add(c);",
                  "casaExtra:(b,q)=>[...BAN_CLIS[+b]].some(ci=>semAcento(rotCli(ci)).includes(q))",
                  'filhoCasa:(k,q)=> tipo(k)!=="c" || semAcento(rotCli(+String(k).slice(1))).includes(q)',
                  "const casa0 = (k)=> casa(0,k) || casaExtra(k);",
                  "|| (nivel===0 && viaFilho(n)));",
                  'placeholder="bandeira ou cliente (código ou nome)'):
        assert termo in corpo, f"template v4 perdeu a busca por cliente (D-78): {termo}"


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


def test_d69_filtro_hierarquico_vale_nos_dois_cubos():
    """D-69: gerente, sup./exec. e vendedor filtram pelo perfil nos DOIS
    cubos (`passaPerfil`), entram no recorte salvo e no "Limpar"; as linhas
    obedecem a D-54 (chips com dado)."""
    corpo = _sem_comentarios(_ler_templates()["template_v4.html"])
    for termo in ("function passaPerfil", 'id="fGer"', 'id="fSup"', 'id="fVend"',
                  "F.ger.has(p[P_GER])", "F.sup.has(p[P_SUP])",
                  "F.vend.has(p[P_VEND])", "ger:[...F.ger]",
                  'DIMS_FILTRO = ["cat","can","head","ger","sup","vend","ban","cli"]'):
        assert termo in corpo, f"template v4 perdeu o filtro hierarquico: {termo}"
    # lista suspensa (decisao de 04/09), alimentada pelo perfil do cubo (D-54)
    assert "function listaSuspensa" in corpo
    assert "lista(P_GER)" in corpo and "lista(P_VEND, p=>!vendEhSup(p))" in corpo
    assert '<select class="lista" id="fGer">' in corpo


def test_d71_vendedor_que_e_o_proprio_sup_nao_desce_um_nivel():
    """D-71: a flag do perfil (posicao 6) marca o Vend./RCA que e a mesma
    pessoa do Sup./Exec. (pelo NOME; codigo e papel sempre diferem). O
    template usa a flag para nao expandir a linha e nao oferecer o vendedor
    no filtro. Rotulos de ausencia nunca casam."""
    from src.load import cubos
    fato, dim_cli, dim_prod, dim_cal = _mini_modelo()
    dim = dim_cli.copy()
    # clientes 1-2: sup e vendedor sao a MESMA pessoa (nomes iguais, codigos e
    # papeis diferentes, um deles com " - " dentro dos colchetes)
    dim.loc[dim["COD_CLIENTE"].isin(["1", "2"]), "SUPERVISOR"] = "1100 - Superv_X - [VAGO - JOAO 1]"
    dim.loc[dim["COD_CLIENTE"].isin(["1", "2"]), "VENDEDOR"] = "900 - TT Superv_X - [VAGO - JOAO 1]"
    pac = cubos.construir(fato, dim, dim_prod, dim_cal)
    assert all(len(p) == 7 for p in pac["dims"]["perfil"])
    flags = {(p[2], p[5]): p[6] for p in pac["dims"]["perfil"]}
    assert flags[("1100 - Superv_X - [VAGO - JOAO 1]", "900 - TT Superv_X - [VAGO - JOAO 1]")] == 1
    assert all(v == 0 for k, v in flags.items() if k[0] != "1100 - Superv_X - [VAGO - JOAO 1]")
    assert cubos._mesma_pessoa("NÃO ATRIBUÍDO", "NÃO ATRIBUÍDO") is False
    assert cubos._mesma_pessoa("2140 - Exec TA_SPC - RONALDO SILVA",
                               "540 - TT Rep DAT - (540) Rep DAT") is False
    corpo = _sem_comentarios(_ler_templates()["template_v4.html"])
    assert "P_VEND_E_SUP=6" in corpo and "vendEhSup(pf)) caminho.pop()" in corpo


def test_d70_sem_notas_de_rodape():
    """D-70: os cards nao tem mais .note; nenhuma funcao escreve em nEvo,
    nHier, nBan ou nCat."""
    corpo = _sem_comentarios(_ler_templates()["template_v4.html"])
    assert 'class="note"' not in corpo and "function notaMatriz" not in corpo
    for alvo in ("nEvo", "nHier", "nBan", "nCat"):
        assert f'el("{alvo}")' not in corpo, alvo


def test_d67_colunas_de_decisao_antes_da_serie():
    """D-67: nas tres matrizes o cabecalho e nome | ATUAL | ANT. | Δ | Δ% |
    Part. % | serie... | TOTAL — e a exportacao segue a mesma ordem.
    D-74: META e ATING. % entram entre ATUAL e ANT., so quando ha meta
    (`colsMeta` vazio sem meta), e a exportacao acompanha."""
    corpo = _sem_comentarios(_ler_templates()["template_v4.html"])
    # D-75: ATUAL = ano selecionado (rotAtual), ANT. = LY, ultima = YTD
    assert ('{v:rotAtual}].concat(colsMeta).concat([{v:"LY"},{v:"Δ"},{v:"Δ%"},'
            '{v:"Part. %"}])') in corpo
    assert '.concat([{v:rotYtd,c:"serie corte"}])' in corpo
    assert ('["Item",txtAtual].concat(mostraMeta?[rotMeta,rotAting]:[])'
            in corpo)
    assert '.concat(["LY","Δ","Δ%","Part. %"]).concat(cols.map(rotCol))' in corpo
    # D-75: o YTD e o acumulado do ano selecionado, nao a soma da serie
    for termo in ("function mesesYtd(p)", "function rotuloAnoSel()",
                  "const mapY = soma(ytd);", "const tot=n=>n.y;",
                  'const txtYtd = "YTD "+anoRot;'):
        assert termo in corpo, f"template v4 perdeu a D-75: {termo}"
    assert "n.serie.reduce((s,v)=>s+v,0)" not in corpo, \
        "a ultima coluna voltou a somar a serie exibida em vez do YTD"


def test_d79_serie_da_matriz_segue_o_filtro_de_periodo():
    """D-79 (11/09/2026): as colunas de mes das matrizes sao os meses
    SELECIONADOS (p.atual), agrupados pelo "Ver por", como o grafico de
    Evolucao. Antes eram os 12 ultimos meses do arquivo, qualquer que fosse o
    filtro: a guarda falha se a serie voltar a andar pelo calendario inteiro."""
    corpo = _sem_comentarios(_ler_templates()["template_v4.html"])
    assert "function colunasSerie(p){" in corpo
    assert "for(const i of p.atual){" in corpo
    assert "const cols=colunasSerie(p);" in corpo
    assert "function gruposSerie" not in corpo, \
        "a serie voltou a percorrer todos os meses do arquivo"
    ini = corpo.index("function colunasSerie(p){")
    fim = corpo.index("\n}", ini)
    assert "NM" not in corpo[ini:fim], "colunasSerie nao pode andar por NM"


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


# ===================== D-72 (04/09/2026): cliente como eixo do cubo principal
def _modelo_rtm_acumulado():
    """H1: o cliente 1 e um DISTRIBUIDOR de bandeira 'DIST X'; os clientes 3
    e 4 sao RTM que HERDARAM essa bandeira (flag da D-59/D-72); o 2 e uma
    rede comum. H2 (5-6) fica em REDE C."""
    fato, dim_cli, dim_prod, dim_cal = _mini_modelo()
    dim = dim_cli.copy()
    dim["BANDEIRA"] = ["DIST X", "REDE B", "DIST X", "DIST X", "REDE C", "REDE C"]
    dim["BANDEIRA_HERDADA"] = [False, False, True, True, False, False]
    return fato, dim, dim_prod, dim_cal


def test_d72_cliente_e_o_quinto_indice_e_a_bandeira_nao_muda_de_valor():
    """O cliente entrou DEPOIS do perfil: bandeira/categoria/perfil seguem em
    1/2/3; as metricas deslocaram para BASE_MET = 5. Pai = soma dos filhos:
    o total por bandeira e o mesmo de antes da D-72."""
    from src.load import cubos
    pac = cubos.construir(*_mini_modelo())
    assert cubos.BASE_MET == 5 and cubos.BASE_MET_SKU == 3
    assert all(len(l) == 8 for l in pac["cubo"])
    cli = pac["dims"]["cli"]
    assert all(l[4] < len(cli) for l in pac["cubo"])
    assert cli[0] == ["1", "CLI 1", 0]                  # [codigo, nome, n_rtm]
    assert {c[0] for c in cli} == {"1", "2", "3", "4", "5", "6"}
    por_ban = {}
    for l in pac["cubo"]:
        por_ban[pac["dims"]["ban"][l[1]]] = por_ban.get(pac["dims"]["ban"][l[1]], 0) + l[cubos.BASE_MET]
    assert por_ban == {"REDE A": 90000, "REDE B": 120000}   # 100+300+500 · 200+400+600
    # cada cliente e uma linha propria sob a bandeira dele
    por_cli = {}
    for l in pac["cubo"]:
        por_cli[cli[l[4]][0]] = por_cli.get(cli[l[4]][0], 0) + l[cubos.BASE_MET]
    assert por_cli == {"1": 10000, "2": 20000, "3": 30000, "4": 40000,
                       "5": 50000, "6": 60000}
    # o cubo de SKU nao mudou (D-64: 3 indices)
    assert all(len(l) == 6 for l in pac["cubo_sku"])


def test_d72_rtm_que_herdou_a_bandeira_vira_uma_linha_acumulada():
    """Regra do Douglas: cliente RTM nao aparece nominal na bandeira do
    distribuidor — os que HERDARAM a bandeira viram UMA chave por bandeira,
    com a contagem no rotulo; o distribuidor segue nominal na mesma
    bandeira. `cliente_rtm_acumulado: false` devolve cada RTM pelo nome."""
    from src.load import cubos
    pac = cubos.construir(*_modelo_rtm_acumulado())
    cli, ban = pac["dims"]["cli"], pac["dims"]["ban"]
    acum = [c for c in cli if c[2] > 0]
    assert acum == [["", "", 2]], "uma linha acumulada, somando 2 clientes RTM"
    assert len(cli) == 5                                 # 4 nominais + 1 acumulado
    por = {}
    for l in pac["cubo"]:
        k = (ban[l[1]], cli[l[4]][0] or "RTM")
        por[k] = por.get(k, 0) + l[cubos.BASE_MET]
    assert por[("DIST X", "1")] == 10000                # o distribuidor, nominal
    assert por[("DIST X", "RTM")] == 70000              # 300 + 400 acumulados
    assert ("DIST X", "3") not in por and ("DIST X", "4") not in por
    assert sum(v for (b, _), v in por.items() if b == "DIST X") == 80000
    # chave sintetica nunca colide com codigo real
    assert cubos.RTM_PREFIXO.startswith("")
    # rollback pelo config: cada RTM volta a ser nominal
    original = cubos._DASH
    cubos._DASH = {**original, "cliente_rtm_acumulado": False}
    try:
        pac2 = cubos.construir(*_modelo_rtm_acumulado())
    finally:
        cubos._DASH = original
    assert all(c[2] == 0 for c in pac2["dims"]["cli"]) and len(pac2["dims"]["cli"]) == 6


def test_d72_recorte_por_nivel_reindexa_clientes_e_mantem_a_contagem_rtm():
    """O arquivo de um colaborador leva SO os clientes do escopo (nem o nome
    dos outros viaja), reindexados; a contagem da linha RTM nao muda."""
    from src.load import cubos
    from run_dashboard import filtrar_por_nivel
    pac = cubos.construir(*_modelo_rtm_acumulado())
    h2 = filtrar_por_nivel(pac, 0, "20 - H2", "N1")
    assert [c[0] for c in h2["dims"]["cli"]] == ["5", "6"]
    assert all(l[4] < len(h2["dims"]["cli"]) for l in h2["cubo"])
    assert sum(l[cubos.BASE_MET] for l in h2["cubo"]) == 110000
    h1 = filtrar_por_nivel(pac, 0, "10 - H1", "N1")
    assert [c for c in h1["dims"]["cli"] if c[2] > 0] == [["", "", 2]]
    assert {c[0] for c in h1["dims"]["cli"] if c[2] == 0} == {"1", "2"}
    assert sum(l[cubos.BASE_MET] for l in h1["cubo"]) == 100000
    assert len(pac["dims"]["cli"]) == 5                  # o pacote global nao muda


def test_d72_saneamento_marca_a_bandeira_herdada():
    """BANDEIRA_HERDADA e a flag que o cubo le: True so no RTM cuja bandeira
    foi de fato trocada; False no distribuidor, com o parametro desligado e
    quando o distribuidor nao tem bandeira ("acumula so quando herdou")."""
    from src.transform import saneamento
    from src.utils.config import CFG
    lig = _com_flag_bandeira(True)[0].set_index("COD_CLIENTE")
    assert bool(lig.loc["900", "BANDEIRA_HERDADA"]) is True
    assert bool(lig.loc["800", "BANDEIRA_HERDADA"]) is False
    des = _com_flag_bandeira(False)[0].set_index("COD_CLIENTE")
    assert bool(des.loc["900", "BANDEIRA_HERDADA"]) is False
    dim, rtm, falt, fato = _dim_saneamento()
    dim = dim.copy()
    dim.loc[dim["COD_CLIENTE"] == "800", "BANDEIRA"] = CFG["dimensoes"]["rotulo_sem_bandeira"]
    original = saneamento._SAN
    saneamento._SAN = {**original, "rtm_herda_bandeira": True}
    try:
        d, _, _ = saneamento.aplicar(dim, rtm, falt, fato, mes_execucao="2026-09")
    finally:
        saneamento._SAN = original
    assert bool(d.set_index("COD_CLIENTE").loc["900", "BANDEIRA_HERDADA"]) is False


def test_d72_template_abre_bandeira_por_cliente():
    """Matriz Bandeira > Cliente > Categoria com chave tipada; nivel Cliente
    pulado na bandeira de um cliente so (BAN_MULTI); linha RTM acumulada por
    ultimo; metricas em BASE_MET = 5; rotulo de leitor vem do config (D-68)."""
    from src.utils.config import CFG
    corpo = _sem_comentarios(_ler_templates()["template_v4.html"])
    for termo in ('niveis:["Bandeira","Cliente","Categoria"]',
                  "const BASE_MET = 5", "function marcarBandeirasMulti",
                  'BAN_MULTI[l[1]] ? [l[1], "c"+l[4], "k"+l[2]] : [l[1], "k"+l[2]]',
                  "function rotCli", "rtm_acumulado", "acumFn:", "nivelDe:",
                  "const CLIDE = (l)=> l[4]"):
        assert termo in corpo, f"template v4 perdeu a D-72: {termo}"
    assert "col-4" not in corpo, "posicao de metrica solta voltou ao template"
    rot = (CFG["dashboard"].get("rotulos_exibicao") or {}).get("rtm_acumulado")
    assert rot and "{n}" in rot
    assert rot not in corpo, "o rotulo de leitor mora no config, nao no template"


# ===================================================== D-74: metas por cliente
def _metas_mini():
    """Meta para o _mini_modelo: cliente 1 (BALA), cliente 3 (GOMAS) e um par
    que NAO tem sell-in (cliente 2 em GOMAS), em jan/26; e fev/26 so para o
    cliente 5 — mes sem sell-in nenhum, com meta NEGATIVA (Q1-a)."""
    return pd.DataFrame({
        "ANO_MES": pd.Series(["2026-01", "2026-01", "2026-01", "2026-02"], dtype="string"),
        "COD_CLIENTE": pd.Series(["1", "3", "2", "5"], dtype="string"),
        "CATEGORIA": pd.Series(["BALA", "GOMAS", "GOMAS", "BALA"], dtype="string"),
        "META_RECEITA": [120.0, 330.0, 50.0, -10.0],
        "META_PESO_KG": [12.0, 33.0, 5.0, -1.0],
        "ARQUIVO_ORIGEM": pd.Series(["m.xlsx"] * 4, dtype="string"),
    })


def _planilha_metas(alvo, linhas, cols=None):
    cols = cols or ["CÓDIGO CLIENTE", "CATEGORIA", "Período", "Tipo Meta", "Valor"]
    df = pd.DataFrame(linhas, columns=cols)
    with pd.ExcelWriter(alvo, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="Metas FY27", index=False)
    return alvo


def _tmp_dir():
    import tempfile
    return Path(tempfile.mkdtemp(prefix="metas_teste_"))


def test_d74_leitor_aceita_serial_data_e_texto_no_periodo():
    """A competencia vem do CONTEUDO: serial do Excel (46266 = 01/09/2026),
    data e texto AAAA-MM viram o mesmo ANO_MES. Codigo zero-preenchido e
    float viram o mesmo cliente (digitos)."""
    from src.extract import metas
    arq = _planilha_metas(_tmp_dir() / "m.xlsx", [
        [1005619, "AMENDOIM", 46266, "VOLUME (KG)", 1.5],
        ["0001005619", "AMENDOIM", 46266, "VALOR (R$)", 30.0],
        [1005619.0, "GOMAS", pd.Timestamp("2026-10-01"), "VOLUME (KG)", 2.0],
        [1005619, "GOMAS", "2026-10", "VALOR (R$)", 40.0],
    ])
    d, extra = metas._ler_um(arq)
    assert list(d.columns) == metas.COLUNAS
    assert sorted(d["ANO_MES"]) == ["2026-09", "2026-10"]
    assert set(d["COD_CLIENTE"]) == {"1005619"}
    assert extra["meses"] == ["2026-09", "2026-10"]
    assert extra["gabarito"]["2026-09"] == {"META_RECEITA": 30.0, "META_PESO_KG": 1.5}
    assert extra["pares_com_um_tipo_so"] == 0


def test_d74_leitor_aborta_tipo_desconhecido_duplicidade_e_periodo_invalido():
    """Tipo de meta fora do config, chave repetida, periodo irreconhecivel e
    valor nulo ABORTAM — nada entra pela metade."""
    from src.extract import metas
    pasta = _tmp_dir()
    casos = {
        "tipo": [[1, "BALA", 46266, "VALOR (US$)", 1.0], [1, "BALA", 46266, "VOLUME (KG)", 1.0]],
        "dup": [[1, "BALA", 46266, "VALOR (R$)", 1.0], [1, "BALA", 46266, "VALOR (R$)", 2.0],
                [1, "BALA", 46266, "VOLUME (KG)", 1.0]],
        "periodo": [[1, "BALA", "setembro", "VALOR (R$)", 1.0], [1, "BALA", 46266, "VOLUME (KG)", 1.0]],
        "nulo": [[1, "BALA", 46266, "VALOR (R$)", None], [1, "BALA", 46266, "VOLUME (KG)", 1.0]],
    }
    for nome, linhas in casos.items():
        arq = _planilha_metas(pasta / f"{nome}.xlsx", linhas)
        try:
            metas._ler_um(arq)
        except SystemExit as e:
            assert e.code == 1
            continue
        raise AssertionError(f"caso {nome} deveria abortar")


def test_d74_categoria_fora_do_modelo_aborta():
    """Q5-a: categoria que nao existe na DIM_PRODUTO rejeita a base."""
    from src.extract import metas
    _, _, dim_prod, _ = _mini_modelo()
    fm = _metas_mini()
    metas.conferir_categorias(fm, dim_prod)          # BALA e GOMAS existem
    fm.loc[0, "CATEGORIA"] = "AMENDOIN"
    try:
        metas.conferir_categorias(fm, dim_prod)
    except SystemExit as e:
        assert e.code == 1
        return
    raise AssertionError("categoria fora do modelo deveria abortar")


def test_d74_cliente_so_com_meta_entra_na_dim_pela_hierarquia():
    """Q4-a: cliente com meta e sem sell-in entra na DIM_CLIENTE com a
    flag SEM_SELLIN, hierarquia pelo de-para e nome ausente (nada inventado)."""
    sellin = pd.DataFrame({
        "ANO_MES": ["2026-01"], "COD_CLIENTE": ["1"], "NOME_CLIENTE": ["CLI 1"],
        "BANDEIRA": ["REDE A"], "UF": ["SP"],
    })
    estrutura = pd.DataFrame({
        "COD_CLIENTE": ["1", "9"], "HEAD": ["10 - H1", "10 - H1"],
        "GERENTE": ["1000 - G1"] * 2, "SUPERVISOR": ["1100 - S1"] * 2,
        "VENDEDOR": ["111 - V1"] * 2, "PROJETO": ["P1"] * 2,
        "BANDEIRA_ESTRUTURA": ["REDE A", "REDE Z"],
    })
    d = dimensoes.dim_cliente(sellin, estrutura, None,
                              clientes_extra=pd.Series(["9", "1", "77"]))
    assert list(d["COD_CLIENTE"]) == ["1", "77", "9"]
    assert list(d["SEM_SELLIN"]) == [False, True, True]
    nove = d.set_index("COD_CLIENTE").loc["9"]
    assert nove["HEAD"] == "10 - H1" and nove["BANDEIRA"] == "REDE Z"
    assert pd.isna(nove["NOME_CLIENTE"])
    sete = d.set_index("COD_CLIENTE").loc["77"]
    assert sete["HEAD"] == dimensoes.SEM_ESTRUTURA and not sete["NA_ESTRUTURA"]


def test_d74_cubo_meta_tem_os_mesmos_indices_e_reconcilia_por_mes():
    """O cubo de meta usa os indices do principal (bandeira, categoria,
    perfil, cliente) e o mes; par so com meta ganha linha; mes so com meta
    entra no calendario; soma por mes bate com a FATO_META ao centavo."""
    from src.load import cubos
    fato, dim_cli, dim_prod, _ = _mini_modelo()
    fm = _metas_mini()
    dim_cal = calendario.construir(sorted(set(fato["ANO_MES"]) | set(fm["ANO_MES"])))
    assert list(dim_cal["ANO_MES"]) == ["2026-01", "2026-02"]
    pac = cubos.construir(fato, dim_cli, dim_prod, dim_cal, fato_meta=fm)
    cm = pac["cubo_meta"]
    assert len(cm) == 4 and all(len(l) == cubos.BASE_MET_META + 2 for l in cm)
    D = pac["dims"]
    # cliente 2 em GOMAS so existe na meta; a linha aponta para os indices certos
    linha = [l for l in cm if D["cli"][l[4]][0] == "2"][0]
    assert D["cat"][linha[2]] == "GOMAS" and D["ban"][linha[1]] == "REDE B"
    assert D["perfil"][linha[3]][0] == "10 - H1"
    assert linha[5] == 5000 and linha[6] == 5000      # R$ 50 em centavos, 5 kg em g
    # fev/26 (indice 1) so tem meta: nenhuma linha do principal, uma da meta
    assert not [l for l in pac["cubo"] if l[0] == 1]
    assert [l for l in cm if l[0] == 1][0][5] == -1000  # negativa entra como esta
    cubos.reconciliar_meta(pac, fm)
    # meta que some do cubo derruba a reconciliacao
    pac["cubo_meta"] = cm[:-1]
    try:
        cubos.reconciliar_meta(pac, fm)
    except SystemExit as e:
        assert e.code == 1
        return
    raise AssertionError("cubo de meta incompleto deveria abortar")


def test_d74_rtm_acumula_a_meta_na_linha_do_distribuidor():
    """Cliente RTM que herdou a bandeira: a meta dele soma na MESMA chave Σ
    do realizado, nunca em linha propria."""
    from src.load import cubos
    fato, dim, dim_prod, dim_cal = _modelo_rtm_acumulado()
    fm = _metas_mini().iloc[:2].copy()           # clientes 1 (dist.) e 3 (RTM)
    fm["CATEGORIA"] = pd.Series(["BALA", "BALA"], dtype="string")
    pac = cubos.construir(fato, dim, dim_prod, dim_cal, fato_meta=fm)
    D = pac["dims"]
    linhas = [l for l in pac["cubo_meta"] if D["ban"][l[1]] == "DIST X"]
    tipos = sorted((D["cli"][l[4]][0], D["cli"][l[4]][2], l[5]) for l in linhas)
    assert tipos == [("", 2, 33000), ("1", 0, 12000)]     # Σ RTM (n=2) e o distribuidor


def test_d74_recorte_por_nivel_leva_a_meta_e_reindexa():
    """filtrar_por_nivel recorta o cubo de meta pelo mesmo perfil e as listas
    de categoria/bandeira/cliente sao a UNIAO com a meta do arquivo."""
    from src.load import cubos
    from run_dashboard import filtrar_por_nivel
    fato, dim_cli, dim_prod, _ = _mini_modelo()
    fm = _metas_mini()
    dim_cal = calendario.construir(["2026-01", "2026-02"])
    pac = cubos.construir(fato, dim_cli, dim_prod, dim_cal, fato_meta=fm)
    h2 = filtrar_por_nivel(pac, 0, "20 - H2")
    # H2 so fatura BALA (SKU 30), e o cliente 5 tem meta em fev/26 em BALA
    assert h2["dims"]["cat"] == ["BALA"]
    assert [l[5] for l in h2["cubo_meta"]] == [-1000]
    assert all(l[3] < len(h2["dims"]["perfil"]) and l[4] < len(h2["dims"]["cli"])
               for l in h2["cubo_meta"])
    h1 = filtrar_por_nivel(pac, 0, "10 - H1")
    assert sum(l[5] for l in h1["cubo_meta"]) == 50000       # 120 + 330 + 50
    assert sum(l[5] for l in h1["cubo_meta"]) + sum(l[5] for l in h2["cubo_meta"]) \
        == sum(l[5] for l in pac["cubo_meta"])


def test_d74_revisoes_registram_mes_alterado_e_removido():
    """Q3: mes ja carregado que muda ou some fica registrado (append) e
    vira aviso; mes novo e igual nao viram aviso."""
    from src.extract import metas
    ant = _metas_mini()
    nov = ant.copy()
    nov.loc[0, "META_RECEITA"] = 121.0              # jan/26 alterado
    nov = nov[nov["ANO_MES"] != "2026-02"]          # fev/26 removido
    nov = pd.concat([nov, pd.DataFrame({
        "ANO_MES": pd.Series(["2026-03"], dtype="string"),
        "COD_CLIENTE": pd.Series(["1"], dtype="string"),
        "CATEGORIA": pd.Series(["BALA"], dtype="string"),
        "META_RECEITA": [1.0], "META_PESO_KG": [1.0],
        "ARQUIVO_ORIGEM": pd.Series(["m.xlsx"], dtype="string")})], ignore_index=True)
    alvo = _tmp_dir() / "metas_revisoes.csv"
    linhas, avisos = metas.registrar_revisoes(nov, ant, alvo, "exec1")
    sit = {l["ANO_MES"]: l["situacao"] for l in linhas}
    assert sit == {"2026-01": "alterado", "2026-02": "removido", "2026-03": "novo"}
    assert [l["pares_alterados"] for l in linhas if l["ANO_MES"] == "2026-01"] == [1]
    assert len(avisos) == 2                          # alterado e removido; novo nao
    assert alvo.exists()
    # segunda execucao sem mudanca: nada registrado, arquivo intacto
    tam = alvo.stat().st_size
    assert metas.registrar_revisoes(nov, nov, alvo, "exec2") == ([], [])
    assert alvo.stat().st_size == tam


def test_d74_template_mostra_meta_so_quando_o_periodo_tem():
    """Guarda no template: cubo de meta indexado por mes, colunas META/ATING
    condicionadas ao periodo, atingimento sobre os meses com meta, caixas
    sem meta, mes so com meta visivel nos chips, medicao no console."""
    corpo = _sem_comentarios(_ler_templates()["template_v4.html"])
    for termo in ("const BASE_META = 5", "function somarMeta", "function metMeta",
                  "const MOSTRA_META = p => TEM_META && p.meta && p.meta.length>0 && METRICAS[F.metrica].col<=1",
                  "function ating(real, meta)", "mapAM = mostraMeta ? soma(p.meta)",
                  "pathMeta:l=>[l[2]]", "OPC.mesMeta.has(i)", "metaParcial",
                  "performance.now()", 'class="cmp meta"', "DB.cubo_meta",
                  # segunda onda: barra Meta na Evolucao, so com meta no periodo
                  'const dsMeta = mostraMeta ? [', 'label:"Meta",data:metaSerie',
                  'const ehMeta=ds.label==="Meta"', "atingSerie[c.dataIndex]"):
        assert termo in corpo, f"template v4 perdeu a D-74: {termo}"
    # D-76: um eixo so; a linha de Δ% saiu e virou rotulo/tooltip da barra
    # Atual; cores da opcao A (validadas pelo kit de dataviz). D-80/V-11
    # (15/09/2026): o trio foi re-derivado da paleta do template DN
    # preservando a estrutura da D-76 (LY = tint do Atual, Meta ambar):
    # Atual #1E4FA1, LY #7895C7, Meta #B5720C. Os hex antigos (#5e94c9,
    # #00539f, #c97b12) NAO podem voltar.
    assert 'yAxisID:"y1"' not in corpo and 'label:"Δ% vs LY"' not in corpo, \
        "a linha de Δ% (e o segundo eixo) voltou ao grafico (D-76)"
    for termo in ('backgroundColor:"#7895C7"', 'backgroundColor:"#1E4FA1"',
                  'backgroundColor:"#B5720C"', "const d=variacao[c.dataIndex];"):
        assert termo in corpo, f"template v4 perdeu a D-76/V-11: {termo}"
    for antigo in ("#5e94c9", "#00539f", "#c97b12"):
        assert antigo not in corpo, f"cor pre-D-80 voltou ao template v4: {antigo}"
    # D-77: o percentual diz o que e ("Δ LY", "ating.") enquanto cabe na
    # barra (measureText); senao marcador (▲▼, ◎) + explicacao no titulo
    for termo in ("const cabe=txt=>g.measureText(txt).width<=slot-4;",
                  '"Δ LY "+fmtVar(', '"ating. "', "c.abrevRotulos=curto;",
                  "▲▼ Δ% vs ano anterior · ◎ % da meta"):
        assert termo in corpo, f"template v4 perdeu a D-77: {termo}"


def test_d81_template_barra_lateral_chips_abas():
    """Guarda no template (D-81, 15/09/2026 a noite, decisao do Douglas por
    opcao tabulada): barra lateral FIXA no padrao do DN (250px, recolhivel
    para 46px, comeca aberta, estado lembrado fora do recorte), chips com
    raio de 8px, abas fixas no topo com a altura medida e navegacao por
    setas com tabindex itinerante. A gaveta sobreposta (fundo escuro, x, Esc)
    nao pode voltar."""
    corpo = _sem_comentarios(_ler_templates()["template_v4.html"])
    for termo in ('<aside class="fgav" id="fGaveta" aria-label="Filtros de dimensão">',
                  ".top,.wrap{margin-left:250px", "body.lat-off .fgav{width:46px",
                  "body.lat-off .fgav-n.tem{display:block}",
                  'const CHAVE_LATERAL = "dashDoriCanais.lateral.v1";',
                  "function lateral(aberta)", "function lateralSalva()",
                  "lateral(lateralSalva());",
                  'localStorage.getItem("dashDoriCanais.lateral.v1")==="off"',
                  'el("fAtivos").classList.toggle("tem", d.length>0);',
                  ".chip{border:1px solid #BBCAE3;background:#F4F6FA;border-radius:8px;",
                  ".tabs{display:flex;gap:6px;flex-wrap:wrap;position:sticky;top:0;",
                  "top:var(--abas-h,45px)", "function medirAbas()",
                  'if(ev.key==="ArrowRight") j=(i+1)%abas.length;',
                  'else if(ev.key==="Home") j=0;',
                  "t.tabIndex = on ? 0 : -1;", "x.tabIndex=-1;"):
        assert termo in corpo, f"template v4 perdeu a D-81: {termo}"
    for antigo in ("abrirGaveda", "abrirGaveta", "fBack", "fFechar", "atualizarToggle",
                   '.fbtn', 'id="fGaveta" hidden', ".chip{border:1px solid #BBCAE3;background:#F4F6FA;border-radius:20px"):
        assert antigo not in corpo, f"a gaveta sobreposta / chip em pilula voltou (D-81): {antigo}"


def test_d82_filtros_bandeira_e_cliente_na_barra_lateral():
    """D-82 (22/09/2026, opcao A do Douglas): Bandeira e Cliente sao filtros
    globais de escolha unica na barra lateral, aplicados SO no cubo principal
    e no de meta (indices 1 e 4). O cubo de SKU nao tem os eixos (D-64):
    `passaSku` nao pode aplica-los e a aba Categorias avisa. Ate LISTA_MAX
    opcoes a linha e lista suspensa (D-69); acima, busca com sugestoes."""
    corpo = _sem_comentarios(_ler_templates()["template_v4.html"])
    for termo in ('ban:new Set(), cli:new Set(),',
                  'F.ban.has(l[1])', 'F.cli.has(l[4])',
                  'if(passaPrincipal(l, "ban+cli")) ban.add(l[1]);',
                  'if(passaPrincipal(l, "cli"))   cli.add(l[4]);',
                  'OPC = {can, cat, head, ger, sup, vend, ban, cli, mes, mesMeta, ano, fy};',
                  'const LISTA_MAX = 50, SUG_MAX = 30;',
                  'function filtroBuscavel(base, idLinha, itens, comDado, sel, rot)',
                  'filtroBuscavel("fBan", "frowBan", ORD_BAN, OPC.ban, F.ban, i=>D.ban[i]);',
                  'filtroBuscavel("fCli", "frowCli", ORD_CLI, OPC.cli, F.cli, rotCli);',
                  '<select class="lista" id="fBanSel">', '<select class="lista" id="fCliSel">',
                  '<input class="busca" id="fBan"', '<input class="busca" id="fCli"',
                  '<div class="aviso" id="avisoCatg" hidden>',
                  'el("avisoCatg").hidden = !semSku;',
                  'ban:[...F.ban].map(i=>D.ban[i]),', 'cli:[...F.cli].map(i=>D.cli[i][0]),',
                  'setDe(F.ban, r.ban, x=>idx(D.ban,x));',
                  'ligarLista("fBanSel","ban",v=>+v); ligarLista("fCliSel","cli",v=>+v);',
                  'ligarSugestoes("fBan","ban",()=>ORD_BAN,i=>D.ban[i]);',
                  'ligarSugestoes("fCli","cli",()=>ORD_CLI,rotCli);'):
        assert termo in corpo, f"template v4 perdeu a D-82: {termo}"
    # o cubo de SKU continua sem os dois filtros (D-64): passaSku so tem perfil e categoria
    ini = corpo.index("function passaSku(l, ignorar){")
    fim = corpo.index("}", corpo.index("return true;", ini))
    trecho = corpo[ini:fim]
    assert "F.ban" not in trecho and "F.cli" not in trecho, "passaSku nao pode filtrar bandeira/cliente (D-64/D-82)"
    assert "F.cat.has(D.sku[l[1]][2])" in trecho


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
