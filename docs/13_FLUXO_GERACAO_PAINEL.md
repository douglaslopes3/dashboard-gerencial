# 13 · Fluxo de geração do painel — ponta a ponta

> Para entender o caminho do dado bruto até o painel publicado **sem ler
> código**. Diagrama navegável em [`fluxo_geracao_painel.html`](fluxo_geracao_painel.html)
> (abre por duplo clique). Estado medido em 26/08/2026.

## O fluxo em uma linha

```
 4 bases Excel ──► run_pipeline.py (6 passos) ──► modelo estrela (Parquet)
                                                       │
                     dashboard/template.html ◄─────────┤ cubos.json + resumo.json
                     + Chart.js embutido               │
                                ▼                      ▼
                     run_dashboard.py ──► dashboard/build/Dashboard_Gerencial_Canais.html
                                          (14,3 MB · um arquivo · abre por duplo clique)
```

---

## 1. Bases de origem — o que entra

| # | Arquivo | Formato | Aba | O que traz | Cadência |
|---|---|---|---|---|---|
| 1 | `bases/Sell In/sellin_*.xlsx` (28 arquivos) e/ou `data/raw/sell_in/*.xlsx` | Excel | `Export` | **o faturamento**: 3.085.119 linhas, mês × cliente × SKU, com Receita Líquida, Peso Líquido (kg) e Qtde Faturado (caixas). Cada arquivo tem um rodapé com a linha `Total` e o texto dos filtros da extração | **diária** (ver doc 14) |
| 2 | `bases/Bases para tabelas dimensões/Produtos.xlsx` | Excel | `Produtos` | cadastro de SKU: código, descrição, **categoria**, **marca** (1.712 SKUs) | estática |
| 3 | `bases/Bases para tabelas dimensões/Hierarquia_Consolidada.xlsx` + `Hierarquia_Complemento.xlsx` (D-34) | Excel | `Planilha1` | estrutura comercial por cliente: **head, gerente, supervisor, projeto** como rótulo `código - papel - nome` (13.448 clientes na oficial + 2.612 no complemento) | estática |
| 4 | `bases/Canais/Canais.xlsx` | Excel | `Export` | **canal e subcanal** por cliente (43.073 clientes; cobre 100% do sell-in) | estática |
| — | `config/config.yaml` + `config/geografia.yaml` | YAML | — | parâmetros: pastas, colunas obrigatórias, ano fiscal (set→ago), tolerâncias, correções declaradas (ex.: Maykon→Vago), cortes de exibição, nomes de UF | muda por decisão |

**O que NÃO entra:** Sell Out (MTRIX/FEMSA/KAN), Metas, Previsão, Estoque e
Alavancas estão na pasta `bases/` mas **nenhum é lido** — fora do escopo deste
painel (são insumo dos Scorecards de canal, projeto vizinho).

---

## 2. ETL — o que cada base sofre

### Sell In (`src/extract/sellin.py`)
1. **Localiza** os arquivos nas duas pastas declaradas no config; rejeita
   qualquer um sem as 12 colunas obrigatórias (aborta, nunca ingere pela metade).
2. **Remove o rodapé**: a linha `Total` vira **gabarito de reconciliação** e o
   texto `Filtros aplicados` é guardado para comparar o recorte entre meses.
3. **Normaliza**: `Ano mês` → `AAAA-MM`; `Cód. cliente`/`Cód. material` → só
   dígitos, **sem zeros à esquerda**; textos com trim/maiúscula; números com
   sinal preservado (devolução é negativa e **fica**); caixas nulas **ficam
   nulas** (não viram zero).
4. **Cache**: cada Excel lido vira um Parquet em `data/staging/` — reexecutar
   sem mudança de arquivo pula a leitura (chave = nome+tamanho+mtime+versão).

### Produtos (`src/extract/cadastros.py`)
Código sem zeros, textos normalizados. **Marca vem do cadastro, nunca é
inferida da descrição.**

### Estrutura comercial (`src/extract/cadastros.py`)
Código zero-preenchido (`0001010846`) → sem zeros (`1010846`) — sem isso o join
casa com **zero** clientes. Correções **declaradas** no config são aplicadas
aqui (hoje: `Maykon - 2600 → Vago - 2600`) e saem no log. Cliente duplicado:
vence a 1ª linha, com aviso; desempate declarável no config.

### Canais (`src/extract/cadastros.py`)
Mesmo tratamento de código; remove o rodapé de filtros; cliente com dois canais
viraria aviso (hoje: zero).

### Derivadas (`src/transform/`)
- `DIM_CALENDARIO`: gerada da amplitude dos meses do sell-in — os **dois
  calendários** (civil e fiscal set→ago) como colunas da mesma tabela, mais o
  pareamento explícito `ANO_MES_LY` (junção, nunca deslocamento).
