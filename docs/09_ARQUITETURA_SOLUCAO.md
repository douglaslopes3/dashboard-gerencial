# 09 · Arquitetura da solução

```
bases/Sell In/*.xlsx  ─┐
data/raw/sell_in/*.xlsx┤
Produtos.xlsx          ├─► ETL Python ─► Parquet (modelo estrela) ─► agregação ─► Dashboard.html
DePara_Estrutura…xlsx ─┘   src/                data/curated/          data/curated/    dashboard/build/
```

Dois comandos, nada mais:

```
python run_pipeline.py     # bases -> Parquet -> relatorio de qualidade
python run_dashboard.py    # Parquet -> Dashboard.html (e abre)
```

---

## 1. Escolha da tecnologia — decidida pelo ambiente, não por preferência

### 1.1 O que existe na máquina (medido em 26/08/2026)

```
Python        3.14.7
pandas        3.0.5      OK
pyarrow       25.0.1     OK
openpyxl      3.1.5      OK
python-calamine 0.8.2    OK
numpy         2.5.2      OK
PyYAML        6.0.3      OK
duckdb        AUSENTE
streamlit     AUSENTE
plotly        AUSENTE
dash          AUSENTE
polars        AUSENTE
```

### 1.2 As restrições reais

1. **O painel é aberto por duplo clique a partir do OneDrive.** Não há servidor,
   e não há garantia de internet.
2. **Não pode exigir instalação** de quem só consome o painel.
3. **`file://` bloqueia `fetch`/XHR** de arquivo local no navegador — um painel
   que carrega o JSON por rede simplesmente não abre.
4. É o modelo que **já funciona nesta empresa**: os Scorecards de canal são HTML
   autocontidos de ~3,2 MB, e o próprio protótipo de referência é um HTML só.

### 1.3 As opções, comparadas

| Opção | Instalação no consumidor | Abre sem servidor | Offline | Veredito |
|---|---|:--:|:--:|---|
| **HTML estático gerado por Python + Chart.js embutido** | **nenhuma** | **sim** | **sim** | **escolhida** |
| Streamlit | `pip install` + rodar servidor | não | sim | reprovada em 1, 2 e 3 |
| Dash / Plotly | idem | não | sim | idem |
| DuckDB + notebook | `pip install` | não | sim | idem |
| Excel / Power BI | licença | — | — | fora do pedido |

**Decisão D-07:** dashboard é um **HTML autocontido**, gerado pelo Python, com os
dados agregados e a biblioteca de gráfico **embutidos**. Zero requisição de rede.

`Chart.js 4.4.1` foi **copiado** do projeto anterior para
`dashboard/lib/chart.umd.min.js` (200 KB). É a única coisa que veio de lá, e é um
arquivo de biblioteca — o novo projeto não depende do anterior para nada.

> O protótipo de referência carrega o Chart.js de CDN. Isso o torna inutilizável
> sem internet. Corrigido aqui.

---

## 2. Camadas

| Camada | Pasta | Conteúdo | Versionada? |
|---|---|---|---|
| **raw** | `bases/Sell In/`, `data/raw/sell_in/` | Excel de origem, **nunca alterado** | não |
| **staging** | `data/staging/` | cache Parquet de cada Excel lido (chave = nome + tamanho + mtime + `VERSAO_CACHE`) | não |
| **curated** | `data/curated/` | modelo estrela + cubos agregados | não |
| **quality** | `data/quality/` | relatório e CSVs de exceção de cada execução | não |
| **logs** | `logs/` | log completo, um arquivo por execução | não |
| **build** | `dashboard/build/` | `Dashboard.html` | não |

Tudo isso está no `.gitignore`. O repositório guarda **código, config e docs**.

## 3. Os 6 passos do pipeline

