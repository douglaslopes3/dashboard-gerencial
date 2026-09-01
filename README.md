# Dashboard Gerencial de Canais — Sell In

Solução analítica independente para o Sell In da Dori:
**bases brutas → ETL Python → modelo estrela → Parquet → camada agregada → painel HTML.**

Roda **100% local**, sem servidor, sem internet e **sem nenhuma IA**.

```
python run_pipeline.py      # bases -> Parquet -> relatorio de qualidade
python run_dashboard.py     # Parquet -> painel v3 + um arquivo por head
```

---

## Estado atual — medido em 01/09/2026

```
28 arquivos de Sell In       3.114.298 linhas de origem   24 meses (2024-09 a 2026-08)
receita liquida              R$ 2.309.797.874,70
peso                         164.510,21 t
caixas                       33.384.067
fato                         3.110.907 linhas (3.391 100% zeradas descartadas, D-36;
                             T-36 corrigiu o registro: o descarte estava subtraido
                             duas vezes no texto anterior)
SKUs 400 · categorias 12 · canais 7 · heads 4 · bandeiras 300 nominais + balde de 10.989
cod. de bandeira (D-42)      13.101 de 16.122 clientes (81,3% · 93,5% da receita),
                             lido da Hierarquia_Consolidada: ponte por codigo com a
                             base de metas FY 26/27
FATO_META (D-43)             meta set/26 ingerida de bases/Metas: 3.282 linhas ·
                             R$ 122.279.463,48 · 7.824,5 t, reconciliada ao centavo
                             com a linha Total do proprio arquivo; 73,3% do R$ casa
                             por codigo + 0,7% por nome (sem par: baldes do Atacado
                             + 3 codigos novos, pedidos ao Comercial abertos)
aba Metas (D-44, rota A)     CUBO_META cruzado na geracao (2.547 linhas, 54 grupos,
                             257 bandeiras, reconciliado): Meta x Realizado x ano
                             anterior por head/gerente/executivo/bandeira/categoria
                             no painel completo e nos 4 arquivos por head; o
                             realizado da bandeira nomeada segue o dono DECLARADO
                             na meta (rota A); mes sem sell-in aparece como n/d,
                             nunca zero

reconciliacao com a fonte    28/28 arquivos, nas 3 metricas
grao                         zero duplicados
cobertura da estrutura       99,96% da receita
cobertura de canal           100,00% da receita
testes                       37/37 unitarios · 6/6 cenarios ponta a ponta
pipeline                     ~2 min a frio · ~20 s com cache · exit 0
painel (v3)                  14,5 MB · zero requisicao de rede · 6 paginas (aba Metas)
                             granularidade Mes|Trimestre|Semestre|Ano ("Ver por"),
                             periodo parcial declarado, filtros em todas as abas
                             exportacao CSV/XLSX em toda tabela
                             drills: Categoria -> SKU · Head -> Gerente
por head                     4 arquivos restritos (1,7 a 7,5 MB), recorte fisico
                             na geracao: o arquivo de um head nao contem os
                             dados dos outros squads
```

**Auditoria completa** (26–27/08, cinco camadas, tudo medido): [`AUDIT.md`](AUDIT.md)
— zero dado errado armazenado; correções aplicadas em duas levas (D-33). Abertos
por decisão: A8 (SCD/estrutura vigente — Comercial), B2 (OneDrive) e B9 (corte
do cubo de SKU).

