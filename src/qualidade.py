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

from .transform import fato as fato_mod
from .utils.config import CFG, PASTA_QUALITY
from .utils.log import EXECUCAO_ID, log

_ESPERADOS = CFG["validacao"]["valores_esperados"]
# C2 (auditoria): os rotulos de ausencia vem do config — as MESMAS strings que
# as dimensoes gravam, nunca uma copia local.
_SEM_CANAL = CFG["dimensoes"]["rotulo_sem_canal"]
_SEM_BANDEIRA = CFG["dimensoes"]["rotulo_sem_bandeira"]
_SEM_ESTRUTURA = CFG["dimensoes"]["rotulo_sem_estrutura"]
_ROT_INATIVO = CFG["dimensoes"].get("rotulo_inativo")


def _nome_base(v) -> str:
    """Rotulo completo normalizado para comparar com a lista esperada.

    Com a Hierarquia_Consolidada (D-34) o rotulo de head e
    'codigo - papel - nome' ('20 - ATACADO - ADEMIR TAVARES'), entao a lista
    esperada guarda o rotulo INTEIRO e a comparacao e igualdade total —
    fatiar no ' - ' (convencao da base anterior) pegaria so o codigo.
    C6 (auditoria) continua valendo: igualdade, nunca prefixo.
    """
    return str(v).strip().casefold()


def _csv(df: pd.DataFrame, nome: str) -> None:
    PASTA_QUALITY.mkdir(parents=True, exist_ok=True)
    df.to_csv(PASTA_QUALITY / nome, index=False, encoding="utf-8-sig", sep=";")


def _fmt(x: float, casas: int = 2) -> str:
    return f"{x:,.{casas}f}".replace(",", "@").replace(".", ",").replace("@", ".")