| # | Passo | O que faz | Aborta se |
|---:|---|---|---|
| 1 | `extrair` | acha os arquivos, valida formato, colunas obrigatórias e `Ano mês`, tira o rodapé, guarda o gabarito e o texto do filtro | pasta vazia · coluna obrigatória faltando · arquivo ilegível · `Ano mês` não reconhecido · mês partido com recorte idêntico (cópia duplicada) |
| 2 | `fato` | monta a fato, confere o **grão** e **reconcilia** contra a linha `Total` de cada arquivo, nas três métricas | duplicidade no grão · diferença > tolerância |
| 3 | `dimensoes` | `DIM_CALENDARIO`, `DIM_PRODUTO`, `DIM_CLIENTE` | — |
| 4 | `integridade` | FKs 100% + pisos de cobertura (estrutura ≥95%, canal ≥95%) | FK órfã · cobertura abaixo do piso |
| 5 | `agregar` | os dois cubos que o painel consome + reconciliação **cubo × fato** — **antes de qualquer gravação** (auditoria A6) | cubo não bate com a fato |
| 6 | `gravar + relatar` | o modelo estrela em Parquet, `cubos.json`/`resumo.json` **atômicos** (`.tmp` + replace) e carimbados com a execução, e o relatório de qualidade | falha de escrita (mensagem diz o estado real dos artefatos) |

> **Desde 27/08/2026 (auditoria A6):** nada é gravado antes de todas as
> validações; os JSONs são trocados atomicamente e `run_dashboard.py` confere
> que `cubos.json` e `resumo.json` vêm da mesma execução antes de publicar.

Saída: `exit 0` com o resumo, ou `exit 1` com a causa. **Reprocessamento
completo** a cada execução — não há carga incremental, porque não há chave de
controle segura na fonte (a competência vem do conteúdo, não do nome do arquivo).
Idempotente por construção.

## 4. Camada de agregação — dimensionada com medição

O painel **nunca** recebe linha transacional. As 3.081.986 linhas viram dois
cubos. Tamanhos medidos serializando o JSON de verdade:

| Cubo | Grão | Linhas | JSON | Serve |
|---|---|---:|---:|---|
| **`CUBO_PRINCIPAL`** | `ANO_MES × BANDEIRA(300+balde) × CATEGORIA × PERFIL(head, gerente, canal, projeto) × UF` | 90.644 | **~3,2 MB** | páginas 1, 2, 3 e 5 e todos os filtros, menos SKU |
| **`CUBO_SKU`** | `ANO_MES × SKU × (HEAD, CANAL) × UF` | 368.699 | **~11,5 MB** | página 4, o filtro global de SKU e os drills |

Total medido no arquivo gerado (após canal, projeto, exportação e drills):
**14,3 MB** de HTML — dados embutidos + 195 KB de biblioteca. No navegador, o
motor re-agrega os cubos com **índice por mês + memo + render só da aba ativa**
(auditoria B1): render medido em **44 ms** (51 ms com filtro de SKU).

> Os tamanhos das tabelas comparativas abaixo foram medidos em cubos de sondagem,
> antes de o eixo HEAD/GERENTE virar par e antes do balde `DEMAIS`. Servem para
> comparar as **alternativas entre si**; o tamanho do que foi gerado é o de cima.

Referência: o protótipo `Dashboard_Gerencial_Dori.html` tem **9,6 MB**, e os
Scorecards publicados têm 3,2 MB. Está dentro do que a empresa já abre.

### 4.1 Duas decisões de corte, com o número que as sustenta

**(a) Bandeira: as 300 maiores + um balde `DEMAIS`.**
São 11.296 bandeiras. Guardar todas cruzadas com categoria, gerente e UF custaria
muito e entregaria ranking irrelevante. Medido:

| Universo | Cobertura da receita | JSON do cubo cruzado |
|---|---:|---:|
| top 50 | 46,7% | 842 KB |
| top 100 | 57,4% | 1.240 KB |
| top 200 | 68,0% | 1.965 KB |
| **top 300** | **73,4%** | **1.758 KB** |
| top 500 | 78,9% | 3.634 KB |
| top 1000 | 85,2% | 5.721 KB |

Escolhido **300** (o protótipo usava 200 = 68%). As demais 10.996 bandeiras
**não somem**: entram no balde `DEMAIS (10.996 bandeiras)`, então **todo total do
painel continua reconciliando com a fato**. Elas só não aparecem no ranking.
O número está em `config/config.yaml → dashboard.top_bandeiras` — subir para 500
custa +1,9 MB e ganha 5,5 pontos de cobertura.

