# -*- coding: utf-8 -*-
"""Recolhe os paineis ANTIGOS das pastas de publicacao (03/09/2026, D-60).

    python ferramentas/limpar_paineis_antigos.py            move para a quarentena
    python ferramentas/limpar_paineis_antigos.py --listar   so mostra, nao move

Quando rodar: sempre que um nome de saida mudar (`dashboard.arquivo_saida`,
`dashboard.por_nivel.prefixo`) ou um colaborador sair da estrutura — depois
de `python run_dashboard.py`, nunca antes.

POR QUE ELE EXISTE
------------------
A publicacao copia SUBSTITUINDO pelo mesmo nome, e a geracao **nao apaga o que
ela nao criou** (regra da D-52, deliberada: um script que apaga arquivo na
pasta de outra pessoa e um script que um dia apaga o errado). Quando a D-58
renomeou as saidas — "_Canais_v4" saiu do nome —, os arquivos antigos ficaram
para tras: cada pasta de usuario passou a ter DOIS paineis, e o antigo esta
congelado nos dados do dia em que foi gerado.

O QUE ELE FAZ
-------------
NAO apaga nada. Move o que sobrou para uma pasta de quarentena dentro do
proprio destino, preservando de qual pasta cada arquivo veio, para o Douglas
conferir e apagar a quarentena inteira de uma vez. Mesmo padrao da D-53
(`_arquivo/`): nada e destruido, so recolhido.

COMO ELE DECIDE O QUE E "ANTIGO"
--------------------------------
Nao por lista de nomes nem por "contem _Canais_v4" — isso so resolveria ESTE
caso e deixaria passar o proximo. Ele CALCULA quais arquivos a geracao atual
produz (lendo o mesmo config e o mesmo `cubos.json` que o `run_dashboard.py`
usa, com as mesmas funcoes de nome) e recolhe todo `.html` do destino que nao
esta nessa lista. Assim ele tambem pega restos de versoes anteriores e de
colaboradores que sairam da estrutura.

GUARDA
------
Antes de mover qualquer coisa, confere que TODOS os arquivos esperados existem
no destino. Se faltar algum, ABORTA sem mexer em nada — arquivo esperado
faltando significa que a geracao nao rodou depois da renomeacao, e nesse estado
o "antigo" pode ser o unico painel que a pessoa tem.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

# O script mora em ferramentas/, fora da raiz: a raiz entra no path para os
# imports de src/ e de run_dashboard funcionarem de qualquer pasta.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

for _fluxo in (sys.stdout, sys.stderr):
    try:
        _fluxo.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

from run_dashboard import _pasta_usuario, _slug, pasta_do_full
from src.utils import log as L
from src.utils.config import CFG, PASTA_CURATED, caminho
from src.utils.log import abortar, log, titulo

_DASH = CFG["dashboard"]
QUARENTENA = "_ANTIGOS_PARA_APAGAR"


def esperados(destino: Path) -> set[Path]:
    """Os arquivos que a geracao ATUAL produz — calculados com as mesmas
    funcoes e o mesmo config que `run_dashboard.py` usa."""
    fonte = PASTA_CURATED / "cubos.json"
    if not fonte.exists():
        abortar(f"{fonte} nao existe. Rode `python run_pipeline.py` primeiro.")
    pacote = json.loads(fonte.read_text(encoding="utf-8"))
    perfis = pacote["dims"]["perfil"]

    fora = {CFG["dimensoes"]["rotulo_sem_estrutura"],
            CFG["dimensoes"].get("rotulo_inativo")}
    pn = _DASH.get("por_nivel") or {}
    prefixo = pn.get("prefixo", "Dashboard_Gerencial_")

    # o Full: na subpasta `publicacao.pasta_full` (D-73) ou na raiz (Q13)
    alvo = {pasta_do_full(destino, _DASH.get("publicacao") or {})
            / _DASH["arquivo_saida"]}
    if pn.get("ativo"):
        for nome_nivel, pos in (pn.get("niveis") or {}).items():
            for rot in sorted({p[int(pos)] for p in perfis} - fora):
                alvo.add(destino / _pasta_usuario(rot)
                         / f"{prefixo}{nome_nivel}_{_slug(rot)}.html")
    return alvo


def main() -> int:
    L.abrir()
    titulo("Recolher paineis antigos das pastas de publicacao")
    so_listar = "--listar" in sys.argv

    pub = _DASH.get("publicacao") or {}
    if not pub.get("destino"):
        abortar("`dashboard.publicacao.destino` nao esta no config.")
    destino = caminho(pub["destino"]).resolve()
    if not destino.exists():
        abortar(f"pasta de publicacao nao encontrada: {destino}")
    log(f"destino: {destino}")

    alvo = esperados(destino)
    log(f"a geracao atual produz {len(alvo)} arquivo(s)")

    # ---- GUARDA: nada e movido se algum painel atual estiver faltando -----
    faltando = sorted(p for p in alvo if not p.exists())
    if faltando:
        log("")
        for p in faltando[:10]:
            log(f"  FALTA {p.relative_to(destino)}", "erro")
        if len(faltando) > 10:
            log(f"  ... e mais {len(faltando) - 10}", "erro")
        abortar(f"{len(faltando)} painel(is) da geracao atual nao estao no "
                "destino — rode `python run_dashboard.py` antes de recolher. "
                "Nada foi movido.")

    quarentena = destino / QUARENTENA
    achados = [p for p in destino.rglob("*.html")
               if p.resolve() not in {a.resolve() for a in alvo}
               and QUARENTENA not in p.parts]
    if not achados:
        log("")
        log("nenhum arquivo antigo — as pastas ja estao limpas.", "ok")
        L.fechar()
        return 0

    log("")
    log(f"{len(achados)} arquivo(s) antigo(s) encontrado(s):")
    total_mb = 0.0
    for p in sorted(achados):
        mb = p.stat().st_size / 1024 / 1024
        total_mb += mb
        log(f"  {str(p.relative_to(destino)):<78} {mb:>7,.2f} MB")
    log(f"  {'TOTAL':<78} {total_mb:>7,.2f} MB")

    if so_listar:
        log("")
        log("--listar: nada foi movido.", "ok")
        L.fechar()
        return 0

    log("")
    movidos = 0
    for p in sorted(achados):
        rel = p.relative_to(destino)
        novo = quarentena / rel
        novo.parent.mkdir(parents=True, exist_ok=True)
        if novo.exists():                       # execucao repetida
            novo.unlink()
        shutil.move(str(p), str(novo))
        movidos += 1
    log(f"{movidos} arquivo(s) movido(s) para {QUARENTENA}\\ "
        f"({total_mb:,.2f} MB)", "ok")
    log("")
    log("A estrutura de pastas foi preservada dentro da quarentena, para dar")
    log("para conferir de qual usuario veio cada arquivo. Nada foi apagado:")
    log(f"apague a pasta {quarentena} inteira quando conferir.")
    log("")
    log("As pastas de usuario ficaram com UM painel cada — o atual.", "ok")
    L.fechar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
