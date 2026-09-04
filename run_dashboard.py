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

from src.load.cubos import COLS_PERFIL
from src.utils import log as L
from src.utils.config import CFG, PASTA_CURATED, caminho, preparar_pastas
from src.utils.log import abortar, log, titulo

_DASH = CFG["dashboard"]
RE_LIB = re.compile(r"<!--LIB:([a-zA-Z0-9_-]+)-->")

# D-54: as posicoes do perfil sao lidas da MESMA lista que monta o cubo — sem
# numero magico aqui e sem risco de divergir se a ordem de COLS_PERFIL mudar.
P_HEAD = COLS_PERFIL.index("HEAD")
P_CANAL = COLS_PERFIL.index("CANAL")


def _slug(s: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFD", str(s))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn").lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t[:60]


def filtrar_por_nivel(pacote: dict, pos: int, rotulo: str,
                      nome_nivel: str | None = None) -> dict:
    """Recorte FISICO por um nivel da hierarquia (D-52): o pacote devolvido so
    contem as linhas de cubo cujo perfil carrega `rotulo` na posicao `pos`
    (0 = head, 1 = gerente, 2 = sup./exec.). E o filtro no nivel de DADOS: o
    que nao esta no arquivo nao existe para quem o abre — nao ha parametro de
    interface que traga de volta.

    D-54 (03/09/2026): TODA lista de dimensao que vira chip ou rotulo na tela e
    recalculada sobre o cubo JA RECORTADO — nao so a de heads. Ate a D-52 so
    `perfil` e `head` encolhiam, e o arquivo de um head continuava carregando a
    lista de canais, de categorias e de SKUs da empresa inteira: o painel do
    Michel Meira exibia o chip de um canal em que o squad dele nao tem uma
    unica linha, e a nota de Categorias prometia "os 400 SKUs da base". A regra
    e uma so, e vale para qualquer nivel: **opcao sem linha por tras dela nao
    entra no arquivo**. Nada de lista de nomes, nada de excecao por pessoa.

    O que NAO encolhe, de proposito: `cal` — remapear mes reindexaria os dois
    cubos e os ponteiros de LY; mes sem faturamento e resolvido na interface,
    que ja sabe olhar o indice por mes (`opcoesComDado`, template v4).

    D-65 (03/09/2026): `dims.ban` tambem encolhe (o cubo carrega TODAS as
    bandeiras, D-65, e o arquivo de um colaborador leva so as do escopo dele,
    reindexadas). A D-57 (Σ recontado por nivel) foi superada: nao ha mais
    balde na geracao; o corte e de EXIBICAO e mora no template. Aqui so se
    decide se o nivel exibe todas (`dashboard.exibir_todas_bandeiras_em`)."""
    dims = pacote["dims"]
    manter_perf = [i for i, p in enumerate(dims["perfil"]) if p[pos] == rotulo]
    mapa_perf = {i: j for j, i in enumerate(manter_perf)}

    # D-51: sem o eixo UF o cubo principal tem 7 colunas (4 indices + 3
    # metricas). D-64: o de SKU tem 6 (mes, sku, perfil + 3 metricas).
    cubo = [[l[0], l[1], l[2], mapa_perf[l[3]], l[4], l[5], l[6]]
            for l in pacote["cubo"] if l[3] in mapa_perf]
    cubo_sku = [[l[0], l[1], mapa_perf[l[2]], l[3], l[4], l[5]]
                for l in pacote["cubo_sku"] if l[2] in mapa_perf]

    perfil = [dims["perfil"][i] for i in manter_perf]

    # ---- categoria e SKU: reindexados sobre o que sobrou -----------------
    # A categoria viaja como INDICE nos dois cubos (coluna 2 do principal e a
    # 3a posicao do rotulo de SKU). Encolher a lista sem remapear os dois
    # apontaria para a categoria errada — por isso o mapa e aplicado nas duas
    # pontas na mesma passada.
    manter_cat = sorted({l[2] for l in cubo})
    mapa_cat = {c: i for i, c in enumerate(manter_cat)}
    manter_sku = sorted({l[1] for l in cubo_sku})
    mapa_sku = {s: i for i, s in enumerate(manter_sku)}

    # ---- bandeira (D-65): so as do escopo, reindexadas. A ordem dos indices
    # e a do ranking global por receita (cubos.py), e `sorted` a preserva.
    manter_ban = sorted({l[1] for l in cubo})
    mapa_ban = {b: i for i, b in enumerate(manter_ban)}

    cubo = [[l[0], mapa_ban[l[1]], mapa_cat[l[2]], l[3], l[4], l[5], l[6]]
            for l in cubo]
    cubo_sku = [[l[0], mapa_sku[l[1]], l[2], l[3], l[4], l[5]]
                for l in cubo_sku]

    sku = [[cod, desc, mapa_cat.get(ic, -1)]
           for cod, desc, ic in (dims["sku"][i] for i in manter_sku)]

    # D-65: o corte e de EXIBICAO e mora no template; aqui o arquivo declara
    # quantas bandeiras carrega e se o nivel exibe todas (N2/N3, config).
    todas_em = [str(x) for x in (_DASH.get("exibir_todas_bandeiras_em") or [])]
    corte = {**(pacote.get("corte_bandeira") or {}),
             "universo": len(manter_ban),
             "exibir_todas": str(nome_nivel) in todas_em}

    novo = dict(pacote)
    novo["dims"] = {**dims,
                    "head": sorted({perfil[l[3]][P_HEAD] for l in cubo}),
                    "canal": sorted({perfil[l[3]][P_CANAL] for l in cubo}),
                    "cat": [dims["cat"][i] for i in manter_cat],
                    "ban": [dims["ban"][i] for i in manter_ban],
                    "sku": sku,
                    "perfil": perfil}
    novo["cubo"] = cubo
    novo["cubo_sku"] = cubo_sku
    novo["corte_bandeira"] = corte
    return novo


