# Dashboard Gerencial de Canais — Sell In

Solução analítica independente para o Sell In da Dori:
**bases brutas → ETL Python → modelo estrela → Parquet → camada agregada → painel HTML.**

Roda **100% local**, sem servidor, sem internet e **sem nenhuma IA**.

```
python run_pipeline.py      # bases -> Parquet -> relatorio de qualidade
python run_dashboard.py     # Parquet -> Dashboard_Gerencial_Canais.html
```

---

## Estado atual — medido em 26/08/2026

```
28 arquivos de Sell In       3.085.119 linhas       24 meses (2024-09 a 2026-08)
receita liquida              R$ 2.260.853.914,86
peso                         161.321,49 t
caixas                       32.659.819
clientes 16.131              SKUs 494               bandeiras 11.296

reconciliacao com a fonte    28/28 arquivos, nas 3 metricas
grao                         zero duplicados em 3,08 mi de linhas
cobertura da estrutura       99,98% da receita
testes                       24/24 unitarios · 6/6 cenarios ponta a ponta
pipeline                     107s a frio · 13s com cache · exit 0
painel                       8,94 MB · zero requisicao de rede
```

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

**3 bases de comparação** — YTD Fiscal (set→ago), YTD Calendário (jan→dez) e
Meses vs mesmo período do ano anterior. Variação absoluta, variação % e
participação % em toda tabela.

**Filtros globais** derivados das dimensões: ano fiscal, ano calendário, meses,
categoria, head, gerente, UF, bandeira e SKU.

---

## O que o painel **não** entrega, e por quê

| Ausência | Motivo | Dono | Doc |
|---|---|---|---|
| **Filtro/quebra por canal** | nenhuma base entregue traz canal ou subcanal | **BI / Cadastro de Clientes** | GAP-01 |
| **Ticket Médio** | sem definição validada na fonte (não há pedido nem nota no grão) | **Comercial / Controladoria** | GAP-02 |

Nenhum dos dois foi inventado, estimado ou preenchido com "NÃO INFORMADO".
As opções para resolver o canal, com **o tamanho medido de cada uma**, estão em
**[docs/04_GAPS_E_RISCOS.md](docs/04_GAPS_E_RISCOS.md)**.

### Três ressalvas que o painel declara na própria tela

1. **Caixas é métrica bruta.** Valor e Volume são líquidos de devolução; Caixas
   não — 93,7% das linhas de devolução não têm quantidade na origem. Desvio
   medido: **0,28%**.
2. **O ranking de bandeiras é nominal nas 300 maiores** (73,4% do faturamento).
   As outras 10.996 **não somem**: entram agregadas, e todo total continua
   reconciliando com a base.
3. **A camada de SKU cruza com head e UF, não com gerente nem bandeira.** Quando
   esses filtros ficam ativos junto com um filtro de SKU, a tela avisa em vez de
   fingir que aplicou.

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
src/{extract,transform,load,models,utils}/
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
| 11 | [Resultado dos testes](docs/11_RESULTADO_DOS_TESTES.md) |
| 12 | [Registro de decisões](docs/12_REGISTRO_DE_DECISOES.md) — 18 decisões, com o porquê |

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
