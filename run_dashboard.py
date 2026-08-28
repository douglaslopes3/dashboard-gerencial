# -*- coding: utf-8 -*-
"""Dashboard Gerencial de Canais — geração do painel.

    python run_dashboard.py             gera o HTML
    python run_dashboard.py --abrir     gera e abre no navegador

Este passo NÃO gera interface. Nenhuma linha de HTML, CSS ou JS nasce em Python:
a interface inteira vive em `dashboard/template.html` e é editada lá, à mão.
Aqui acontecem exatamente duas substituições de texto:

    <!--LIB:chart-->                  ->  o bundle do Chart.js, embutido
    /*DADOS_INICIO*/…/*DADOS_FIM*/    ->  o JSON dos cubos

É isso que cumpre "HTML praticamente estático, só os dados mudam": no ciclo
mensal o template não é tocado.
"""
from __future__ import annotations

import json
import re
import sys
import time
import webbrowser
from datetime import datetime
from pathlib import Path

for _fluxo in (sys.stdout, sys.stderr):
    try:
        _fluxo.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

from src.utils import log as L
from src.utils.config import (CFG, PASTA_CURATED, caminho, nome_uf,
                              preparar_pastas)
from src.utils.log import abortar, log, titulo

_DASH = CFG["dashboard"]
RE_LIB = re.compile(r"<!--LIB:([a-zA-Z0-9_-]+)-->")


def embutir_libs(html: str) -> str:
    libs = _DASH.get("libs") or {}
    faltando: list[str] = []

    def troca(m: re.Match) -> str:
        nome = m.group(1)
        if nome not in libs:
            faltando.append(nome)
            return m.group(0)
        alvo = caminho(libs[nome])
        if not alvo.exists():
            faltando.append(f"{nome} ({alvo})")
            return m.group(0)
        js = alvo.read_text(encoding="utf-8")
        log(f"lib {nome:<10} {len(js) / 1024:>8,.0f} KB embutida")
        # Fecha qualquer </script> que apareca dentro do bundle: o parser do
        # navegador encerra o bloco no primeiro que encontrar, mesmo em string.
        js = js.replace("</script>", "<\\/script>")
        return "<script>" + js + "</script>"

    saida = RE_LIB.sub(troca, html)
    if faltando:
        abortar(f"biblioteca(s) nao encontrada(s): {faltando}\n"
                "  (config/config.yaml -> dashboard.libs)")
    return saida


