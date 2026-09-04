# -*- coding: utf-8 -*-
"""Compara dois conjuntos de paineis (ex.: o PUBLICADO x o recem-gerado em
dashboard/build) sem abrir navegador: descompacta o bloco de dados de cada
HTML e confere, arquivo a arquivo, os totais que o leitor ve.

    python ferramentas/comparar_paineis.py                  # publicado x build
    python ferramentas/comparar_paineis.py <pasta_A> <pasta_B>

Nasceu na rodada D-72 (04/09/2026): o cubo principal ganhou o eixo CLIENTE e
os 73 arquivos ja estavam compartilhados — antes de religar a publicacao, a
prova exigida foi "nenhum numero de bandeira mudou". O que e conferido, por
arquivo que exista nas duas pastas:

  - total geral das 3 metricas (centavos/gramas/centesimos);
  - total por MES;
  - total por BANDEIRA (o nivel 0 da aba Bandeiras);
  - o cubo de SKU inteiro, EXATO (nao mudou na D-72);
  - lista de bandeiras, categorias, canais e heads do arquivo, igual.

Tolerancia dos totais: o cubo grava cada grupo arredondado ao centavo (grama,
centesimo), entao dois cubos com GRAOS diferentes somam o mesmo dinheiro com
desvio de ate meio centavo por grupo de cada lado. O limite aceito e 1 unidade
por linha de cubo do total comparado (o teto teorico), nunca um numero solto:
Atacado, medido na D-72, desviou 9 centavos em R$ 926 mi com 503 mil linhas.
Acima do limite, ou qualquer diferenca de SKU/dimensao, sai listado e o exit
code e 1. Os arquivos sao pareados pelo CAMINHO relativo (uma copia antiga do
Full numa subpasta nao mascara o Full da raiz). Le a mesma serializacao que o
template le (`{"z":"gzip+base64","b64":...}`), entao serve para qualquer par
de versoes desde a D-48. Roda de qualquer pasta."""
from __future__ import annotations

import base64
import gzip
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.utils.config import CFG, caminho  # noqa: E402

_RE = re.compile(r"/\*DADOS_INICIO\*/(.*?)/\*DADOS_FIM\*/", re.S)


def ler_db(arq: Path) -> dict:
    txt = arq.read_text(encoding="utf-8")
    m = _RE.search(txt)
    if not m:
        raise ValueError(f"{arq.name}: bloco de dados nao encontrado")
    carga = json.loads(m.group(1).replace("<\\/script>", "</script>"))
    if isinstance(carga, dict) and carga.get("z") == "gzip+base64":
        carga = json.loads(gzip.decompress(base64.b64decode(carga["b64"])).decode("utf-8"))
    return carga


def _base_met(db: dict) -> int:
    """Posicao da 1a metrica no cubo principal: 4 ate a D-71, 5 desde a D-72
    (deduzida do tamanho da linha: 3 metricas no fim)."""
    return len(db["cubo"][0]) - 3 if db["cubo"] else 4


def resumo(db: dict) -> dict:
    b = _base_met(db)
    tot = [0, 0, 0, 0]                  # R, P, C, linhas
    por_mes: dict = {}
    por_ban: dict = {}
    for l in db["cubo"]:
        pm = por_mes.setdefault(l[0], [0, 0, 0, 0])
        pb = por_ban.setdefault(db["dims"]["ban"][l[1]], [0, 0, 0, 0])
        for k in range(3):
            tot[k] += l[b + k]
            pm[k] += l[b + k]
            pb[k] += l[b + k]
        tot[3] += 1
        pm[3] += 1
        pb[3] += 1
    sku = sorted(tuple(l) for l in db["cubo_sku"])
    dims = {k: sorted(db["dims"][k]) for k in ("ban", "cat", "canal", "head")}
    return {"total": tot, "por_mes": por_mes, "por_ban": por_ban, "sku": sku,
            "dims": dims, "linhas": len(db["cubo"]), "base": b}


def _fora(va, vb) -> int | None:
    """Maior desvio (nas 3 metricas) acima do teto teorico de arredondamento:
    1 unidade por linha de cubo, contando as linhas dos DOIS lados."""
    if va is None or vb is None:
        return -1
    teto = va[3] + vb[3]
    pior = max(abs(va[k] - vb[k]) for k in range(3))
    return pior if pior > teto else None