- `DIM_CLIENTE`: nome/bandeira/UF **mais recentes** do sell-in + head/gerente/
  supervisor/projeto do de-para + canal/subcanal do Canais.xlsx. Quem não está
  num de-para entra **marcado** (`NÃO ATRIBUÍDO` / `SEM CANAL`), nunca descartado.
- `DIM_PRODUTO`: cadastro + os 7 SKUs órfãos adotados do próprio sell-in
  (`FORA_DO_CADASTRO = true`).

---

## 3. Relacionamentos — como as bases se conectam

```
                       DIM_CALENDARIO (24 linhas · PK ANO_MES)
                              │ 1:N
  DIM_PRODUTO ────────── FATO_SELLIN ────────── DIM_CLIENTE
  (494 · PK COD_PRODUTO)  3.085.119 linhas      (16.131 · PK COD_CLIENTE)
        1:N                                          1:N
```

| Ligação | Chave | Cardinalidade | Integridade |
|---|---|---|---|
| Fato → Calendário | `ANO_MES` (`AAAA-MM`) | N:1 — 24 meses | 100%, aborta se quebrar |
| Fato → Cliente | `COD_CLIENTE` (dígitos sem zeros) | N:1 — 16.131 clientes | 100% (a dimensão adota órfãos) |
| Fato → Produto | `COD_PRODUTO` (idem) | N:1 — 494 SKUs | 100% (idem) |
| Cliente → canal/head/gerente/projeto/bandeira/UF | atributos na própria `DIM_CLIENTE` | 1:1 por cliente | coberturas com piso: estrutura 99,98%, canal 100,00% (abaixo de 95% o pipeline aborta) |
| Produto → categoria/marca | atributos na própria `DIM_PRODUTO` | 1:1 por SKU | zero divergência medida entre sell-in e cadastro |

**Grão da fato (declarado e medido):** *uma linha = o faturamento líquido de um
SKU para um cliente em um mês* — zero duplicados em 24 meses. Não há snowflake:
toda dimensão liga direto na fato.

---

## 4. Pipeline — ordem, e o que cada etapa produz

`python run_pipeline.py` — 6 passos, ~2 min a frio / ~20 s com cache, `exit 0`
ou aborta com a causa (nenhum Parquet é atualizado num aborto):

| # | Passo | O que faz | Produz |
|---|---|---|---|
| 1 | **EXTRAIR** | localiza, valida schema, tira rodapé, lê as 4 bases | `data/staging/*.parquet` (cache) |
| 2 | **FATO** | monta a fato, confere o **grão** (zero duplicados) e **reconcilia contra a linha `Total`** de cada arquivo, nas 3 métricas | — |
| 3 | **DIMENSÕES** | calendário, cliente (com canal/estrutura), produto | — |
| 4 | **INTEGRIDADE** | FKs 100% + pisos de cobertura (estrutura ≥95%, canal ≥95%) | — |
| 5 | **AGREGAR** | os 2 cubos (principal 90.644 linhas: mês × bandeira × categoria × perfil × UF; SKU 368.699: mês × SKU × head/canal × UF) e a **reconciliação cubo × fato** — tudo **antes** de qualquer gravação (auditoria A6) | — |
| 6 | **GRAVAR + RELATAR** | o modelo estrela em Parquet; `cubos.json`/`resumo.json` gravados de forma **atômica** e carimbados com a execução (conferida pelo `run_dashboard.py`); relatório de qualidade | `data/curated/DIM_*.parquet`, `FATO_SELLIN/ANO=*/`, `cubos.json`, `resumo.json`, `data/quality/*` |

**Regra de ouro do passo 6:** linha transacional **nunca** chega ao HTML — só
agregado; e camada agregada que não reconcilia com a fato **não é publicada**.

## 5. Publicação — como o painel final nasce

`python run_dashboard.py` (~1 s):

1. Lê `data/curated/cubos.json` e `resumo.json`.
2. Abre `dashboard/template.html` — **a interface inteira vive aqui**, editada à
   mão; nenhuma linha de HTML/CSS/JS nasce em Python.
3. Faz **duas substituições de texto**: injeta o JSON dos cubos entre os
   marcadores de dados e embute o `dashboard/lib/chart.umd.min.js` no marcador
   de biblioteca (cada marcador precisa existir exatamente 1 vez, senão aborta).
4. Grava **`dashboard/build/Dashboard_Gerencial_Canais.html`** — 14,3 MB, um
   arquivo só, **zero requisições de rede**. Abre por duplo clique, inclusive
   em `file://` no OneDrive, sem servidor e sem internet.

O rodapé do painel é gerado nesta etapa a partir do `resumo.json` — nada é
digitado à mão: nº de arquivos, linhas, período, totais, execução e as
ressalvas medidas.

> Distribuição para os heads (SharePoint): plano e decisões em
> [`15_PLANO_SHAREPOINT.md`](15_PLANO_SHAREPOINT.md).