def gerar(fato: pd.DataFrame, dim_cliente: pd.DataFrame,
          dim_produto: pd.DataFrame, dim_cal: pd.DataFrame,
          meta: dict, cobertura_head: float, cobertura_canal: float,
          pacote_cubo: dict, avisos: list[str],
          saneamento: dict | None = None) -> dict:
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
    zer = meta.get("linhas_zeradas") or {}
    if zer:
        det = ", ".join(f"`{a}` ({n})" for a, n in sorted(zer.items()))
        linha(f"- **Linhas 100% zeradas descartadas (D-36):** "
              f"{sum(zer.values()):,} em {len(zer)} arquivo(s) — {det}. "
              "Receita, peso e caixas zerados/nulos; somam R$ 0,00 e não "
              "alteram a reconciliação")
    else:
        linha("- **Linhas 100% zeradas descartadas (D-36):** 0")
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
    # C5 (auditoria): o grao e o do fato.py — nao uma copia local da chave.
    dup = int(fato.duplicated(fato_mod.GRAO).sum())
    linha(f"- Duplicados no grão `{' × '.join(fato_mod.GRAO)}`: "
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
        # C5: a mesma funcao que o passo de integridade usa para abortar.
        orfaos = fato_mod.contar_orfaos(fato, dim, coluna)
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
    # Rotulos DECLARADOS de ausencia/inativo nao sao "valores estranhos" —
    # mesmo tratamento que o canal ja dava ao rotulo_sem_canal.
    head_real = set(dim_cliente["HEAD"].dropna()) - {_SEM_ESTRUTURA,
                                                     _ROT_INATIVO}
    esperados_head = {str(e).casefold() for e in _ESPERADOS.get("head", [])}
    for v in sorted(head_real):
        # C6: igualdade do rotulo completo (casefold), nunca prefixo — um head
        # novo parecido com um esperado deve aparecer aqui, nao passar batido.
        if _nome_base(v) not in esperados_head:
            n = int((dim_cliente["HEAD"] == v).sum())
            nao_rec.append({"DIMENSAO": "HEAD", "VALOR": v, "SKUS": n})
    canal_real = set(dim_cliente["CANAL"].dropna()) - {_SEM_CANAL}
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
          f"**{int((dim_cliente['BANDEIRA'] == _SEM_BANDEIRA).sum()):,}**")
    linha()
    linha("> Nenhum deles é descartado. Descartar faria o total do painel deixar "
          "de bater com o total da fonte.")
    linha()
    resumo["clientes_sem_estrutura"] = len(sem_est)
    resumo["clientes_sem_canal"] = len(sem_canal)
    resumo["skus_sem_cadastro"] = len(sem_cad)

    # -------------------------------------- 7b. reestruturacao (D-50)
    # Os DOIS lados da reatribuicao RTM quantificados + o saneamento 5.2.
    if saneamento and "ORIGEM_RTM" in dim_cliente.columns:
        san = saneamento
        rec_total = float(fato["RECEITA"].sum())

        def _receita_de(cods) -> float:
            return float(fato.loc[fato["COD_CLIENTE"].isin(set(cods)),
                                  "RECEITA"].sum())

        linha("## 7b. Reestruturação (D-50): RTM e saneamento da hierarquia")
        linha()
        rtm_ok = dim_cliente[dim_cliente["ORIGEM_RTM"]
                             & dim_cliente["COD_DISTRIBUIDOR"].notna()]
        rtm_sem = dim_cliente[dim_cliente["ORIGEM_RTM"]
                              & dim_cliente["COD_DISTRIBUIDOR"].isna()]
        rec_ok = _receita_de(rtm_ok["COD_CLIENTE"])
        rec_sem = _receita_de(rtm_sem["COD_CLIENTE"])
        # D-59 (03/09/2026): o texto declara a regra de bandeira que RODOU,
        # lida das medidas do saneamento — nunca um texto fixo.
        if "rtm_bandeira_herdada" in san:
            regra_ban = (f"bandeira do distribuidor herdada por "
                         f"{san['rtm_bandeira_herdada']:,} deles, a de origem "
                         "fica em BANDEIRA_ORIGINAL (D-59); UF preservada")
        else:
            regra_ban = "bandeira/UF preservadas (Q4-a; `rtm_herda_bandeira` desligado)"
        linha(f"- **RTM reatribuídos:** {len(rtm_ok):,} clientes · receita "
              f"histórica **R$ {_fmt(rec_ok)}** ({rec_ok / max(rec_total, 1):.2%}) "
              f"**entra** na hierarquia e no canal de "
              f"{san.get('rtm_distribuidores', 0)} distribuidores (o mesmo "
              f"valor **sai** do balde sem estrutura; {regra_ban})")
        if len(rtm_ok):
            por_dist = (fato[fato["COD_CLIENTE"].isin(set(rtm_ok["COD_CLIENTE"]))]
                        .merge(rtm_ok[["COD_CLIENTE", "DISTRIBUIDOR"]],
                               on="COD_CLIENTE")
                        .groupby("DISTRIBUIDOR")["RECEITA"].sum()
                        .sort_values(ascending=False))
            linha()
            linha("| Distribuidor (destino) | Receita histórica que entra R$ |")
            linha("|---|---:|")
            for nome_d, v in por_dist.items():
                linha(f"| {nome_d} | {_fmt(float(v))} |")
            linha()
        linha(f"- **RTM sem distribuidor identificado:** {len(rtm_sem):,} "
              f"clientes · **R$ {_fmt(rec_sem)}** — ficam FORA da hierarquia, "
              "canal original mantido, pendência do Comercial "
              "(`rtm_sem_distribuidor.csv`)")
        _csv(rtm_sem[["COD_CLIENTE", "NOME_CLIENTE", "BANDEIRA", "UF",
                      "DISTRIBUIDOR", "CANAL"]], "rtm_sem_distribuidor.csv")

        inat = dim_cliente[dim_cliente["INATIVO"]]
        pend = dim_cliente[dim_cliente["SANEAMENTO_PENDENTE"]]
        rec_inat = _receita_de(inat["COD_CLIENTE"])
        rec_pend = _receita_de(pend["COD_CLIENTE"])
        jan = san.get("janela") or []
        jtxt = f"{jan[0]}..{jan[-1]}" if jan else "?"
        linha(f"- **Inativados pelo saneamento (5.2):** {len(inat):,} clientes "
              f"(HIERARQUIA=NÃO e sem sell-in em {jtxt}) · receita histórica "
              f"**R$ {_fmt(rec_inat)}** — fora da matriz hierárquica no balde "
              "próprio; o histórico permanece em TODOS os totais (Q7-i) "
              "(`saneamento_inativados.csv`)")
        _csv(inat[["COD_CLIENTE", "NOME_CLIENTE", "BANDEIRA", "UF", "CANAL",
                   "MOTIVO_INATIVO", "DATA_INATIVACAO"]],
             "saneamento_inativados.csv")
        linha(f"- **Caso NÃO coberto (Q5, aguarda decisão):** {len(pend):,} "
              f"clientes com HIERARQUIA=NÃO **e** sell-in na janela · receita "
              f"histórica **R$ {_fmt(rec_pend)}** — nenhuma regra aplicada, "
              "seguem sem estrutura (`saneamento_pendentes_decisao.csv`)")
        _csv(pend[["COD_CLIENTE", "NOME_CLIENTE", "BANDEIRA", "UF", "CANAL"]],
             "saneamento_pendentes_decisao.csv")
        if san.get("sim_pendentes"):
            linha(f"- **HIERARQUIA=SIM ainda sem vínculo na Consolidada:** "
                  f"{san['sim_pendentes']:,} — pendência do Comercial; nada "
                  "foi inferido")
        if san.get("conflito_rtm_saneamento"):
            linha(f"- **Conflito RTM × Faltando:** "
                  f"{san['conflito_rtm_saneamento']:,} cliente(s) nas duas "
                  "bases — valeu a regra RTM (5.4)")
        linha()
        resumo["rtm_reatribuidos"] = len(rtm_ok)
        resumo["rtm_sem_distribuidor"] = len(rtm_sem)
        resumo["inativados"] = len(inat)
        resumo["saneamento_pendentes"] = len(pend)

    # ------------------------------------------------------------- 8. cubos
    corte = pacote_cubo["corte_bandeira"]
    linha("## 8. Camada agregada")
    linha()
    linha(f"- `CUBO_PRINCIPAL`: **{len(pacote_cubo['cubo']):,}** linhas")
    linha(f"- `CUBO_SKU`: **{len(pacote_cubo['cubo_sku']):,}** linhas")
    # D-65: o cubo carrega TODAS as bandeiras; o corte e so de exibicao.
    linha(f"- Bandeiras no cubo: **{corte['universo']:,}** (todas). Corte de "
          f"exibição no Full e nos arquivos N1: as **{corte['top']:,}** maiores "
          f"de cada arquivo nominalmente (no Full cobrem "
          f"**{corte['cobertura_top_full']:.1%}** da receita), o resto na linha "
          f"Σ `{corte['rotulo_base']}` montada na tela; N2 e N3 exibem todas")
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
