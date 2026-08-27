# -*- coding: utf-8 -*-
"""Relatório de qualidade e linhagem — o checklist do §14 do prompt.

Este passo NÃO corrige nada. Ele mede, escreve e conta. Divergência corrigida em
silêncio é o único jeito garantido de o painel "fechar" errado.

Saídas em `data/quality/`:
  relatorio_qualidade.md          o relatório da execução
  valores_nao_reconhecidos.csv    categoria/head fora da lista esperada do config
  clientes_sem_estrutura.csv      quem fatura e não tem head
  skus_sem_cadastro.csv           quem fatura e não está no Produtos.xlsx
  linhagem_arquivos.csv           arquivo -> meses, linhas, totais
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from .utils.config import CFG, PASTA_QUALITY
from .utils.log import EXECUCAO_ID, log

_ESPERADOS = CFG["validacao"]["valores_esperados"]


def _csv(df: pd.DataFrame, nome: str) -> None:
    PASTA_QUALITY.mkdir(parents=True, exist_ok=True)
    df.to_csv(PASTA_QUALITY / nome, index=False, encoding="utf-8-sig", sep=";")


def _fmt(x: float, casas: int = 2) -> str:
    return f"{x:,.{casas}f}".replace(",", "@").replace(".", ",").replace("@", ".")


def gerar(fato: pd.DataFrame, dim_cliente: pd.DataFrame,
          dim_produto: pd.DataFrame, dim_cal: pd.DataFrame,
          meta: dict, cobertura_head: float, cobertura_canal: float,
          pacote_cubo: dict, avisos: list[str]) -> dict:
    PASTA_QUALITY.mkdir(parents=True, exist_ok=True)
    L: list[str] = []
    resumo: dict = {}

    def linha(s: str = "") -> None:
        L.append(s)

    linha(f"# Relatório de qualidade — execução `{EXECUCAO_ID}`")
    linha()
    linha(f"Gerado em {datetime.now():%d/%m/%Y %H:%M:%S}.")
    linha()

    # ---------------------------------------------------------- 1. linhagem
    linha("## 1. Arquivos processados")
    linha()
    por_arq = (fato.groupby("ARQUIVO_ORIGEM")
                   .agg(LINHAS=("RECEITA", "size"),
                        RECEITA=("RECEITA", "sum"),
                        PESO_KG=("PESO_KG", "sum"),
                        CAIXAS=("CAIXAS", "sum"))
                   .reset_index())
    por_arq["MESES"] = por_arq["ARQUIVO_ORIGEM"].map(
        lambda a: ", ".join(meta["meses_por_arquivo"].get(a, [])))
    _csv(por_arq, "linhagem_arquivos.csv")

    linha(f"- **Aceitos:** {len(por_arq)}")
    linha("- **Rejeitados:** 0 — arquivo incompatível aborta o pipeline antes "
          "deste ponto, nunca entra pela metade")
    linha()
    linha("| Arquivo | Mês(es) | Linhas | Receita R$ | Peso kg | Caixas |")
    linha("|---|---|---:|---:|---:|---:|")
    for r in por_arq.itertuples():
        linha(f"| `{r.ARQUIVO_ORIGEM}` | {r.MESES} | {r.LINHAS:,} | "
              f"{_fmt(r.RECEITA)} | {_fmt(r.PESO_KG)} | {_fmt(r.CAIXAS, 0)} |")
    linha()
    linha("> A competência vem do **conteúdo** (`Ano mês`), nunca do nome do "
          "arquivo. Renomear um arquivo não muda o mês em que ele entra.")
    linha()

    # ------------------------------------------------------------ 2. periodo
    meses = sorted(fato["ANO_MES"].unique())
    resumo["meses"] = len(meses)
    resumo["periodo"] = f"{meses[0]} a {meses[-1]}"
    esperados = set(dim_cal["ANO_MES"])
    buracos = sorted(esperados - set(meses))
    linha("## 2. Período coberto")
    linha()
    linha(f"- **{len(meses)} meses**, de `{meses[0]}` a `{meses[-1]}`")
    linha(f"- Meses sem faturamento dentro do intervalo: "
          f"{('**' + ', '.join(buracos) + '**') if buracos else 'nenhum'}")
    com_ly = int(dim_cal["ANO_MES_LY"].notna().sum())
    linha(f"- Meses com ano anterior pareado: **{com_ly} de {len(dim_cal)}**")
    linha()

    # ------------------------------------------------------------ 3. volumes
    linha("## 3. Totais e sinais")
    linha()
    linha("| Métrica | Soma | Negativos | Zeros | Nulos |")
    linha("|---|---:|---:|---:|---:|")
    for col, nome in (("RECEITA", "Receita R$"), ("PESO_KG", "Peso kg"),
                      ("CAIXAS", "Caixas")):
        s = fato[col]
        linha(f"| {nome} | {_fmt(s.sum())} | {int((s < 0).sum()):,} | "
              f"{int((s == 0).sum()):,} | {int(s.isna().sum()):,} |")
        resumo[f"total_{col.lower()}"] = float(s.sum())
    linha()
    neg = fato[fato["RECEITA"] < 0]
    cx_neg = int(neg["CAIXAS"].isna().sum())
    linha(f"- Linhas com receita negativa (devolução): **{len(neg):,}**. Dessas, "
          f"**{cx_neg:,} ({cx_neg / max(len(neg), 1):.1%})** não têm caixa "
          "informada na fonte.")
    linha("- **Caixas é métrica BRUTA** — não líquida de devolução, ao contrário "
          "de Receita e Peso. Ver GAP-04 em `docs/04_GAPS_E_RISCOS.md`.")
    linha()

    # -------------------------------------------------------- 4. duplicidade
    linha("## 4. Chaves e duplicidade")
    linha()
    dup = int(fato.duplicated(["ANO_MES", "COD_CLIENTE", "COD_PRODUTO"]).sum())
    linha(f"- Duplicados no grão `ANO_MES × COD_CLIENTE × COD_PRODUTO`: "
          f"**{dup:,}** de {len(fato):,}")
    for c in ("ANO_MES", "COD_CLIENTE", "COD_PRODUTO"):
        linha(f"- Chaves nulas em `{c}`: **{int(fato[c].isna().sum()):,}**")
    linha()

    # ------------------------------------------------------- 5. integridade
    linha("## 5. Integridade fato ↔ dimensões")
    linha()
    for coluna, dim, nome in (("COD_PRODUTO", dim_produto, "DIM_PRODUTO"),
                              ("COD_CLIENTE", dim_cliente, "DIM_CLIENTE"),
                              ("ANO_MES", dim_cal, "DIM_CALENDARIO")):
        orfaos = int((~fato[coluna].isin(set(dim[coluna]))).sum())
        linha(f"- `{coluna}` → {nome}: **{orfaos:,}** órfã(s)")
    linha()

    # ------------------------------------------- 6. valores nao reconhecidos
    linha("## 6. Valores não reconhecidos (§9 do prompt)")
    linha()
    linha("A lista esperada está em `config/config.yaml → "
          "validacao.valores_esperados`. Ela **só confere** — não filtra, não "
          "corrige e não ordena nada.")
    linha()
    nao_rec = []
    cat_real = set(dim_produto["CATEGORIA"].dropna())
    for v in sorted(cat_real - set(_ESPERADOS.get("categoria", []))):
        n = int((dim_produto["CATEGORIA"] == v).sum())
        nao_rec.append({"DIMENSAO": "CATEGORIA", "VALOR": v, "SKUS": n})
    head_real = set(dim_cliente["HEAD"].dropna())
    esperados_head = set(_ESPERADOS.get("head", []))
    for v in sorted(head_real):
        # comparacao por prefixo: "Izabela - 2650" reconhece "Izabela"
        if not any(str(v).lower().startswith(str(e).lower()) for e in esperados_head):
            n = int((dim_cliente["HEAD"] == v).sum())
            nao_rec.append({"DIMENSAO": "HEAD", "VALOR": v, "SKUS": n})
    canal_real = set(dim_cliente["CANAL"].dropna()) - {"SEM CANAL"}
    for v in sorted(canal_real - set(_ESPERADOS.get("canal", []))):
        n = int((dim_cliente["CANAL"] == v).sum())
        nao_rec.append({"DIMENSAO": "CANAL", "VALOR": v, "SKUS": n})
    df_nr = pd.DataFrame(nao_rec, columns=["DIMENSAO", "VALOR", "SKUS"])
    _csv(df_nr, "valores_nao_reconhecidos.csv")
    resumo["valores_nao_reconhecidos"] = len(df_nr)
    if len(df_nr):
        linha("| Dimensão | Valor encontrado | Itens |")
        linha("|---|---|---:|")
        for r in df_nr.itertuples():
            linha(f"| {r.DIMENSAO} | `{r.VALOR}` | {r.SKUS:,} |")
        linha()
        linha("> **Nada foi corrigido.** Correção de rótulo é decisão de negócio "
              "e vive em `config/config.yaml → dimensoes.estrutura_comercial`.")
    else:
        linha("Nenhum. Todos os valores batem com a lista esperada.")
    linha()
    ufs = sorted(dim_cliente["UF"].dropna().unique())
    linha(f"- UFs distintas: **{len(ufs)}** — {', '.join(ufs)}")
    linha()

    # ---------------------------------------------- 7. sem classificacao
    linha("## 7. Registros sem classificação")
    linha()
    sem_est = dim_cliente[~dim_cliente["NA_ESTRUTURA"]]
    rec_sem = float(fato.loc[fato["COD_CLIENTE"].isin(set(sem_est["COD_CLIENTE"])),
                             "RECEITA"].sum())
    _csv(sem_est[["COD_CLIENTE", "NOME_CLIENTE", "BANDEIRA", "UF"]],
         "clientes_sem_estrutura.csv")
    linha(f"- Clientes sem head no de-para: **{len(sem_est):,}** de "
          f"{len(dim_cliente):,} · receita **R$ {_fmt(rec_sem)}** "
          f"({rec_sem / max(float(fato['RECEITA'].sum()), 1):.2%})")
    linha(f"- Cobertura da estrutura comercial sobre a receita: "
          f"**{cobertura_head:.2%}**")

    sem_canal = dim_cliente[~dim_cliente["TEM_CANAL"]] \
        if "TEM_CANAL" in dim_cliente.columns else dim_cliente.iloc[0:0]
    rec_canal = float(fato.loc[fato["COD_CLIENTE"].isin(set(sem_canal["COD_CLIENTE"])),
                               "RECEITA"].sum())
    _csv(sem_canal[["COD_CLIENTE", "NOME_CLIENTE", "BANDEIRA", "UF"]],
         "clientes_sem_canal.csv")
    linha(f"- Clientes sem canal no de-para: **{len(sem_canal):,}** de "
          f"{len(dim_cliente):,} · receita **R$ {_fmt(rec_canal)}** "
          f"({rec_canal / max(float(fato['RECEITA'].sum()), 1):.2%})")
    linha(f"- Cobertura de canal sobre a receita: **{cobertura_canal:.2%}**")

    sem_cad = dim_produto[dim_produto["FORA_DO_CADASTRO"]]
    rec_sku = float(fato.loc[fato["COD_PRODUTO"].isin(set(sem_cad["COD_PRODUTO"])),
                             "RECEITA"].sum())
    _csv(sem_cad[["COD_PRODUTO", "DESCRICAO_PRODUTO", "CATEGORIA"]],
         "skus_sem_cadastro.csv")
    linha(f"- SKUs fora do cadastro `Produtos.xlsx`: **{len(sem_cad)}** de "
          f"{len(dim_produto)} · receita **R$ {_fmt(rec_sku)}** "
          f"({rec_sku / max(float(fato['RECEITA'].sum()), 1):.2%})")
    linha(f"- Clientes sem bandeira: "
          f"**{int((dim_cliente['BANDEIRA'] == 'SEM BANDEIRA').sum()):,}**")
    linha()
    linha("> Nenhum deles é descartado. Descartar faria o total do painel deixar "
          "de bater com o total da fonte.")
    linha()
    resumo["clientes_sem_estrutura"] = len(sem_est)
    resumo["clientes_sem_canal"] = len(sem_canal)
    resumo["skus_sem_cadastro"] = len(sem_cad)

    # ------------------------------------------------------------- 8. cubos
    corte = pacote_cubo["corte_bandeira"]
    linha("## 8. Camada agregada")
    linha()
    linha(f"- `CUBO_PRINCIPAL`: **{len(pacote_cubo['cubo']):,}** linhas")
    linha(f"- `CUBO_SKU`: **{len(pacote_cubo['cubo_sku']):,}** linhas")
    linha(f"- Bandeiras no ranking: **{corte['top']:,}** "
          f"(**{corte['cobertura']:.1%}** da receita); as outras "
          f"**{corte['demais']:,}** entram agregadas em `{corte['rotulo_demais']}`, "
          "então o total continua fechando")
    linha("- Reconciliação cubo × fato nas 3 métricas: **ok** (o pipeline aborta "
          "se não fechar)")
    linha()

    # ------------------------------------------------------- 9. divisao/zero
    linha("## 9. Divisão por zero")
    linha()
    peso_zero_meses = int((fato.groupby("ANO_MES")["PESO_KG"].sum() == 0).sum())
    linha(f"- Meses com peso total zero (preço médio ficaria indefinido): "
          f"**{peso_zero_meses}**")
    linha("- Comportamento na interface: denominador zero ou nulo exibe **`n/d`** "
          "com tooltip, nunca `∞`, `NaN` ou erro técnico.")
    linha()

    # ---------------------------------------------------------- 10. avisos
    linha("## 10. Avisos desta execução")
    linha()
    if avisos:
        for a in avisos:
            linha(f"- {a}")
    else:
        linha("Nenhum.")
    linha()
    linha("---")
    linha()
    linha("Gaps conhecidos e seus donos: `docs/04_GAPS_E_RISCOS.md`.")

    alvo = PASTA_QUALITY / "relatorio_qualidade.md"
    alvo.write_text("\n".join(L), encoding="utf-8")
    log(f"relatorio de qualidade -> {alvo.relative_to(alvo.parents[2])}", "ok")
    return resumo