**(b) SKU cruza com head e UF, não com gerente.**

| Alternativa | JSON | O que o SKU responde |
|---|---:|---|
| `AM × SKU × HEAD` | 442 KB | período, categoria, head |
| `AM × SKU × GERENTE` | 1.045 KB | período, categoria, head, gerente |
| **`AM × SKU × HEAD × UF`** | **4.388 KB** | **período, categoria, head, UF** |
| `AM × SKU × GERENTE × UF` | 7.852 KB | + gerente |

Escolhido `AM × SKU × HEAD × UF`, porque o §11 pede explicitamente **recorte por
SKU na página geográfica**. O que fica de fora: cruzar SKU com **gerente** e com
**bandeira** — a tela avisa quando esses filtros estão ativos.

### 4.2 Reconciliação obrigatória dos cubos

O passo 6 recomputa a soma de cada cubo e compara com a `FATO_SELLIN` nas três
métricas. **Diferença acima da tolerância aborta o pipeline** — camada agregada
que não reconcilia com a fato não é publicada.

## 5. Performance — o que foi feito e o que não foi

| Técnica | Aplicada? | Por quê |
|---|:--:|---|
| Leitura de Excel com `python-calamine` | **sim** | ~10× mais rápido que `openpyxl` neste volume |
| Cache Parquet por arquivo de origem | **sim** | reexecução sem mudança de base pula a leitura do Excel |
| Parquet + seleção só das colunas necessárias | **sim** | |
| Particionamento da fato por `ANO` | **sim** | 3 partições hoje (2024, 2025, 2026); cresce 1 por ano |
| Categorias como `category`/dicionário no Parquet | **sim** | 16.092 clientes e 11.296 bandeiras repetidas |
| Cubos pré-agregados no lugar da fato na interface | **sim** | 3,08 mi de linhas → 280 mil |
| Tabelas do painel paginadas / com rolagem própria | **sim** | |
| Compressão zstd + row groups de 1 Mi | **sim** (auditoria B7) | fato 23,2 → **20,3 MB**; leitura igual |
| Linhagem (`ARQUIVO_ORIGEM`/`EXECUCAO_ID`) como `category` | **sim** (auditoria B3) | fato −41% de RAM; no disco nada muda |
| Motor do painel com índice por mês + memo + aba sob demanda | **sim** (auditoria B1) | ~10 mi → ~1 mi de visitas de linha por clique; 44 ms medidos |
| `DuckDB` | **não** | não está instalado, e o volume não exige: o pipeline inteiro roda em pandas. Reavaliar acima de ~20 mi de linhas |
| Particionar por `ANO_MES` | **não** | 24 partições de ~130 mil linhas — mais arquivo, nenhum ganho medido |
| Cache no navegador / lazy loading por página | **não** | o JSON já está embutido; não há o que carregar sob demanda |

## 6. Estrutura de pastas

```
Dashboard - Gerencial/
├── bases/                        (origem, somente leitura)
├── data/{raw/sell_in,staging,curated,quality}/
├── src/
│   ├── extract/    leitura das fontes, cache, validacao de schema
│   ├── transform/  normalizacao, dimensoes, fato, calendario
│   ├── load/       gravacao em parquet, agregacao dos cubos
│   └── utils/      config, log, texto, numeros
├── dashboard/
│   ├── lib/chart.umd.min.js      (biblioteca embutida)
│   ├── template.html             (interface, editada a mao)
│   └── build/Dashboard.html      (gerado)
├── config/config.yaml
├── docs/  logs/  tests/
├── run_pipeline.py
├── run_dashboard.py
├── requirements.txt
└── README.md
```

**Desvio da estrutura sugerida no §5 do prompt, com justificativa:** o projeto
mora na pasta que já existe (`Dashboard - Gerencial`), em vez de uma
`novo_dashboard_gerencial_dori/` criada ao lado, porque as bases já estão aqui —
criar a subpasta obrigaria a mover 95 MB de Excel ou a apontar para fora do
projeto. A pasta de entrada `data/raw/sell_in/` foi criada como o §1 pede, e o
config aceita **as duas** pastas de entrada. Registrado como decisão D-03.