def _pasta_usuario(rotulo: str) -> str:
    """Nome da pasta por usuario no SharePoint (Q13): o rotulo completo do
    colaborador, legivel, com os caracteres invalidos de pasta trocados por
    '-' (ex.: 'Superv_RS/SC' -> 'Superv_RS-SC')."""
    nome = re.sub(r'[<>:"/\\|?*]', "-", str(rotulo)).strip(" .")
    return nome[:100]


def publicar(origem: Path, destino_dir: Path) -> None:
    """Copia SUBSTITUINDO (mesmo nome -> links do SharePoint continuam
    validos) e confere o hash — padrao da publicacao de 01/09/2026."""
    import hashlib
    import shutil
    destino_dir.mkdir(parents=True, exist_ok=True)
    alvo = destino_dir / origem.name
    shutil.copy2(origem, alvo)
    h1 = hashlib.md5(origem.read_bytes()).hexdigest()
    h2 = hashlib.md5(alvo.read_bytes()).hexdigest()
    if h1 != h2:
        abortar(f"publicacao corrompida: hash divergente em {alvo}")


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
    pacote["tops"] = {"ban": _DASH["tops_bandeira"]}
    pacote["top_ranking"] = int(_DASH["top_ranking"])
    # D-51: a matriz hierarquica exibe estes rotulos como linhas sintese "fora
    # da hierarquia" (sem expansao). As strings vem do config — o template nao
    # carrega valor de negocio.
    pacote["rotulos_fora"] = [
        CFG["dimensoes"]["rotulo_sem_estrutura"],
        CFG["dimensoes"].get("rotulo_inativo"),
    ]

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
    # ------------------------------------------- arquivos por nivel (D-52)
    # Um arquivo por colaborador, N1 a N3, recorte fisico na geracao. O N4
    # nao gera arquivo (decisao de 02/09); os baldes fora-da-hierarquia
    # tambem nao. Cada NIVEL particiona a base inteira — a reconciliacao
    # roda nivel a nivel.
    pn = _DASH.get("por_nivel") or {}
    if pn.get("ativo"):
        sem_estrutura = CFG["dimensoes"]["rotulo_sem_estrutura"]
        rotulo_inativo = CFG["dimensoes"].get("rotulo_inativo")
        fora = {sem_estrutura, rotulo_inativo}
        prefixo = pn.get("prefixo", "Dashboard_Gerencial_")
        pub = _DASH.get("publicacao") or {}
        destino = caminho(pub["destino"]) if pub.get("ativo") else None
        rec_total = sum(l[4] for l in pacote["cubo"])      # centavos, exato
        n_arquivos = 0
        for nome_nivel, pos in (pn.get("niveis") or {}).items():
            pos = int(pos)
            rotulos = sorted({p[pos] for p in pacote["dims"]["perfil"]} - fora)
            log("")
            log(f"recortes {nome_nivel} ({len(rotulos)}) — baldes "
                "fora-da-hierarquia nao geram arquivo")
            soma_nivel = 0
            for rot in rotulos:
                pac = filtrar_por_nivel(pacote, pos, rot, nome_nivel)
                # Prova do recorte, nao confianca: nenhuma linha de fora.
                perf = pac["dims"]["perfil"]
                assert all(perf[l[3]][pos] == rot for l in pac["cubo"])
                assert all(perf[l[2]][pos] == rot for l in pac["cubo_sku"])
                # D-65: toda linha aponta para uma bandeira DA LISTA do arquivo
                assert all(l[1] < len(pac["dims"]["ban"]) for l in pac["cubo"])
                soma_nivel += sum(l[4] for l in pac["cubo"])
                # P2-D/L3-G: titulo e cabecalho declaram o recorte; a
                # restricao de verdade e o recorte fisico feito acima.
                pac["meta"] = {**pacote["meta"], "recorte": rot,
                               "recorte_nivel": nome_nivel}
                alvo_n = escrever(pac, f"{prefixo}{nome_nivel}_{_slug(rot)}.html")
                n_arquivos += 1
                if destino:
                    publicar(alvo_n, destino / _pasta_usuario(rot))
            # Cada nivel particiona a base: rotulos + fora = total.
            resto = rec_total - soma_nivel
            log(f"particionamento {nome_nivel} fecha: "
                f"R$ {br(soma_nivel / 100)} + fora da hierarquia "
                f"R$ {br(resto / 100)} = R$ {br(rec_total / 100)}", "ok")
        if destino:
            # Q13: o painel Full vai para a RAIZ do destino, fora das pastas
            # compartilhadas — e o unico com a visao corporativa inteira.
            publicar(alvo, destino)
            log("")
            log(f"publicados {n_arquivos} arquivos por nivel (pasta por "
                f"usuario) + o Full na raiz de {destino}", "ok")

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
