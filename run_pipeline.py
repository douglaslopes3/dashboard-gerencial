# -*- coding: utf-8 -*-
"""Dashboard Gerencial de Canais — pipeline de dados.

    python run_pipeline.py

Bases brutas -> ETL -> modelo estrela em Parquet -> cubos -> relatório de
qualidade. Sem IA, sem rede, sem edição manual de código.

REPROCESSAMENTO COMPLETO, sempre. Não há carga incremental: a fonte não tem
chave de controle segura (a competência vem do conteúdo, não do nome do
arquivo), e o volume não pede. Idempotente por construção — rodar duas vezes
seguidas produz exatamente o mesmo Parquet.

Sai com `exit 0` em caso de sucesso e `exit 1` em qualquer falha de validação.
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback

import pandas as pd

# O console do Windows abre em cp1252 e engole os acentos do log. O arquivo de
# log ja e UTF-8; isto alinha o console com ele.
for _fluxo in (sys.stdout, sys.stderr):
    try:
        _fluxo.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

from src.extract import cadastros, metas, sellin
from src.load import cubos, parquet
from src.qualidade import gerar as gerar_qualidade
from src.transform import calendario, dimensoes, fato as fato_mod, saneamento
from src.utils import log as L
from src.utils.config import CFG, PASTA_CURATED, PASTA_QUALITY, preparar_pastas
from src.utils.log import EXECUCAO_ID, abortar, log, titulo


def _gravar_json(alvo, conteudo: str) -> None:
    """Escrita atômica (A6): grava em `.tmp` e troca com `os.replace`. Um
    aborto no meio nunca deixa um JSON pela metade no lugar do anterior."""
    tmp = alvo.with_suffix(alvo.suffix + ".tmp")
    tmp.write_text(conteudo, encoding="utf-8")
    os.replace(tmp, alvo)


def main() -> int:
    t0 = time.time()
    preparar_pastas()
    arq_log = L.abrir()
    avisos_negocio: list[str] = []

    titulo(f"{CFG['projeto']['nome']}  ·  execucao {EXECUCAO_ID}")
    log(f"log desta execucao: {arq_log}")

    # ---------------------------------------------------------- 1. EXTRAIR
    titulo("1/6 · EXTRAIR — localizar, validar schema e ler as fontes")
    bruto, meta = sellin.ler()
    log(f"sell-in consolidado: {len(bruto):,} linhas, "
        f"{bruto['ANO_MES'].nunique()} meses "
        f"({bruto['ANO_MES'].min()} a {bruto['ANO_MES'].max()})")
    avisos_negocio += sellin.conferir_filtro_extracao(meta)

    produtos = cadastros.ler_produtos()
    estrutura, avisos_est = cadastros.ler_estrutura()
    avisos_negocio += avisos_est
    canais, avisos_can = cadastros.ler_canais()
    avisos_negocio += avisos_can
    # D-50 (Fase 2): reatribuicao RTM e saneamento da hierarquia.
    rtm, avisos_rtm = cadastros.ler_rtm()
    avisos_negocio += avisos_rtm
    faltando, avisos_falt = cadastros.ler_faltando()
    avisos_negocio += avisos_falt
    # D-74 (08/09/2026): metas por cliente x categoria x mes (bases/Metas).
    # Fonte opcional: sem arquivo o painel sai sem meta, com aviso.
    fato_meta, meta_metas, avisos_metas = metas.ler()
    avisos_negocio += avisos_metas

    # ------------------------------------------------------------ 2. FATO
    titulo("2/6 · FATO — grao e reconciliacao contra a origem")
    f = fato_mod.construir(bruto)
    fato_mod.conferir_grao(f)
    avisos_negocio += fato_mod.reconciliar_origem(f, meta)

    # ------------------------------------------------------ 3. DIMENSOES
    titulo("3/6 · DIMENSOES")
    # D-74: o calendario cobre ate o ultimo mes com META — out/26 tem meta e
    # ainda nao tem sell-in; sem o mes no calendario a meta nao teria indice.
    dim_cal = calendario.construir(sorted(set(f["ANO_MES"].unique())
                                          | set(fato_meta["ANO_MES"].unique())))
    log(f"DIM_CALENDARIO: {len(dim_cal)} meses · anos fiscais "
        f"{sorted(dim_cal['ANO_FISCAL_ROTULO'].unique())}")
    # D-74/Q4-a: cliente com meta e sem sell-in entra na DIM_CLIENTE.
    dim_cli = dimensoes.dim_cliente(bruto, estrutura, canais,
                                    clientes_extra=fato_meta["COD_CLIENTE"])
    dim_prod = dimensoes.dim_produto(bruto, produtos)
    del bruto    # B4: 692 MB que ninguem mais le — fora do pico de memoria
    # D-74/Q5-a: categoria da meta que nao existe no modelo ABORTA.
    metas.conferir_categorias(fato_meta, dim_prod)
    # D-50: RTM + saneamento agem SO na DIM_CLIENTE — a fato nunca e tocada;
    # e o join com a dimensao que decide a quem o historico aparece atribuido.
    dim_cli, san, avisos_san = saneamento.aplicar(dim_cli, rtm, faltando, f)
    avisos_negocio += avisos_san

    # ----------------------------------------------------- 4. INTEGRIDADE
    titulo("4/6 · INTEGRIDADE REFERENCIAL")
    fato_mod.conferir_integridade(f, dim_cli, dim_prod, dim_cal)
    cobertura = fato_mod.conferir_cobertura_estrutura(f, dim_cli)
    cobertura_canal = fato_mod.conferir_cobertura_canal(f, dim_cli)

    # ------------------------------------------------ 5. AGREGAR e VALIDAR
    titulo("5/6 · AGREGAR — cubos montados e validados ANTES de gravar")
    # A6: o passo de agregacao roda ANTES de qualquer gravacao. Antes, um
    # aborto na validacao dos cubos deixava parquet novo em data/curated com
    # cubos.json/resumo.json velhos — e `run_dashboard.py` publicava painel da
    # execucao anterior com cara de valido.
    pacote = cubos.construir(f, dim_cli, dim_prod, dim_cal, fato_meta=fato_meta)
    cubos.reconciliar(pacote, f)
    # D-74: o CUBO_META (join direto pela chave do cliente, sem rota A) e
    # reconciliado com a FATO_META mes a mes. (O CUBO_META antigo, D-44,
    # saiu na D-49; este e o ponto de reintegracao descrito la.)
    cubos.reconciliar_meta(pacote, fato_meta)
    pacote["execucao"] = EXECUCAO_ID     # conferido por run_dashboard.py (A6)

    # D-74/Q3: a meta de um mes ja carregado pode mudar; a diferenca contra a
    # FATO_META da execucao ANTERIOR fica registrada (append) antes de
    # sobrescrever. Comparacao feita aqui, antes de qualquer gravacao.
    alvo_meta = PASTA_CURATED / "FATO_META.parquet"
    anterior = pd.read_parquet(alvo_meta) if alvo_meta.exists() else None
    revisoes, avisos_rev = metas.registrar_revisoes(
        fato_meta, anterior, PASTA_QUALITY / "metas_revisoes.csv", EXECUCAO_ID)
    avisos_negocio += avisos_rev

    # ------------------------------------------------ 6. GRAVAR e RELATAR
    titulo("6/6 · GRAVAR o modelo estrela e RELATAR")
    parquet.salvar(dim_cal, "DIM_CALENDARIO")
    parquet.salvar(dim_cli, "DIM_CLIENTE")
    parquet.salvar(dim_prod, "DIM_PRODUTO")
    # D-74: FATO_META (ANO_MES x COD_CLIENTE x CATEGORIA), em R$ e KG. Sem
    # meta o parquet e gravado VAZIO (esquema estavel; ausencia declarada).
    parquet.salvar(fato_meta, "FATO_META")
    f_part = f.copy()
    f_part["ANO"] = f_part["ANO_MES"].str.slice(0, 4)
    parquet.salvar_particionado(f_part, "FATO_SELLIN", "ANO")
    del f_part   # B4: ~460 MB fora do pico

    alvo = PASTA_CURATED / "cubos.json"
    _gravar_json(alvo, json.dumps(pacote, ensure_ascii=False,
                                  separators=(",", ":")))
    log(f"cubos.json             {alvo.stat().st_size / 1024:>10,.0f} KB", "ok")

    resumo = gerar_qualidade(f, dim_cli, dim_prod, dim_cal, meta, cobertura,
                             cobertura_canal, pacote,
                             avisos_negocio + L.avisos(), saneamento=san,
                             fato_meta=fato_meta, meta_metas=meta_metas,
                             revisoes_meta=revisoes)

    # Resumo enxuto para o painel. Existe para que `run_dashboard.py` nao precise
    # reabrir os 3 milhoes de linhas da fato so para escrever o rodape.
    # E o ULTIMO write, de proposito: funciona como "commit" da execucao —
    # run_dashboard confere `execucao` do cubos.json x resumo.json (A6).
    _gravar_json(PASTA_CURATED / "resumo.json", json.dumps({
        "execucao": EXECUCAO_ID,
        "gerado_em": time.strftime("%d/%m/%Y %H:%M"),
        "arquivos": len(meta["arquivos"]),
        "linhas": len(f),
        "meses": resumo["meses"],
        "periodo": resumo["periodo"],
        "receita": resumo["total_receita"],
        "peso_t": resumo["total_peso_kg"] / 1000,
        "caixas": resumo["total_caixas"],
        "caixas_sem_info": int(f["CAIXAS"].isna().sum()),
        "clientes": len(dim_cli),
        "skus": len(dim_prod),
        "cobertura_estrutura": cobertura,
        "cobertura_canal": cobertura_canal,
        "avisos": len(L.avisos()),
        # D-74: o painel declara quais meses tem meta (o cubo tambem diz;
        # aqui e para o leitor humano e para o run_dashboard).
        "metas": {"meses": sorted(meta_metas.get("gabarito") or {}),
                  "clientes": int(fato_meta["COD_CLIENTE"].nunique()),
                  "pares": int(len(fato_meta)),
                  "arquivos": [a["arquivo"] for a in meta_metas.get("arquivos") or []]},
    }, ensure_ascii=False, indent=1))

    # ------------------------------------------------------------ RESUMO
    titulo("RESUMO")
    log(f"arquivos lidos ......... {len(meta['arquivos'])}")
    log(f"linhas da fato ......... {len(f):,}")
    log(f"periodo ................ {resumo['periodo']}  ({resumo['meses']} meses)")
    log(f"receita ................ R$ {resumo['total_receita']:,.2f}")
    log(f"peso ................... {resumo['total_peso_kg'] / 1000:,.2f} t")
    log(f"caixas ................. {resumo['total_caixas']:,.0f}")
    log(f"clientes ............... {len(dim_cli):,}")
    log(f"SKUs ................... {len(dim_prod):,}")
    log(f"cobertura da estrutura . {cobertura:.2%}")
    log(f"cobertura de canal ..... {cobertura_canal:.2%}")
    meses_meta = sorted(meta_metas.get("gabarito") or {})
    log(f"metas .................. "
        + (f"{len(meses_meta)} mes(es) ({meses_meta[0]} a {meses_meta[-1]}), "
           f"{fato_meta['COD_CLIENTE'].nunique():,} clientes"
           if meses_meta else "sem base de metas"))
    log(f"avisos ................. {len(L.avisos())}")
    log("")
    log(f"tempo total: {time.time() - t0:.1f}s")
    log("")
    log("SUCESSO. Rode `python run_dashboard.py` para gerar o painel.", "ok")
    L.fechar()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:                                        # noqa: BLE001
        log("falha nao tratada no pipeline:", "erro")
        for l in traceback.format_exc().splitlines():
            log("  " + l, "erro")
        abortar("execucao interrompida")