def main() -> int:
    t0 = time.time()
    preparar_pastas()
    L.abrir()
    titulo(f"{CFG['projeto']['nome']}  ·  geracao do painel")

    fonte = PASTA_CURATED / "cubos.json"
    if not fonte.exists():
        abortar(f"{fonte} nao existe.\n"
                "  Rode `python run_pipeline.py` primeiro.")
    pacote = json.loads(fonte.read_text(encoding="utf-8"))

    # Contexto que o painel exibe ao leitor. Nada disto e digitado a mao: sai do
    # resumo que o pipeline gravou.
    resumo_arq = PASTA_CURATED / "resumo.json"
    if not resumo_arq.exists():
        abortar(f"{resumo_arq} nao existe. Rode `python run_pipeline.py` primeiro.")
    R = json.loads(resumo_arq.read_text(encoding="utf-8"))

    # A6: cubos.json e resumo.json tem de vir da MESMA execucao. Divergencia
    # significa gravacao interrompida no meio — o painel sairia com cara de
    # valido misturando dados de execucoes diferentes.
    if pacote.get("execucao") != R.get("execucao"):
        abortar("cubos.json e resumo.json vem de execucoes DIFERENTES "
                f"({pacote.get('execucao') or '?'} x {R.get('execucao') or '?'}).\n"
                "  A gravacao anterior deve ter sido interrompida no meio.\n"
                "  Rode `python run_pipeline.py` de novo antes de gerar o painel.")

    meses = [c[0] for c in pacote["cal"]]

    def br(v: float, casas: int = 2) -> str:
        return f"{v:,.{casas}f}".replace(",", "@").replace(".", ",").replace("@", ".")

    c = pacote["corte_bandeira"]
    rodape = (
        f"<b>{R['arquivos']}</b> arquivos de Sell In · "
        f"<b>{br(R['linhas'], 0)}</b> linhas · período <b>{meses[0]} a {meses[-1]}</b> "
        f"({len(meses)} meses) · receita líquida <b>R$ {br(R['receita'])}</b> · "
        f"<b>{br(R['peso_t'])} t</b> · <b>{br(R['caixas'], 0)}</b> caixas<br>"
        f"Processado em {R['gerado_em']} · execução <code>{R['execucao']}</code><br>"
        "<b>Ressalvas medidas, declaradas de propósito:</b> "
        "(1) <b>Caixas é métrica bruta</b> — Valor e Volume são líquidos de devolução, "
        f"Caixas não; {br(R['caixas_sem_info'], 0)} linhas não têm caixa informada na origem. "
        f"(2) <b>Canal</b> vem de <code>bases/Canais/Canais.xlsx</code>, com "
        f"<b>{br(R.get('cobertura_canal', 0) * 100, 2)}%</b> da receita classificada; "
        "clientes sem canal sairiam em <code>data/quality/clientes_sem_canal.csv</code>. "
        f"(3) Ranking de bandeiras nominal nas {c['top']} maiores "
        f"({br(c['cobertura'] * 100, 1)}% do faturamento); as demais entram agregadas, "
        "o total continua fechando. "
        "(4) A camada de SKU cruza com head, canal, categoria e UF — não com gerente, "
        "bandeira nem projeto; a tela avisa quando esses filtros ficam ativos juntos.<br>"
        "Gaps, donos e tamanhos em <code>docs/04_GAPS_E_RISCOS.md</code> · "
        "qualidade desta carga em <code>data/quality/relatorio_qualidade.md</code>"
    )

    pacote["meta"] = {
        "periodo": f"{meses[0]} a {meses[-1]}",
        "meses": len(meses),
        "linhas": R["linhas"],
        "arquivos": R["arquivos"],
        "gerado_em": R["gerado_em"],
        "execucao": R["execucao"],
        "rodape": rodape,
    }
    pacote["tops"] = {"ban": _DASH["tops_bandeira"], "sku": _DASH["tops_sku"]}
    pacote["top_ranking"] = int(_DASH["top_ranking"])
    pacote["nome_uf"] = nome_uf()

    template = caminho(_DASH["template"])
    if not template.exists():
        abortar(f"template nao encontrado: {template}")
    html = template.read_text(encoding="utf-8")

    ini, fim = _DASH["marcador_inicio"], _DASH["marcador_fim"]
    # Cada marcador tem de aparecer EXATAMENTE uma vez. Duas ocorrencias fazem a
    # troca acontecer na primeira — que pode ser um comentario de documentacao —
    # e o painel sai com o `null` do template no lugar dos dados, sem erro nenhum.
    for marca in (ini, fim):
        n = html.count(marca)
        if n != 1:
            abortar(f"o marcador {marca} aparece {n} vez(es) em {template.name}; "
                    "tem de aparecer exatamente 1. Nao escreva o marcador dentro "
                    "de comentarios do template.")
    n_lib = len(RE_LIB.findall(html))
    if n_lib != 1:
        abortar(f"o marcador de biblioteca aparece {n_lib} vez(es) em "
                f"{template.name}; tem de aparecer exatamente 1.")

    dados = json.dumps(pacote, ensure_ascii=False, separators=(",", ":"))
    # C1 (auditoria): descricao de SKU vem de Excel de terceiros. Um "</script>"
    # futuro dentro de um valor encerraria o bloco no parse e quebraria o painel
    # inteiro. "<\/" e escape JSON valido — o valor lido nao muda.
    dados = dados.replace("</script>", "<\\/script>")
    antes, resto = html.split(ini, 1)
    _, depois = resto.split(fim, 1)
    html = antes + ini + dados + fim + depois
    html = embutir_libs(html)

    saida_dir = caminho(_DASH["pasta_saida"])
    saida_dir.mkdir(parents=True, exist_ok=True)
    alvo = saida_dir / _DASH["arquivo_saida"]
    alvo.write_text(html, encoding="utf-8")

    tam = alvo.stat().st_size / 1024 / 1024
    log("")
    log(f"dados embutidos ........ {len(dados) / 1024 / 1024:,.2f} MB")
    log(f"painel ................. {alvo} ({tam:,.2f} MB)", "ok")
    log(f"tempo total ............ {time.time() - t0:.1f}s")
    log("")
    log("Abra por duplo clique. Nao precisa de servidor nem de internet.", "ok")

    if "--abrir" in sys.argv:
        webbrowser.open(alvo.resolve().as_uri())
    L.fechar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