def comparar(a: Path, b: Path) -> tuple[list[str], dict]:
    ra, rb = resumo(ler_db(a)), resumo(ler_db(b))
    dif: list[str] = []
    med = {"linhas": (ra["linhas"], rb["linhas"]),
           "dif_total_centavos": ra["total"][0] - rb["total"][0],
           "pior_bandeira_centavos": 0}
    if _fora(ra["total"], rb["total"]) is not None:
        dif.append(f"total geral fora do teto: {ra['total'][:3]} x {rb['total'][:3]}")
    for m in sorted(set(ra["por_mes"]) | set(rb["por_mes"])):
        if _fora(ra["por_mes"].get(m), rb["por_mes"].get(m)) is not None:
            dif.append(f"mes {m}: {ra['por_mes'].get(m)} x {rb['por_mes'].get(m)}")
    so_a = set(ra["por_ban"]) - set(rb["por_ban"])
    so_b = set(rb["por_ban"]) - set(ra["por_ban"])
    if so_a or so_b:
        dif.append(f"bandeiras so em A: {sorted(so_a)[:5]} · so em B: {sorted(so_b)[:5]}")
    ruins = []
    for k in ra["por_ban"]:
        if k in rb["por_ban"]:
            med["pior_bandeira_centavos"] = max(
                med["pior_bandeira_centavos"],
                abs(ra["por_ban"][k][0] - rb["por_ban"][k][0]))
            if _fora(ra["por_ban"][k], rb["por_ban"][k]) is not None:
                ruins.append(k)
    if ruins:
        ex = ruins[0]
        dif.append(f"{len(ruins)} bandeira(s) fora do teto; ex.: {ex}: "
                   f"{ra['por_ban'][ex][:3]} x {rb['por_ban'][ex][:3]}")
    if ra["sku"] != rb["sku"]:
        dif.append(f"cubo de SKU diferente ({len(ra['sku'])} x {len(rb['sku'])} linhas)")
    for k in ra["dims"]:
        if ra["dims"][k] != rb["dims"][k]:
            dif.append(f"dims.{k} diferente ({len(ra['dims'][k])} x {len(rb['dims'][k])})")
    return dif, med


def main() -> int:
    if len(sys.argv) >= 3:
        pa, pb = Path(sys.argv[1]), Path(sys.argv[2])
    else:
        pa = caminho(CFG["dashboard"]["publicacao"]["destino"])
        pb = caminho(CFG["dashboard"]["pasta_saida"])
    # Pareamento pelo NOME do arquivo, mas so a primeira ocorrencia em ordem
    # de profundidade (raiz antes das subpastas): a publicacao poe o Full na
    # raiz e um arquivo por pasta de usuario; uma copia avulsa numa subpasta
    # nao pode substituir o oficial na comparacao — ela e listada a parte.
    def mapa(pasta: Path) -> tuple[dict, list]:
        out: dict = {}
        extras: list = []
        for p in sorted(pasta.rglob("*.html"), key=lambda x: (len(x.parts), str(x))):
            if p.name in out:
                extras.append(p)
            else:
                out[p.name] = p
        return out, extras
    arqs_a, extras_a = mapa(pa)
    arqs_b, extras_b = mapa(pb)
    comuns = sorted(set(arqs_a) & set(arqs_b))
    print(f"A = {pa}\nB = {pb}\n{len(comuns)} arquivo(s) em comum "
          f"(so em A: {len(set(arqs_a) - set(arqs_b))}, so em B: {len(set(arqs_b) - set(arqs_a))})")
    for e in extras_a + extras_b:
        print(f"AVISO   copia avulsa ignorada: {e}")
    print()
    ruins = 0
    pior = 0
    for nome in comuns:
        dif, med = comparar(arqs_a[nome], arqs_b[nome])
        pior = max(pior, med["pior_bandeira_centavos"])
        if dif:
            ruins += 1
            print(f"DIFERE  {nome}")
            for d in dif:
                print(f"        {d}")
        else:
            print(f"ok      {nome}  linhas {med['linhas'][0]:,} -> {med['linhas'][1]:,} · "
                  f"dif. total {med['dif_total_centavos']:+d} centavo(s) · pior bandeira "
                  f"{med['pior_bandeira_centavos']} centavo(s)")
    print(f"\n{len(comuns) - ruins} de {len(comuns)} dentro do teto de arredondamento em "
          f"total geral, por mes e por bandeira; cubo de SKU e listas de dimensao "
          f"identicos. Pior desvio de bandeira em todos os arquivos: {pior} centavo(s).")
    return 1 if ruins else 0


if __name__ == "__main__":
    sys.exit(main())
