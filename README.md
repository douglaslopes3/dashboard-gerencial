# Dashboard Gerencial de Canais — Sell In

Solução analítica independente para o Sell In da Dori:
**bases brutas → ETL Python → modelo estrela → Parquet → camada agregada → painel HTML.**

Roda **100% local**, sem servidor, sem internet e **sem nenhuma IA**.

```
python run_pipeline.py      # bases -> Parquet -> relatorio de qualidade
python run_dashboard.py     # Parquet -> Dashboard_Gerencial_Canais.html
```

---

## Estado no encerramento do ciclo — medido em 26/08/2026

```
28 arquivos de Sell In       3.085.119 linhas       24 meses (2024-09 a 2026-08)
receita liquida              R$ 2.260.853.914,86
peso                         161.321,49 t
caixas                       32.659.819
clientes 16.131              SKUs 494               bandeiras 11.296  canais 8

reconciliacao com a fonte    28/28 arquivos, nas 3 metricas
grao                         zero duplicados em 3,08 mi de linhas
cobertura da estrutura       99,98% da receita
cobertura de canal           100,00% da receita
testes                       29/29 unitarios · 6/6 cenarios ponta a ponta
pipeline                     ~2 min a frio · ~20 s com cache · exit 0
fato em disco                20,3 MB (zstd) · JSONs atomicos e carimbados
painel                       14,3 MB · zero requisicao de rede · 5 paginas
                             render 44 ms (motor com indice + memo + aba ativa)
                             exportacao CSV/XLSX em toda tabela
                             drills: Categoria -> SKU · Head -> Gerente
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
o SharePoint: **[docs/15](docs/15_PLANO_SHAREPOINT.md)** — com 5 decisões em
aberto.

---

## Operação mensal

1. Largue o arquivo novo de Sell In em `bases\Sell In\` **ou** `data\raw\sell_in\`.
2. `python run_pipeline.py`
3. Confira `data\quality\relatorio_qualidade.md`.
4. `python run_dashboard.py` → abra `dashboard\build\Dashboard_Gerencial_Canais.html`
   por **duplo clique**.

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
variação % e participação % em toda tabela.

**Exportação CSV/XLSX em todas as tabelas** (dado cru, respeitando os filtros)
e **drill-down**: Categoria → SKUs e Head → Gerentes, ordenados pela maior
queda.

**Filtros globais** derivados das dimensões: ano fiscal, ano calendário, meses,
**canal**, categoria, head, gerente, **projeto**, UF, bandeira e SKU.

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
2. **O ranking de bandeiras é nominal nas 300 maiores** (73,4% do faturamento).
   As outras 10.996 **não somem**: entram agregadas, e todo total continua
   reconciliando com a base.
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
dashboard/{lib,template.html,build/}
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
| 11 | [Resultado dos testes](docs/11_RESULTADO_DOS_TESTES.md) — T-01 a T-25 |
| 12 | [Registro de decisões](docs/12_REGISTRO_DE_DECISOES.md) — 31 decisões, com o porquê |
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
| P7 | As **5 decisões do SharePoint** (D-a a D-e) | **Douglas decide** | — | [docs/15](docs/15_PLANO_SHAREPOINT.md) |

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
