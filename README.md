# Dashboard Gerencial de Canais — Sell In

Solução analítica independente para o Sell In da Dori:
**bases brutas → ETL Python → modelo estrela → Parquet → camada agregada → painel HTML.**

Roda **100% local**, sem servidor, sem internet e **sem nenhuma IA**.

```
python run_pipeline.py      # bases -> Parquet -> relatorio de qualidade
python run_dashboard.py     # Parquet -> painel v4 + 72 arquivos por nivel, publicados
```

---

## Estado atual — medido em 02/09/2026 (ago/26 fechado + set/26 parcial)

```
29 arquivos de Sell In       3.121.445 linhas de origem   25 meses (2024-09 a 2026-09)
receita liquida              R$ 2.318.751.361,89
peso                         165.122,14 t
caixas                       33.516.211
fato                         3.117.999 linhas (3.446 100% zeradas descartadas, D-36)
ATENCAO (aviso do detector)  ago/26 e set/26 vieram com RECORTE de extracao
                             diferente dos 19 meses anteriores ("tipo mercado
                             original", sem excluir "diversos") - ago/26 fechado
                             subiu R$ 7,68 mi sobre o parcial (105,06 -> 112,74 mi);
                             conferir com o BI se o recorte novo e o oficial
SKUs 400 · categorias 12 · canais 7 · heads 4 · gerentes 13 · Sup./Exec. 55
                             Vend./RCA (N4) 204 (ingerido na D-50)
                              bandeiras 300 nominais + balde de 10.989
cod. de bandeira (D-42)      13.101 de 16.122 clientes (81,3% · 93,5% da receita),
                             lido da Hierarquia_Consolidada; desde a D-49 e
                             atributo do cadastro, sem funcao de join
METAS REMOVIDAS (D-49)       o tema Metas saiu inteiro do produto em 02/09/2026
                             (leitor D-43, CUBO_META/aba D-44, meta na Evolucao
                             D-45, bloco Meta x Realizado D-47): havera novo
                             arquivo de metas cruzado pela chave do cliente —
                             ponto de reintegracao em docs/12 (D-49);
                             bases/Metas/ fica intocada

RTM (D-50, Step 4)           1.596 clientes migrados para distribuidor: o
                             sell-in deles (historico e futuro) carrega a
                             hierarquia e o canal do DISTRIBUIDOR (R$ 82,62 mi
                             entram no canal Distribuidor; bandeira/UF
                             preservadas — Q4-a); 166 SEM distribuidor
                             identificado ficam fora da hierarquia (R$ 6,47 mi,
                             lista de excecao, pendencia do Comercial)
saneamento (D-50, Step 5)    janela 2026-03..2026-08 (ultima competencia
                             fechada, parametro): 612 inativados no balde
                             "INATIVO (SANEAMENTO)" — fora da matriz, historico
                             permanece nos totais (Q7-i); 158 HIERARQUIA=NAO
                             COM sell-in na janela aguardam decisao (Q5, lista)
reconciliacao com a fonte    29/29 arquivos, nas 3 metricas
grao                         zero duplicados
cobertura da estrutura       97,65% da receita (piso 95% restaurado na D-50)
cobertura de canal           100,00% da receita
fora da hierarquia           R$ 54,55 mi (2,35%): inativos + pendentes Q5 +
                             RTM sem distribuidor + 71 antigos sem estrutura
testes                       43/43 unitarios · 6/6 cenarios ponta a ponta
pipeline                     ~2 min a frio · ~25 s com cache · exit 0
painel (v4, D-51)            11,35 MB · zero requisicao de rede · 3 ABAS:
                             Visao Geral · Bandeiras · Categorias
                             cubos compactados no arquivo (30,8 MB -> 11,1 MB),
                             SEM o eixo UF (Q10): 516 perfis com N4 · cubo
                             principal 124.493 linhas · cubo SKU 866.562
                             MATRIZ HIERARQUICA EXPANSIVEL na Visao Geral
                             (Head > Gerente > Sup./Exec. > Vend./RCA; linhas
                             sintese Σ para fora-da-hierarquia) · Bandeiras
                             expande p/ Categoria · Categorias expande p/ SKU
                             filtros: Metrica, Comparar, Ano, Meses, Canal,
                             Categoria e Head (escopo do Template Full)
                             granularidade Mes|Trimestre|Semestre|Ano ("Ver
                             por") · periodo parcial declarado · exportacao
                             CSV/XLSX (matrizes: linhas visiveis) · NENHUM
                             elemento desabilitado/acinzentado em estado algum
VISIBILIDADE (D-54, 03/09)   botao so aparece com pelo menos UMA linha de dado
                             atras dele: opcao sem dado some (a ja selecionada
                             fica com o contador "0"), linha de filtro com
                             menos de 2 opcoes some inteira, ↓CSV/↓XLSX saem
                             com a tabela vazia. Decidido pelo cubo, sem lista
                             de nomes. Vale para Full, N1, N2 e N3
BALDE DE BANDEIRAS (D-57)    a linha Σ declara quantas bandeiras ela agrega
                             NAQUELE arquivo (antes repetia o numero global em
                             todos os 73); o CORTE das 300 maiores segue global
                             e a tela diz isso
FORMATACAO (D-55, 03/09)     uma funcao formata todo numero de metrica:
                             mil/mi/bi com 1 casa, omitida quando zero —
                             R$ 1 mil · R$ 25 mil · R$ 1,5 mi · R$ 1,2 bi. O
                             "R$" sai da metrica ativa, entao Volume (t) e
                             Caixas (cx) nunca o recebem
                             template_v3 fica como retorno rapido (exige o
                             pipeline pre-D-51, via git)
por nivel (D-52)             73 arquivos: Full + 4 N1 + 13 N2 + 55 N3, recorte
                             FISICO na geracao (o arquivo de um nivel nao
                             contem dados de fora do escopo; assert por
                             arquivo); a matriz de cada arquivo comeca no
                             proprio nivel (N2 -> Gerente..., N3 -> Sup./Exec...)
                             o N4 nao gera arquivo (decisao 02/09); baldes
                             fora-da-hierarquia tambem nao; particionamento
                             reconciliado nos 3 niveis, ao centavo
publicacao (Q13)             substituicao automatica na geracao: 72 pastas por
                             usuario + o Full na raiz de Paineis Comerciais\
                             Gerencial\, com MD5 conferido; o Douglas
                             compartilha cada pasta com o proprio usuario
                             (permissao por heranca; links preservados)
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
o SharePoint: **[docs/15](docs/15_PLANO_SHAREPOINT.md)** — decidido e
executado em 02/09/2026 (D-52/Q13): pasta por usuário em `Documentos\Painéis
Comerciais\Gerencial\`, publicação por substituição na própria geração.
Pendente do Douglas: compartilhar as 72 pastas e apagar os v3 antigos da raiz.

---

## Operação mensal

1. Largue o arquivo novo de Sell In em `bases\Sell In\` **ou** `data\raw\sell_in\`.
2. `python run_pipeline.py`
3. Confira `data\quality\relatorio_qualidade.md`.
4. `python run_dashboard.py` → abra
   `dashboard\build\Dashboard_Gerencial_Canais_v4.html` por **duplo clique**.
   Saem também os **72 arquivos por nível** (`..._v4_N1_/_N2_/_N3_...`), cada
   um contendo apenas os dados do próprio escopo — e a geração já **publica
   substituindo** nas pastas por usuário de `Painéis Comerciais\Gerencial\`
   (D-52/Q13; `dashboard.publicacao.ativo: false` desliga). Regra de
   distribuição: cada colaborador recebe só a própria pasta.

Nenhuma edição de código em nenhuma etapa. Detalhes e mensagens de erro em
**[docs/10_GUIA_OPERACIONAL.md](docs/10_GUIA_OPERACIONAL.md)**.

## Instalação

```bash
pip install -r requirements.txt
```

Python 3.11+ (validado em 3.14.7). Cinco dependências, todas já presentes na
máquina de destino.

---

## O que o painel entrega (v4, D-51)

**3 abas** — **Visão Geral** (5 cards de KPI, gráfico de Evolução e a
**matriz hierárquica expansível** Head → Gerente → Sup./Exec. → Vend./RCA) ·
**Bandeiras** (ganhos/quedas + matriz expansível Bandeira → Categoria, top N
nominais + balde Σ) · **Categorias** (ganhos/quedas + matriz expansível
Categoria → SKU, todos os 400 SKUs). Toda navegação entre níveis é pela
**expansão da matriz** — o drill-down deixou de existir. As linhas síntese Σ
(sem estrutura, inativos do saneamento) ficam fora da hierarquia com o
histórico preservado no Total geral, que fecha com os cards.

**3 métricas** no seletor global — **Valor R$**, **Volume (t)**, **Caixas** —
e **Preço Médio R$/kg** no card da Visão Geral, calculado sempre como
`SUM(receita) / SUM(peso_kg)`
(razão das somas; o seletor global **não** altera essa definição).

**Uma única formatação de valor** (D-55): a métrica selecionada decide o
prefixo, e ele aparece em **todo** indicador — card, rótulo de barra, eixo,
tooltip, célula de matriz, total e destaque. Escala `mil`/`mi`/`bi` com uma
casa decimal, omitida quando for zero: `R$ 1 mil`, `R$ 25 mil`, `R$ 1,5 mi`,
`R$ 1,2 bi`. **Métrica não monetária nunca recebe R$** — Volume sai em ` t` e
Caixas em ` cx`. A exportação CSV/XLSX continua levando número cru.

**2 bases de comparação** — YTD Fiscal (set→ago) e YTD Calendário (jan→dez),
com a comparação contra o mesmo período do ano anterior **embutida** (o período
é a seleção de meses; o anterior são os mesmos meses do LY). Variação absoluta,
variação % e participação % em toda tabela. No gráfico de Evolução, as barras
seguem a ordem cronológica: ano anterior à esquerda, atual à direita.

**4 granularidades** no seletor **Ver por** da barra de Período: Mês, Trimestre,
Semestre e Ano. Mesma tela e mesma conta nos quatro modos; muda só o
agrupamento das colunas/barras e os rótulos. Grupo com menos meses que a
granularidade pede sai marcado **(parcial)**, nunca como período cheio.

**Exportação CSV/XLSX em todas as tabelas** (dado cru, respeitando os
filtros; nas matrizes expansíveis, as linhas visíveis na expansão atual).

**Filtros globais** (D-51): ano fiscal, ano calendário, meses, **canal**,
**categoria** e **Head** — este último é o seletor de escopo do Template
Full e fica oculto nos arquivos por nível. Gerente, Sup./Exec., projeto, UF
e as buscas de bandeira/SKU saíram: a navegação hierárquica é a matriz, e
bandeira/SKU seguem como dimensões nas abas. Nenhum filtro ou elemento fica
desabilitado ou acinzentado em estado algum — e, desde a **D-54**, um botão só
aparece quando há pelo menos uma linha de dado atrás dele: opção sem dado some
(a que o usuário já selecionou fica com o contador "0"), e a linha do filtro
sai inteira quando não há escolha a fazer. A regra é decidida pelo dado, nunca
por lista de nomes, e vale para Head, Gerente, Supervisor e Executivo. O painel de filtros (com o
"Ver por" e a linha de estado) existe em todas as abas: abaixo do gráfico
de Evolução na Visão Geral, no topo nas demais.

**Visão por head**: além do painel completo, a geração produz um arquivo por
head com o recorte aplicado no nível de dados. Os cubos embutidos no arquivo de
um head contêm somente as linhas do squad dele; não há filtro, link ou
parâmetro capaz de exibir outro squad, porque o dado não está no arquivo.
Desde a **D-54**, as listas de **canal, categoria e SKU** também encolhem junto
com o perfil — antes elas viajavam do tamanho da empresa inteira, e era por isso
que o painel de um head exibia o chip de um canal sem nenhuma linha dele.
Título e cabeçalho declaram a restrição (o rodapé textual saiu em D-47); o
filtro Head fica oculto — componente preservado, visibilidade por perfil.
Configuração em `config/config.yaml → dashboard.por_head`.

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
   medido em 01/09/2026; na tela do v4 a cobertura é recalculada sob o recorte
   ativo). As outras 10.989 **não somem**: entram agregadas, e todo total
   continua reconciliando com a base.
3. ~~**A camada de SKU cruza com head, canal, categoria e UF — não com
   gerente, bandeira nem projeto.**~~ **Resolvido em 02/09/2026 (D-48):** o
   cubo de SKU passou a carregar o mesmo perfil comercial do cubo principal
   (head, gerente, **Sup./Exec.**, canal, projeto) mais a bandeira. **Nenhum
   filtro é ignorado em nenhuma aba** — e o painel ficou menor, porque os
   cubos passaram a viajar compactados.

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
bases/                     origem (somente leitura): Sell In, Canais,
                           dimensões, RTM-Transicao, Metas
data/{raw,staging,curated,quality}/
src/{extract,transform,load,utils}/
dashboard/{lib,template_v4.html,build/}   (template_v3.html: retorno rapido)
config/{config.yaml,geografia.yaml}
docs/  logs/  tests/
run_pipeline.py  run_dashboard.py
_arquivo/                  fora de uso (D-53): bases fora do escopo, protótipo,
                           templates v1/v2, backups pré-fases — nada lido pelo
                           pipeline; ver _arquivo/LEIA-ME.md
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
| 12 | [Registro de decisões](docs/12_REGISTRO_DE_DECISOES.md) — D-01 a D-57, com o porquê |
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
