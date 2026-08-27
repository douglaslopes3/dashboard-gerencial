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
import sys
import time
import traceback

# O console do Windows abre em cp1252 e engole os acentos do log. O arquivo de
# log ja e UTF-8; isto alinha o console com ele.
for _fluxo in (sys.stdout, sys.stderr):
    try:
        _fluxo.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

from src.extract import cadastros, sellin
from src.load import cubos, parquet
from src.qualidade import gerar as gerar_qualidade
from src.transform import calendario, dimensoes, fato as fato_mod
from src.utils import log as L
from src.utils.config import CFG, PASTA_CURATED, preparar_pastas
from src.utils.log import EXECUCAO_ID, abortar, log, titulo


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

    # ------------------------------------------------------------ 2. FATO
    titulo("2/6 · FATO — grao e reconciliacao contra a origem")
    f = fato_mod.construir(bruto)
    fato_mod.conferir_grao(f)
    avisos_negocio += fato_mod.reconciliar_origem(f, meta)

    # ------------------------------------------------------ 3. DIMENSOES
    titulo("3/6 · DIMENSOES")
    dim_cal = calendario.construir(sorted(f["ANO_MES"].unique()))
    log(f"DIM_CALENDARIO: {len(dim_cal)} meses · anos fiscais "
        f"{sorted(dim_cal['ANO_FISCAL_ROTULO'].unique())}")
    dim_cli = dimensoes.dim_cliente(bruto, estrutura, canais)
    dim_prod = dimensoes.dim_produto(bruto, produtos)

    # ----------------------------------------------------- 4. INTEGRIDADE
    titulo("4/6 · INTEGRIDADE REFERENCIAL")
    fato_mod.conferir_integridade(f, dim_cli, dim_prod, dim_cal)
    cobertura = fato_mod.conferir_cobertura_estrutura(f, dim_cli)
    cobertura_canal = fato_mod.conferir_cobertura_canal(f, dim_cli)

    # -------------------------------------------------------- 5. GRAVAR
    titulo("5/6 · GRAVAR o modelo estrela")
    parquet.salvar(dim_cal, "DIM_CALENDARIO")
    parquet.salvar(dim_cli, "DIM_CLIENTE")
    parquet.salvar(dim_prod, "DIM_PRODUTO")
    f_part = f.copy()
    f_part["ANO"] = f_part["ANO_MES"].str.slice(0, 4)
    parquet.salvar_particionado(f_part, "FATO_SELLIN", "ANO")

    # ------------------------------------------- 6. AGREGAR + QUALIDADE
    titulo("6/6 · AGREGAR e RELATAR")
    pacote = cubos.construir(f, dim_cli, dim_prod, dim_cal)
    cubos.reconciliar(pacote, f)

    alvo = PASTA_CURATED / "cubos.json"
    alvo.write_text(json.dumps(pacote, ensure_ascii=False, separators=(",", ":")),
                    encoding="utf-8")
    log(f"cubos.json             {alvo.stat().st_size / 1024:>10,.0f} KB", "ok")

    resumo = gerar_qualidade(f, dim_cli, dim_prod, dim_cal, meta, cobertura,
                             cobertura_canal, pacote,
                             avisos_negocio + L.avisos())

    # Resumo enxuto para o painel. Existe para que `run_dashboard.py` nao precise
    # reabrir os 3 milhoes de linhas da fato so para escrever o rodape.
    (PASTA_CURATED / "resumo.json").write_text(json.dumps({
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
    }, ensure_ascii=False, indent=1), encoding="utf-8")

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
