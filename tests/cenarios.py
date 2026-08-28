# -*- coding: utf-8 -*-
"""Cenários de ponta a ponta — rodam o pipeline de verdade.

    python tests/cenarios.py

Cada cenário monta um arquivo de entrada, executa `run_pipeline.py` como
subprocesso e confere o **exit code** e a **mensagem**. É a única forma de provar
que o pipeline aborta quando tem de abortar.

IMPORTANTE: os arquivos de teste são apagados no fim, sempre — inclusive se um
cenário falhar. Nada sintético sobrevive à execução, e o script termina rodando
o pipeline limpo para deixar os Parquets consistentes com as bases reais.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "data" / "raw" / "sell_in"
MARCA = "_TESTE_"

sys.path.insert(0, str(RAIZ))
import pandas as pd                                              # noqa: E402

COLS = ["Ano", "Ano mês", "Cód. cliente", "Cliente", "Bandeira cliente",
        "Estado", "Desc. categoria", "Cód. material",
        "Desc. material sem código", "Receita Líquida", "Peso Líquido",
        "Qtde Faturado", "Comissão Faturada Líquida"]


def _planilha(alvo: Path, linhas, com_total=True, com_filtro=True,
              cols=None) -> Path:
    cols = cols or COLS
    df = pd.DataFrame(linhas, columns=cols)
    if com_total:
        tot = {c: None for c in cols}
        tot["Ano"] = "Total"
        for c in ("Receita Líquida", "Peso Líquido", "Qtde Faturado",
                  "Comissão Faturada Líquida"):
            if c in cols:
                tot[c] = df[c].sum()
        df = pd.concat([df, pd.DataFrame([tot])], ignore_index=True)
    if com_filtro:
        fl = {c: None for c in cols}
        fl["Ano"] = "Filtros aplicados:"
        f2 = {c: None for c in cols}
        f2["Ano"] = ("Tipo mercado não é B2B, (Em branco), NAO INFORMADO, "
                     "DIVERSOS, OUTRAS VENDAS ou EXTERNO | Ano mês é 2026/09")
        df = pd.concat([df, pd.DataFrame([fl, f2])], ignore_index=True)
    alvo.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(alvo, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="Export", index=False)
    return alvo


def _linha(mes="2026/09", cli=1000021, prod=9012876, rec=1000.0, peso=100.0,
           cx=10.0):
    return [int(mes[:4]), mes, cli, "FEIRA DOS CARAMELOS LTDA", "LAREDO", "PA",
            "AMENDOIM", prod, "AMENDOIM JAPONES DORI 24X400G", rec, peso, cx, 50.0]


def rodar() -> tuple[int, str]:
    r = subprocess.run([sys.executable, "run_pipeline.py"], cwd=RAIZ,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def limpar() -> None:
    for a in ENTRADA.glob(f"*{MARCA}*"):
        a.unlink()
    # o cache guardado para o arquivo de teste tambem sai
    for a in (RAIZ / "data" / "staging").glob(f"*{MARCA}*"):
        a.unlink()


RESULTADOS: list[dict] = []


def cenario(cod, nome, esperado, prepara, valida):
    limpar()
    prepara()
    code, saida = rodar()
    ok, detalhe = valida(code, saida)
    RESULTADOS.append({"cod": cod, "nome": nome, "esperado": esperado,
                       "exit": code, "ok": ok, "detalhe": detalhe})
    print(f"{'  ok  ' if ok else ' FALHA'} {cod} · {nome}")
    print(f"         esperado: {esperado}")
    print(f"         obtido  : exit {code} · {detalhe}")
    limpar()


def main() -> int:
    print("=" * 78)
    print("CENARIOS DE PONTA A PONTA")
    print("=" * 78)

    # ---------------------------------------------------------------- T-05
    def prep_novo():
        _planilha(ENTRADA / f"sellin{MARCA}2026-09.xlsx",
                  [_linha(rec=1000.0, peso=100.0, cx=10.0)])

    def val_novo(code, s):
        achou = "2026-09" in s and code == 0
        rec = "2,260,854,914.86" in s.replace("−", "-")
        return achou and rec, ("mes 2026-09 entrou e a receita subiu exatamente "
                               "os R$ 1.000,00 do arquivo novo" if achou and rec
                               else "arquivo novo NAO foi absorvido corretamente")

    cenario("T-05", "nova base de Sell In largada em data/raw/sell_in/",
            "exit 0, mes novo aparece, total sobe exatamente o valor do arquivo",
            prep_novo, val_novo)

    # ---------------------------------------------------------------- T-07
    def prep_dup():
        # mesmo mes/cliente/SKU duas vezes, em arquivos diferentes
        _planilha(ENTRADA / f"sellin{MARCA}dup_a.xlsx", [_linha()])
        _planilha(ENTRADA / f"sellin{MARCA}dup_b.xlsx", [_linha()])

    def val_dup(code, s):
        # Auditoria A3: a duplicata agora e pega ANTES do grao — duas partes do
        # mesmo mes com o MESMO recorte de extracao sao copia duplicada (caso
        # real: copia de conflito do OneDrive) e abortam ja na ingestao, com
        # diagnostico melhor. O grao continua como segunda linha de defesa
        # (arquivos sem rodape de filtro cairiam nele).
        pegou = ("MESMO recorte de extracao" in s) or ("fora do grao declarado" in s)
        onde = ("na ingestao (A3: mesmo recorte = copia duplicada)"
                if "MESMO recorte" in s else "no grao")
        return (code == 1 and pegou,
                f"abortou {onde}, apontando os dois arquivos"
                if code == 1 else "NAO abortou")

    cenario("T-07", "duplicidade: mesmo mes/cliente/SKU em dois arquivos",
            "exit 1 — copia duplicada barrada na ingestao (A3) ou no grao",
            prep_dup, val_dup)

    # ---------------------------------------------------------------- T-08
    def prep_invalido():
        alvo = ENTRADA / f"sellin{MARCA}invalido.xlsx"
        with pd.ExcelWriter(alvo, engine="openpyxl") as w:
            pd.DataFrame({"qualquer": [1, 2]}).to_excel(
                w, sheet_name="OutraAba", index=False)

    def val_invalido(code, s):
        return (code == 1 and "REJEITADO" in s,
                "arquivo rejeitado antes de entrar" if code == 1
                else "NAO rejeitou")

    cenario("T-08", "arquivo incompativel (aba errada) na pasta de entrada",
            "exit 1, arquivo REJEITADO, nenhuma ingestao parcial",
            prep_invalido, val_invalido)

    # ---------------------------------------------------------------- T-09
    def prep_sem_coluna():
        cols = [c for c in COLS if c != "Qtde Faturado"]
        linha = [v for c, v in zip(COLS, _linha()) if c != "Qtde Faturado"]
        _planilha(ENTRADA / f"sellin{MARCA}sem_coluna.xlsx", [linha], cols=cols)

    def val_sem_coluna(code, s):
        return (code == 1 and "Qtde Faturado" in s and "REJEITADO" in s,
                "acusou a coluna obrigatoria ausente pelo nome" if code == 1
                else "NAO rejeitou")

    cenario("T-09", "arquivo sem uma coluna obrigatoria (Qtde Faturado)",
            "exit 1, mensagem nomeando a coluna que falta",
            prep_sem_coluna, val_sem_coluna)

    # ---------------------------------------------------------------- T-10
    def prep_gabarito():
        alvo = ENTRADA / f"sellin{MARCA}gabarito.xlsx"
        _planilha(alvo, [_linha(rec=1000.0)], com_total=True)
        # adultera a linha Total para simular perda de linha na leitura
        df = pd.read_excel(alvo, sheet_name="Export")
        df.loc[df["Ano"].astype(str) == "Total", "Receita Líquida"] = 9999.0
        with pd.ExcelWriter(alvo, engine="openpyxl") as w:
            df.to_excel(w, sheet_name="Export", index=False)

    def val_gabarito(code, s):
        return (code == 1 and "NAO bate com a linha 'Total'" in s,
                "abortou na reconciliacao contra a origem" if code == 1
                else "NAO abortou")

    cenario("T-10", "soma nao bate com a linha Total do proprio arquivo",
            "exit 1, reconciliacao contra a origem falha",
            prep_gabarito, val_gabarito)

    # ------------------------------------------------------- reprocessamento
    print()
    print("T-06 · reprocessamento (idempotencia)")
    c1, _ = rodar()
    h1 = _impressao()
    c2, _ = rodar()
    h2 = _impressao()
    ok = c1 == 0 and c2 == 0 and h1 == h2
    RESULTADOS.append({"cod": "T-06", "nome": "reprocessamento completo (idempotencia)",
                       "esperado": "duas execucoes seguidas produzem o mesmo modelo",
                       "exit": c2, "ok": ok,
                       "detalhe": f"{len(h1)} tabelas conferidas; identicas: {h1 == h2}"})
    print(f"{'  ok  ' if ok else ' FALHA'} T-06 · {len(h1)} tabelas, identicas: {h1 == h2}")

    print()
    print("=" * 78)
    n_ok = sum(1 for r in RESULTADOS if r["ok"])
    print(f"{n_ok} de {len(RESULTADOS)} cenarios passaram.")
    print("=" * 78)
    return 0 if n_ok == len(RESULTADOS) else 1


def _impressao() -> dict:
    """Assinatura do modelo: linhas e somas por tabela, sem as colunas de
    linhagem (que carregam o id da execucao e mudam de propósito)."""
    from src.load import parquet
    out = {}
    for nome in ("DIM_CALENDARIO", "DIM_CLIENTE", "DIM_PRODUTO"):
        d = parquet.carregar(nome)
        out[nome] = (len(d), len(d.columns))
    f = parquet.carregar("FATO_SELLIN")
    out["FATO_SELLIN"] = (len(f), round(float(f["RECEITA"].sum()), 2),
                          round(float(f["PESO_KG"].sum()), 3),
                          round(float(f["CAIXAS"].sum()), 2))
    return out


if __name__ == "__main__":
    try:
        codigo = main()
    finally:
        limpar()
        print("\nlimpando e reprocessando com as bases reais...")
        c, _ = rodar()
        print(f"pipeline final: exit {c}")
    sys.exit(codigo)