O caminho do dado bruto ao painel, sem ler código:
**[docs/13_FLUXO_GERACAO_PAINEL.md](docs/13_FLUXO_GERACAO_PAINEL.md)** (diagrama
em [docs/fluxo_geracao_painel.html](docs/fluxo_geracao_painel.html)). Cadência
de atualização (Sell In diário; o resto estático):
**[docs/14](docs/14_CADENCIA_DE_ATUALIZACAO.md)**. Saída do ambiente de IA para
o SharePoint: **[docs/15](docs/15_PLANO_SHAREPOINT.md)**. Primeiro passo
executado em 01/09/2026 (painéis publicados em `Documentos\Painéis
Comerciais\Gerencial\`, permissões pendentes com o Douglas); as 5 decisões
D-a a D-e seguem em aberto.

---

## Operação mensal

1. Largue o arquivo novo de Sell In em `bases\Sell In\` **ou** `data\raw\sell_in\`.
2. `python run_pipeline.py`
3. Confira `data\quality\relatorio_qualidade.md`.
4. `python run_dashboard.py` → abra
   `dashboard\build\Dashboard_Gerencial_Canais_v3.html` por **duplo clique**.
   Saem também os 4 arquivos `..._v3_HEAD_<head>.html`, um por head, cada um
   contendo apenas os dados do próprio squad. Regra de distribuição: cada head
   recebe só o seu.

Nenhuma edição de código em nenhuma etapa. Detalhes e mensagens de erro em
**[docs/10_GUIA_OPERACIONAL.md](docs/10_GUIA_OPERACIONAL.md)**.

## Instalação

```bash
pip install -r requirements.txt
```

Python 3.11+ (validado em 3.14.7). Cinco dependências, todas já presentes na
máquina de destino.

---

## O que o painel entrega

**5 páginas** — Visão Geral · Geografia · Bandeiras · SKU · R$/kg.

**3 métricas** no seletor global — **Valor R$**, **Volume (t)**, **Caixas** —
e **Preço Médio R$/kg**, calculado sempre como `SUM(receita) / SUM(peso_kg)`
(razão das somas; o seletor global **não** altera essa definição).

**2 bases de comparação** — YTD Fiscal (set→ago) e YTD Calendário (jan→dez),
com a comparação contra o mesmo período do ano anterior **embutida** (o período
é a seleção de meses; o anterior são os mesmos meses do LY). Variação absoluta,
variação % e participação % em toda tabela. No gráfico de Evolução, as barras
seguem a ordem cronológica: ano anterior à esquerda, atual à direita.

**4 granularidades** no seletor **Ver por** da barra de Período: Mês, Trimestre,
Semestre e Ano. Mesma tela e mesma conta nos quatro modos; muda só o
agrupamento das colunas/barras e os rótulos. Grupo com menos meses que a
granularidade pede sai marcado **(parcial)**, nunca como período cheio.

**Exportação CSV/XLSX em todas as tabelas** (dado cru, respeitando os filtros)
e **drill-down**: Categoria → SKUs e Head → Gerentes, ordenados pela maior
queda.

**Filtros globais** derivados das dimensões: ano fiscal, ano calendário, meses,
**canal**, categoria, head, gerente, **projeto**, UF, bandeira e SKU. O painel
de filtros (com a barra de Período e a linha de estado) existe em todas as
abas: abaixo do gráfico de Evolução na Visão Geral, no topo nas demais.

**Visão por head**: além do painel completo, a geração produz um arquivo por
head com o recorte aplicado no nível de dados. Os cubos embutidos no arquivo de
um head contêm somente as linhas do squad dele; não há filtro, link ou
parâmetro capaz de exibir outro squad, porque o dado não está no arquivo.
Título, cabeçalho e rodapé declaram a restrição. Configuração em
`config/config.yaml → dashboard.por_head`.

---

## Resolvido na devolutiva de 26/08/2026

| Item | Como ficou |
|---|---|
| **Canal** | integrado de `bases/Canais/Canais.xlsx` — **100,0000%** dos clientes e da receita, zero órfãos. Filtro e quebra em todas as páginas (D-19) |
| **Ticket Médio** | **= preço médio** (`Σvalor ÷ Σpeso`) por decisão — não são indicadores distintos. O card "Faturamento médio/mês" (`receita ÷ nº meses`) chama o que a fórmula calcula (D-22) |
| **Head vago** | `Maykon - 2600` → `Vago - 2600`, declarado no config e registrado no log; total geral inalterado (D-23) |
| **Projeto** | dimensão de primeira classe (coluna `PROJETO` do de-para de estrutura, 8 valores): filtro + quebra em todas as páginas (D-25) |

### Três ressalvas que o painel declara na própria tela

1. **Caixas é métrica bruta.** Valor e Volume são líquidos de devolução; Caixas
   não — 93,7% das linhas de devolução não têm quantidade na origem. Desvio
   medido: **0,28%**.
2. **O ranking de bandeiras é nominal nas 300 maiores** (73,7% do faturamento,
   medido em 01/09/2026; na tela do v3 a cobertura é recalculada sob o recorte
   ativo). As outras 10.989 **não somem**: entram agregadas, e todo total
   continua reconciliando com a base.
3. **A camada de SKU cruza com head, canal, categoria e UF — não com gerente,
   bandeira nem projeto.** Quando esses filtros ficam ativos junto com um filtro
   de SKU, a tela avisa em vez de fingir que aplicou.

---

## Regras que o projeto segue

**Fonte única da verdade.** Nada é inventado. Divergência não é corrigida em
silêncio: correção de rótulo é **declarada em `config/config.yaml`** e sai
registrada no log e no relatório de qualidade.

**Zero hardcode de negócio.** Não há lista fixa de canal, categoria, head, UF,
bandeira, cliente, SKU, período ou ano em lugar nenhum do código. A lista em
`validacao.valores_esperados` é **só gabarito de conferência** — não filtra, não
corrige e não ordena.

**Nada é descartado para o número fechar.** Os 71 clientes sem head e os 7 SKUs
fora do cadastro entram no fato, marcados, e saem listados em `data/quality/`.

**Nenhuma camada agregada é publicada sem reconciliar com a fato.** O pipeline
aborta se não fechar.

**Sem carga incremental.** Reprocessamento completo, idempotente. A competência
vem do **conteúdo**, nunca do nome do arquivo.

---

## Estrutura

```
bases/                     origem (somente leitura)
data/{raw,staging,curated,quality}/
src/{extract,transform,load,utils}/
dashboard/{lib,template_v3.html,build/}   (template.html e template_v2.html: retorno rapido)
config/{config.yaml,geografia.yaml}
docs/  logs/  tests/
run_pipeline.py  run_dashboard.py
```

## Documentação

| # | Documento |
|---|---|
| 01 | [Inventário das fontes](docs/01_INVENTARIO_FONTES.md) — o que cada base tem, medido |
| 02 | [Engenharia reversa do HTML](docs/02_ENGENHARIA_REVERSA_HTML.md) — o protótipo, item a item |
| 03 | [Matriz de reaproveitamento do ETL](docs/03_MATRIZ_REAPROVEITAMENTO_ETL.md) — o que veio do projeto anterior |
| 04 | [Gaps e riscos](docs/04_GAPS_E_RISCOS.md) — **o que pedir, a quem, e quanto custa** |
| 05 | [Dicionário de dados](docs/05_DICIONARIO_DADOS.md) |
| 06 | [Modelo estrela](docs/06_MODELO_ESTRELA.md) — o grão, declarado |
| 07 | [Catálogo de métricas](docs/07_CATALOGO_METRICAS.md) |
| 08 | [Especificação funcional](docs/08_ESPECIFICACAO_FUNCIONAL_DASHBOARD.md) |
| 09 | [Arquitetura](docs/09_ARQUITETURA_SOLUCAO.md) — escolha de tecnologia e cortes, com medida |
| 10 | [Guia operacional](docs/10_GUIA_OPERACIONAL.md) — **comece por aqui para operar** |
| 11 | [Resultado dos testes](docs/11_RESULTADO_DOS_TESTES.md) — T-01 a T-35 |
| 12 | [Registro de decisões](docs/12_REGISTRO_DE_DECISOES.md) — 41 decisões, com o porquê |
| 13 | [Fluxo de geração do painel](docs/13_FLUXO_GERACAO_PAINEL.md) — ponta a ponta, sem ler código (+ [diagrama](docs/fluxo_geracao_painel.html)) |
| 14 | [Cadência de atualização](docs/14_CADENCIA_DE_ATUALIZACAO.md) — Sell In diário; estáticas e o que refazer |
| 15 | [Plano SharePoint](docs/15_PLANO_SHAREPOINT.md) — migração, limitações e **decisões em aberto** |
| — | [AUDIT.md](AUDIT.md) — auditoria de 5 camadas com medição; achados, correções (✔) e o que ficou aberto |
| — | [docs/pedidos/](docs/pedidos/) — material pronto para encaminhar ao Comercial e ao BI |

## Pendências abertas no encerramento — e de quem dependem

| # | Pendência | Dono | Tamanho medido | Onde está o material |
|---|---|---|---|---|
| P1 | Colar os **71 clientes sem estrutura** no DePara (head `Vago - 2600` já preenchido; falta gerente/supervisor) | **Comercial** | R$ 421 mil (0,02%) | `docs/pedidos/incluir_no_DePara_estrutura.xlsx` |
| P2 | Reclassificar no `Canais.xlsx` os 3 clientes `KEY ACCOUNT` (R$ 0) e as 2 linhas de P&L (`Orçado/Rateio KR`) | **BI** | impacto zero de receita | `docs/pedidos/clientes_canal_key_account.csv` |
| P3 | `KEY ACCOUNT NACIONAL/REGIONAL` são canais novos ou reclassificação? | **Comercial** | 90 clientes no de-para | GAP-01 / D-27 |
| P4 | Caixas na devolução: pedir `Qtde` negativa ao BI (opção A), estimar pelo fator kg/caixa (B, cobre 98,6%) ou manter bruta (C, atual) | **Douglas decide** + BI | 0,28% das caixas | GAP-04 e a tabela de opções na conversa de 26/08 |
| P5 | 7 SKUs fora do `Produtos.xlsx` | **Cadastro de Produtos** | R$ 910 mil (0,04%) | `data/quality/skus_sem_cadastro.csv` |
| P6 | Drill Canal/Projeto → **Cliente** (bloqueios B1/B3: cliente não é dimensão de cubo; embutir multiplica o HTML × carregar sob demanda quebra o "um arquivo") | **Douglas decide** | ver D-30 | docs/12 |
| P7 | As **5 decisões do SharePoint** (D-a a D-e). Primeiro passo já executado em 01/09/2026: painéis publicados em `Painéis Comerciais\Gerencial\`; **falta o Douglas configurar as permissões** (cada `_HEAD_` só para o próprio head) | **Douglas decide** | — | [docs/15](docs/15_PLANO_SHAREPOINT.md) |

---

## Isolamento do projeto anterior

`Documentos\Dashboards - Heads - Canais` foi tratado como **somente leitura**:
nada foi escrito, movido, renomeado, apagado ou executado lá (conferido: **0
arquivos modificados**).

O que veio de lá: componentes de ETL **copiados e adaptados** (normalização de
tipos, calendário fiscal, cache de leitura, reconciliação contra o gabarito da
fonte, injeção de dados no template) e uma **cópia** de `chart.umd.min.js`.
Tudo documentado, componente a componente, em
[docs/03](docs/03_MATRIZ_REAPROVEITAMENTO_ETL.md).

**Nenhum import, config, Parquet ou caminho absoluto do projeto anterior existe
aqui.** Apagar o projeto anterior não afeta nada — verificado em
[docs/11, T-14](docs/11_RESULTADO_DOS_TESTES.md).
