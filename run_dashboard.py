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

import base64
import gzip
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


def _slug(s: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFD", str(s))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn").lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t[:60]


def filtrar_por_head(pacote: dict, head: str) -> dict:
    """Recorte FISICO por head: o pacote devolvido so contem as linhas de cubo
    cujo perfil (cubo principal) ou par head/canal (cubo de SKU) pertencem ao
    head pedido. E o filtro no nivel de DADOS: o que nao esta no arquivo nao
    existe para quem o abre, nao ha parametro de interface que traga de volta.
    O indice de perfil e remapeado porque a lista encolhe."""
    # D-48: os DOIS cubos passaram a viajar pelo mesmo indice de perfil — o
    # par `hc` deixou de existir, e o recorte por head virou um mapeamento so.
    dims = pacote["dims"]
    manter_perf = [i for i, p in enumerate(dims["perfil"]) if p[0] == head]
    mapa_perf = {i: j for j, i in enumerate(manter_perf)}

    cubo = [[l[0], l[1], l[2], mapa_perf[l[3]], l[4], l[5], l[6], l[7]]
            for l in pacote["cubo"] if l[3] in mapa_perf]
    cubo_sku = [[l[0], l[1], mapa_perf[l[2]], l[3], l[4], l[5], l[6], l[7]]
                for l in pacote["cubo_sku"] if l[2] in mapa_perf]

    novo = dict(pacote)
    novo["dims"] = {**dims,
                    "head": [head],
                    "perfil": [dims["perfil"][i] for i in manter_perf]}
    novo["cubo"] = cubo
    novo["cubo_sku"] = cubo_sku
    return novo


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

    # L3-G (01/09/2026, Q3-b): o rodape textual saiu de TODOS os arquivos do
    # painel — os Heads nao precisam dessa informacao. As mesmas medidas
    # continuam em resumo.json e em data/quality/relatorio_qualidade.md; as
    # ressalvas (caixas bruta, corte de bandeiras, camada de SKU) seguem
    # declaradas nas proprias telas que elas afetam.
    pacote["meta"] = {
        "periodo": f"{meses[0]} a {meses[-1]}",
        "meses": len(meses),
        "linhas": R["linhas"],
        "arquivos": R["arquivos"],
        "gerado_em": R["gerado_em"],
        "execucao": R["execucao"],
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

    # A lib entra UMA vez na base; os marcadores de dados sobrevivem (o bundle
    # do Chart.js nao os contem — os checks acima ja rodaram sobre o template).
    base = embutir_libs(html)
    antes, resto = base.split(ini, 1)
    _, depois = resto.split(fim, 1)

    saida_dir = caminho(_DASH["pasta_saida"])
    saida_dir.mkdir(parents=True, exist_ok=True)

    # D-48 (02/09/2026): os cubos vao COMPACTADOS para dentro do HTML.
    # Medido: com o eixo novo do cubo de SKU (que acabou com os quatro filtros
    # ignorados) o JSON cru levaria o painel a 25,8 MB — acima do teto de
    # 25 MB — e ele cresce ~4% a cada mes novo de sell-in. Em gzip+base64 sao
    # ~9,6 MB, MENOS que os 14,66 MB do painel anterior. O template descompacta
    # na abertura (DecompressionStream, nativo do navegador, sem rede).
    # `dashboard.compactar: false` no config desliga, para diagnostico.
    compactar = bool(_DASH.get("compactar", True))

    def escrever(pac: dict, nome_arquivo: str) -> Path:
        dados = json.dumps(pac, ensure_ascii=False, separators=(",", ":"))
        cru_mb = len(dados.encode("utf-8")) / 1024 / 1024
        if compactar:
            bruto = gzip.compress(dados.encode("utf-8"), 6)
            carga = json.dumps({"z": "gzip+base64",
                                "b64": base64.b64encode(bruto).decode("ascii")},
                               separators=(",", ":"))
        else:
            carga = dados
        # C1 (auditoria): descricao de SKU vem de Excel de terceiros. Um
        # "</script>" dentro de um valor encerraria o bloco no parse e
        # quebraria o painel inteiro. "<\/" e escape JSON valido. (Base64 nao
        # produz essa sequencia, mas o escape fica: ele protege o caminho
        # `compactar: false` e nao custa nada no outro.)
        carga = carga.replace("</script>", "<\\/script>")
        alvo = saida_dir / nome_arquivo
        alvo.write_text(antes + ini + carga + fim + depois, encoding="utf-8")
        tam = alvo.stat().st_size / 1024 / 1024
        extra = (f" · cubos {cru_mb:,.1f} MB -> "
                 f"{len(carga) / 1024 / 1024:,.1f} MB compactados"
                 if compactar else " · SEM compactacao")
        log(f"painel ................. {alvo.name} ({tam:,.2f} MB){extra}", "ok")
        return alvo

    log("")
    alvo = escrever(pacote, _DASH["arquivo_saida"])

    # ---------------------------------------------- arquivos por head (bloco C)
    # Um arquivo por head, com o recorte aplicado no NIVEL DE DADOS: o arquivo
    # do head so carrega as linhas de cubo do proprio squad. Nao e filtro de
    # interface — o que nao esta no arquivo nao pode ser exibido nem recuperado
    # por manipulacao de parametros.
    ph = _DASH.get("por_head") or {}
    if ph.get("ativo"):
        sem_estrutura = CFG["dimensoes"]["rotulo_sem_estrutura"]
        # D-50: o balde de inativos do saneamento tambem nao e squad de
        # ninguem — sem isto, sairia um "arquivo do head INATIVO (SANEAMENTO)".
        rotulo_inativo = CFG["dimensoes"].get("rotulo_inativo")
        fora = {sem_estrutura, rotulo_inativo}
        heads = [h for h in pacote["dims"]["head"] if h not in fora]
        prefixo = ph.get("prefixo", "Dashboard_Gerencial_Canais_v3_HEAD_")
        soma_heads = 0
        log("")
        log(f"recortes por head ({len(heads)}) — '{sem_estrutura}' fica de "
            "fora: nao e squad de ninguem")
        for head in heads:
            pac = filtrar_por_head(pacote, head)
            # Prova do recorte, nao confianca: nenhuma linha de outro head.
            perf = pac["dims"]["perfil"]
            assert all(perf[l[3]][0] == head for l in pac["cubo"])
            assert all(perf[l[2]][0] == head for l in pac["cubo_sku"])
            rec_head = sum(l[5] for l in pac["cubo"])      # centavos, exato
            soma_heads += rec_head
            # L3-G: sem rodape; titulo e cabecalho seguem declarando o
            # recorte (P2-D) — a restricao de verdade continua sendo o
            # recorte fisico das linhas de cubo, feito acima.
            pac["meta"] = {**pacote["meta"], "recorte_head": head}
            escrever(pac, f"{prefixo}{_slug(head)}.html")
        # Reconciliacao do particionamento: heads + sem-estrutura = base.
        rec_total = sum(l[5] for l in pacote["cubo"])
        rec_resto = rec_total - soma_heads
        log(f"particionamento fecha: heads R$ {br(soma_heads / 100)} + "
            f"fora da hierarquia ('{sem_estrutura}' + inativos) "
            f"R$ {br(rec_resto / 100)} = R$ {br(rec_total / 100)}", "ok")

    log("")
    log(f"tempo total ............ {time.time() - t0:.1f}s")
    log("")
    log("Abra por duplo clique. Nao precisa de servidor nem de internet.", "ok")

    if "--abrir" in sys.argv:
        webbrowser.open(alvo.resolve().as_uri())
    L.fechar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
