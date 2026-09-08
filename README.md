# Dashboard Gerencial de Canais — Sell In

Solução analítica independente para o Sell In da Dori:
**bases brutas → ETL Python → modelo estrela → Parquet → camada agregada → painel HTML.**

Roda **100% local**, sem servidor, sem internet e **sem nenhuma IA**.

```
python run_pipeline.py      # bases -> Parquet -> relatorio de qualidade
python run_dashboard.py     # Parquet -> painel v4 + 72 arquivos por nivel, publicados
```

---

## Estado atual — medido em 08/09/2026 (execucao 20260908-105634; ago/26 fechado + set/26 parcial; metas set+out/26)

```
29 arquivos de Sell In       3.134.928 linhas de fato    25 meses (2024-09 a 2026-09)
receita liquida              R$ 2.329.190.649,47
peso                         165.806,51 t
caixas                       33.658.816
fato                         3.134.928 linhas (linhas 100% zeradas descartadas, D-36)
D-74..D-77 (08/09,           METAS FY27 POR CLIENTE: bases/Metas/Metas_FY'27.xlsx
PUBLICADAS com o ok)         (cliente x categoria x mes, set/26 R$ 122,28 mi e
                             out/26 R$ 119,95 mi) entram como FATO_META e
                             cubo_meta com os MESMOS indices do cubo principal;
                             a meta herda bandeira/hierarquia/canal/RTM pelo
                             join com a DIM_CLIENTE. Na tela: "Meta · Ating."
                             nos cards Valor e Volume, colunas META / ATING. %
                             nas 3 matrizes e barra Meta na Evolucao (com o
                             atingimento), so quando o periodo tem meta.
                             Calendario ate out/26 (26 meses, FY2027). Full
                             19,46 MB (teto subiu para 35 MB, Q7-a), abertura
                             3,7 s, heap 200 MB. 78/78 + 6/6. Decisoes Q1-Q10
                             do Douglas em docs/12 D-74. Na mesma tarde: barra
                             Meta na Evolucao, colunas ano/LY/YTD (D-75), cores
                             opcao A e um eixo so (D-76), percentuais nomeados
                             (D-77) e busca por cliente na aba Bandeiras
                             (D-78). PUBLICADOS em 08/09 com o ok dele (duas
                             vezes: D-74..77 e depois D-78): 73/73 arquivos
                             identicos ao build (MD5); publicacao automatica
                             LIGADA de novo
D-72 (04/09, PUBLICADA       aba Bandeiras abre por CLIENTE (Bandeira >
a noite com o ok)            Cliente > Categoria); cliente e o 5o eixo do cubo
                             principal (730.257 linhas); clientes RTM que
                             herdaram a bandeira viram UMA linha "RTM (soma de
                             N clientes)" sob o distribuidor; bandeira de um
                             cliente so abre direto em categoria. Full 17,6 MB.
                             Os 73 arquivos foram publicados nas pastas em
                             04/09 a noite (MD5 conferido); a publicacao
                             automatica esta LIGADA de novo
ATENCAO (aviso do detector)  3 recortes de extracao na serie: 19 meses ate
                             jul/26, ago/26 ("tipo mercado original") e set/26
                             ("tipo mercado e interno"); ago/26 fechado subiu
                             R$ 7,68 mi sobre o parcial (105,06 -> 112,74 mi).
                             Conferir com o BI qual recorte e o oficial (aberto
                             desde 01/09)
SKUs 400 · categorias 12 · canais 7 · heads 4 · gerentes 13 · Sup./Exec. 55
                             Vend./RCA (N4) 203 (ingerido na D-50)
                             bandeiras 300 nominais (76,7% da receita) + balde
                             de 10.048 (universo 10.348 depois da D-59)
cod. de bandeira (D-42)      13.169 de 16.136 clientes (81,6% · 93,6% da receita),
                             lido da Hierarquia_Consolidada; desde a D-49 e
                             atributo do cadastro, sem funcao de join
HIERARQUIA (D-56, D-61)      Hierarquia_Consolidada e a UNICA fonte (13.516
                             clientes; desempate N4 incorporado na origem em
                             03/09). Editar a base sem os 27 distribuidores
                             derruba a cobertura para 75,40% e o pipeline
                             aborta (aconteceu e foi restaurado em 03/09);
                             ferramentas/diagnostico_cobertura.py explica
METAS (D-49 -> D-74)         o tema Metas antigo (por bandeira, rota A) saiu em
                             02/09 (D-49); voltou em 08/09 (D-74) pela chave do
                             CLIENTE: leitor src/extract/metas.py, FATO_META,
                             cubo_meta, secao 11 do relatorio de qualidade.
                             Negativas (1.034 pares, R$ -96 mil) entram como
                             estao e saem em data/quality/metas_negativas*.csv;
                             revisoes de mes ja carregado em metas_revisoes.csv

BANDEIRA RTM (D-59, 03/09)   o cliente RTM herda tambem a BANDEIRA do
                             distribuidor (`saneamento.rtm_herda_bandeira`):
                             o painel do head de Distribuicao passou de 1.111
                             bandeiras de ponto final para 66 (60 nominais +
                             6 no balde Σ), os distribuidores que sao os
                             clientes dele; efeito zero nos outros 3 heads;
                             universo 11.314 -> 10.348. R$ 82,76 mi (3,56%)
                             trocam de rotulo, nenhum centavo sai do total; a
                             origem fica em DIM_CLIENTE.BANDEIRA_ORIGINAL
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
fora da hierarquia           R$ 54,69 mi (2,35%), 1.053 clientes: 612 inativos
                             + 158 pendentes Q5 + 166 RTM sem distribuidor +
                             117 sem linha em base nenhuma
testes                       68/68 unitarios · 6/6 cenarios ponta a ponta
pipeline                     ~2 min a frio · ~30 s com cache · exit 0
painel (v4, D-51)            17,60 MB (Full) · zero requisicao de rede · 3 ABAS:
                             Visao Geral · Bandeiras · Categorias
                             cubos compactados no arquivo (45,2 MB -> 17,3 MB),
                             SEM o eixo UF (Q10): 517 perfis com N4 · cubo
                             principal 730.257 linhas (todas as bandeiras,
                             D-65; cliente como 5o eixo, D-72) · cubo SKU
                             681.892 (sem bandeira, D-64)
                             arquivos por nivel: Atacado 12,4 MB, Sul/CO 4,4,
                             RS/SC 3,5, Distribuicao 1,3
ABERTURA (D-63, 03/09)       abre no FY corrente ate o ultimo mes fechado; sem
                             mes fechado no FY, abre no FY anterior inteiro
                             (em setembro: set/25 a ago/26, LY 12 de 12)
MATRIZES (D-67, 03/09)       colunas de decisao primeiro: nome · ATUAL · ANT. ·
                             Δ · Δ% · Part. % · serie (ate 12) · TOTAL
BUSCA (D-66, 03/09)          bandeira (aba Bandeiras) e SKU (aba Categorias),
                             sem acento, ignora o corte, fica no recorte
ROTULOS Σ (D-68, 03/09)      "Sem estrutura comercial" e "Inativos (sem sell-in
                             ha 6 meses)" na tela; chave de dado inalterada
FILTRO HIERARQUICO (D-69)    Gerente, Sup./Exec. e Vend./RCA no painel de
                             filtros, valendo nas 3 abas (o head ve um
                             subordinado especifico em Bandeiras/Categorias);
                             so opcoes com dado, cascata, some onde ha 1 opcao.
                             Lista suspensa de escolha unica (decisao 04/09)
SEM RODAPE NOS CARDS (D-70)  as notas explicativas sob grafico e matrizes
                             sairam; contagens ficam na propria tabela
SUP = VENDEDOR (D-71)        Sup./Exec. que e o proprio Vend./RCA (mesma
                             pessoa, pelo nome: 43 dos 203 pares, 37 dos 55
                             sups) nao desce um nivel na matriz nem aparece
                             no filtro de vendedor; flag na posicao 6 do perfil
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
BANDEIRAS (D-64/D-65, 03/09)  o cubo carrega TODAS as bandeiras (sem balde na
                             geracao); cada arquivo leva so as do proprio
                             escopo. Corte so de EXIBICAO: Full e N1 mostram as
                             300 maiores do arquivo + linha Σ montada na tela;
                             N2 e N3 exibem todas. Ganhos/quedas sobre o escopo
                             inteiro. O eixo bandeira saiu do cubo de SKU
                             (morto no v4), e e o que paga a conta
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
publicacao (Q13, D-73)       substituicao automatica na geracao: 72 pastas por
                             usuario + o Full na pasta "Dashboard - Full\" de
                             Paineis Comerciais\Gerencial\ (D-73, 04/09: a
                             raiz daria visibilidade a todas as pastas), com
                             MD5 conferido; o Douglas compartilha cada pasta
                             com o proprio usuario (permissao por heranca;
                             links preservados)
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
Nomes sem sufixo de versão desde a D-58; painéis antigos recolhidos (D-60).
As 72 pastas e a `Dashboard - Full\` (D-73) foram compartilhadas pelo Douglas
em 04/09/2026 à noite.

---

## Operação mensal

1. Largue o arquivo novo de Sell In em `bases\Sell In\` **ou** `data\raw\sell_in\`.
2. `python run_pipeline.py`
3. Confira `data\quality\relatorio_qualidade.md`.
4. `python run_dashboard.py` → abra
   `dashboard\build\Dashboard_Gerencial.html` por **duplo clique**.
   Saem também os **72 arquivos por nível** (`Dashboard_Gerencial_N1_/_N2_/_N3_...`), cada
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
**Bandeiras** (ganhos/quedas + matriz expansível **Bandeira → Cliente →
Categoria** desde a D-72: a bandeira com mais de um cliente abre por CNPJ, a
de um cliente só abre direto em categoria, e os clientes RTM que herdaram a
bandeira do distribuidor aparecem como uma única linha "RTM (soma de N
clientes)"; todas as bandeiras do escopo no arquivo; Full e N1 exibem as N
maiores + linha Σ, N2 e N3 exibem todas; busca por nome) · **Categorias** (ganhos/quedas +
matriz expansível Categoria → SKU, todos os SKUs do escopo; busca por SKU). Toda navegação entre níveis é pela
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

**Filtros globais**: ano fiscal, ano calendário, meses, **canal**,
**categoria**, **Head** (seletor de escopo do Template Full, oculto nos
arquivos por nível) e, desde a D-69, **Gerente, Sup./Exec. e Vend./RCA**,
que valem nas três abas. Projeto e UF saíram na D-51; bandeira e SKU são
dimensões das abas, com busca própria (D-66). Nenhum filtro ou elemento fica
desabilitado ou acinzentado em estado algum — e, desde a **D-54**, um botão só
aparece quando há pelo menos uma linha de dado atrás dele: opção sem dado some
(a que o usuário já selecionou fica com o contador "0"), e a linha do filtro
sai inteira quando não há escolha a fazer. A regra é decidida pelo dado, nunca
por lista de nomes, e vale para Canal, Categoria, Head, Ano, Meses e o "Top"
de Bandeiras, em todos os arquivos (Full, N1, N2 e N3). O painel de filtros (com o
"Ver por" e a linha de estado) existe em todas as abas: abaixo do gráfico
de Evolução na Visão Geral, no topo nas demais.

**Visão por colaborador (N1 a N3)**: além do painel completo, a geração
produz um arquivo por head, por gerente e por Sup./Exec. com o recorte
aplicado no nível de dados (D-52). Os cubos embutidos no arquivo de um
colaborador contêm somente as linhas do escopo dele; não há filtro, link ou
parâmetro capaz de exibir outro escopo, porque o dado não está no arquivo.
Desde a **D-54**, as listas de **canal, categoria e SKU** também encolhem junto
com o perfil (antes elas viajavam do tamanho da empresa inteira, e era por isso
que o painel de um head exibia o chip de um canal sem nenhuma linha dele), e
desde a **D-57** a linha Σ de bandeiras declara a contagem do próprio arquivo.
Título e cabeçalho declaram o recorte (o rodapé textual saiu em D-47); a matriz
começa no nível do colaborador e o filtro Head fica oculto. O N4 não gera
arquivo: é o nível expansível dentro do arquivo do N3. Configuração em
`config/config.yaml → dashboard.por_nivel` e `dashboard.publicacao`.

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
2. **Todas as bandeiras do escopo estão no arquivo** (D-65). No Full e nos
   arquivos por head a tabela exibe as N maiores **daquele arquivo** (seletor
   Top; 300 = 76,7% da receita no Full) e soma as outras na linha Σ montada na
   tela; a busca acha qualquer uma. Gerentes e Sup./Exec. veem todas, sem
   corte. Todo total continua reconciliando com a base.
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
ferramentas/               scripts de medicao e manutencao, fora do pipeline:
                           diagnostico de cobertura (D-61), analise da bandeira
                           RTM (D-59), recolhimento de paineis antigos (D-60);
                           ver ferramentas/LEIA-ME.md
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
| 11 | [Resultado dos testes](docs/11_RESULTADO_DOS_TESTES.md) — T-01 a T-58 |
| 12 | [Registro de decisões](docs/12_REGISTRO_DE_DECISOES.md) — D-01 a D-72, com o porquê (a D-72 vem precedida da análise que a sustentou) |
| 13 | [Fluxo de geração do painel](docs/13_FLUXO_GERACAO_PAINEL.md) — ponta a ponta, sem ler código (+ [diagrama](docs/fluxo_geracao_painel.html)) |
| 14 | [Cadência de atualização](docs/14_CADENCIA_DE_ATUALIZACAO.md) — Sell In diário; estáticas e o que refazer |
| 15 | [Plano SharePoint](docs/15_PLANO_SHAREPOINT.md) — migração, limitações e **decisões em aberto** |
| — | [AUDIT.md](AUDIT.md) — auditoria de 5 camadas com medição; achados, correções (✔) e o que ficou aberto |
| — | [docs/pedidos/](docs/pedidos/) — material pronto para encaminhar ao Comercial e ao BI |

## Roadmap — fechamento de 08/09/2026

**Feito em 08/09 (D-74, publicação DESLIGADA até o ok do Douglas):** análise
da planilha de metas (só leitura, relatório com 10 perguntas) · decisões
Q1–Q10 · leitor de metas por cliente · FATO_META · cubo_meta com os índices
do principal · recorte por nível · teto 35 MB · cards e matrizes com META e
ATING. % · seção 11 do relatório de qualidade · listas de negativas e de
revisões · 9 testes novos · docs 05/06/08/10/11/12.

**Também em 08/09 (D-75):** colunas de decisão renomeadas nas três matrizes:
ATUAL vira o ano selecionado (dinâmico: "FY2027", "FY2027 (2 m.)" ou
"2026"), ANT. vira LY e a última coluna vira "YTD <ano>", que agora soma o
acumulado do ano até o último mês escolhido (antes somava as 12 colunas
exibidas). Ordenação e exportação seguem o YTD.

**Também em 08/09 (D-76):** cores do gráfico de Evolução trocadas pela
opção A validada (LY azul médio, Atual azul Dori, Meta laranja queimado); a
linha de Δ% e o eixo direito saíram, o Δ% virou a segunda linha do rótulo
da barra Atual e entra no tooltip. **D-77:** os percentuais dizem o que são
("Δ LY", "ating.") enquanto cabem na barra; senão viram marcador (▲▼, ◎)
explicado no título do gráfico.

**Próximo passo, por responsável (08/09):**

| Quem | O quê | Quando |
|---|---|---|
| **Douglas** | ~~abrir o build e dar o ok~~ **feito em 08/09 ("Aprovado, pode publicar")**: publicação religada, 73/73 publicados idênticos ao build | feito |
| **Douglas** | analisar `data/quality/metas_negativas_por_bandeira.csv` (Q1): 204 pares bandeira×mês ficam negativos no total da bandeira; decidir se volta ao Comercial | esta semana |
| **Douglas** | aviso de uma linha aos usuários: "o painel agora traz a meta FY27 por cliente" (junto com o aviso pendente da D-72) | na publicação |
| **D-78 (08/09 à tarde, PUBLICADA com o ok)** | busca por cliente na aba Bandeiras: a mesma caixa acha a bandeira pelo rótulo ou por qualquer cliente dela (código ou nome); bandeira achada por cliente abre mostrando só os clientes que casam. 73/73 publicados idênticos ao build | feito |
| **Próxima rodada** (decisão dele) | canal como dimensão; Vendedor × Bandeira | quando ele pedir |

**Feito em 03 e 04/09 (D-54 a D-71, tudo publicado em 04/09 ~00:25):**
visibilidade dinâmica dos botões · formatação única · desempate N4 na origem ·
nomes sem sufixo · RTM herda bandeira · pasta `ferramentas/` · incidente da
cobertura registrado · pedido Q5 gerado · abertura no FY até o último mês
fechado · todas as bandeiras no arquivo com corte só de exibição · busca por
bandeira e SKU · colunas de decisão primeiro · rótulos Σ de leitor · filtro
hierárquico em lista suspensa · sem notas de rodapé · Sup./Exec. que é o
próprio vendedor não desce um nível · docs 08/10/13/14/15 reescritos.

**Próximo passo, por responsável:**

| Quem | O quê | Quando |
|---|---|---|
| **Douglas** | ~~compartilhar as 72 pastas~~ **feito em 04/09/2026 à noite** (P7); a pasta `Dashboard - Full\` também está compartilhada (D-73). Falta o aviso de uma linha aos usuários sobre a abertura por cliente (D-72) | feito |
| **Douglas → Comercial** | enviar `docs/pedidos/pedido_Q5_hierarquia_158.{xlsx,md}` (P8) e cobrar os 117 sem estrutura (P1) | esta semana |
| **Douglas → BI** | confirmar o recorte de extração oficial do Sell In (P9) | esta semana |
| **Próxima rodada do painel** (decisão do Douglas antes de abrir) | cubo de **cliente** só nos arquivos N2/N3 (medido: N3 mediana 4.447 linhas, RS/SC 139.653; inviável no Atacado); quebra por **canal** como dimensão (hoje só filtro); Vendedor × Bandeira para o executivo | quando ele pedir |
| **Operação diária** | `python run_pipeline.py` + `python run_dashboard.py` (publica sozinho); ver docs/10 | todo dia |

## Pendências abertas no encerramento — e de quem dependem

| # | Pendência | Dono | Tamanho medido | Onde está o material |
|---|---|---|---|---|
| P1 | Classificar na `Hierarquia_Consolidada.xlsx` os clientes que faturam e não constam de base nenhuma (117 em 03/09/2026) | **Comercial** | dentro dos R$ 54,69 mi fora da hierarquia | `docs/pedidos/clientes_sem_estrutura.xlsx` (lista viva em `data/quality/clientes_sem_estrutura.csv`) |
| P8 | **Q5**: os **158 clientes** com `Hierarquia = NÃO` e sell-in na janela (100 faturaram em jul/ago/26; 17 são distribuidores) precisam de N1–N4 na hierarquia. Sem decisão em 03/09; pedido gerado | **Comercial** | R$ 36,5 mi hist. · R$ 5,46 mi na janela mar–ago/26 | `docs/pedidos/pedido_Q5_hierarquia_158.xlsx` + `.md` (D-62) |
| P9 | Confirmar qual **recorte de extração** do Sell In é o oficial (3 recortes na série desde ago/26) | **BI** | ago/26: +R$ 7,68 mi entre parcial e fechado | §10 do relatório de qualidade |
| P2 | Reclassificar no `Canais.xlsx` os 3 clientes `KEY ACCOUNT` (R$ 0) e as 2 linhas de P&L (`Orçado/Rateio KR`) | **BI** | impacto zero de receita | `docs/pedidos/clientes_canal_key_account.csv` |
| P3 | `KEY ACCOUNT NACIONAL/REGIONAL` são canais novos ou reclassificação? | **Comercial** | 90 clientes no de-para | GAP-01 / D-27 |
| P4 | Caixas na devolução: pedir `Qtde` negativa ao BI (opção A), estimar pelo fator kg/caixa (B, cobre 98,6%) ou manter bruta (C, atual) | **Douglas decide** + BI | 0,28% das caixas | GAP-04 e a tabela de opções na conversa de 26/08 |
| P5 | 4 SKUs fora do `Produtos.xlsx` (eram 7) | **Cadastro de Produtos** | R$ 1,04 mi (0,04%) | `data/quality/skus_sem_cadastro.csv` |
| P6 | Drill Canal/Projeto → **Cliente** (bloqueios B1/B3: cliente não é dimensão de cubo; embutir multiplica o HTML × carregar sob demanda quebra o "um arquivo") | **Douglas decide** | ver D-30 | docs/12 |
| P7 | ~~Compartilhar as 72 pastas~~ **FEITO em 04/09/2026 à noite pelo Douglas**: as 72 pastas de colaborador e a pasta `Dashboard - Full\` estão compartilhadas; a segregação por pasta está em vigor (a por conteúdo já estava, D-52). Os arquivos publicados são os da D-72 | — | 72 pastas + Full | [docs/15](docs/15_PLANO_SHAREPOINT.md) |
| P10 | **Cliente na aba Bandeiras: FEITO e PUBLICADO na D-72 (04/09 à noite, com o ok do Douglas)**; conferido contra os arquivos anteriores por `ferramentas/comparar_paineis.py`. Falta só o aviso de uma linha aos usuários ("a bandeira agora abre por cliente"). Ficam para a próxima rodada: canal como dimensão, Vendedor × Bandeira | **Douglas** avisa os usuários; decide o resto | ver docs/12 D-72 | docs/12 (proposta + D-72) |
| P11 | ~~Cópia avulsa do Full em `Dashboard - Full\`~~ **Resolvida na D-73** (04/09 à noite): a pasta virou o destino oficial do Full (`publicacao.pasta_full`), porque o Douglas a compartilhou com pessoas que não podem ver as pastas dos colaboradores. A raiz não recebe mais o Full | — | — | docs/12 D-73 |
| P12 | **Metas negativas na planilha FY27** (Q1-a: entram como estão): 1.034 pares, 318 clientes, R$ −96.066; 493 dos 517 pares de set/26 coincidem com realizado negativo no FY26 (rateio herdou devoluções). Em 204 pares bandeira×mês a soma da bandeira inteira fica negativa (102 bandeiras por mês, a pior em R$ −1.777) | **Douglas** analisa; **Comercial** corrige se ele pedir | R$ −96 mil em R$ 242 mi (0,04%) | `data/quality/metas_negativas.csv` e `metas_negativas_por_bandeira.csv` (regenerados a cada execução) |
| P13 | ~~Publicação da D-74 desligada até o ok~~ **FEITA em 08/09/2026**: ok do Douglas, publicação religada, 73/73 arquivos (D-74 a D-77) nas pastas, MD5 igual ao build. Falta o aviso de uma linha aos usuários (meta por cliente no painel + bandeira abre por cliente) | **Douglas** avisa | 73 arquivos | `config/config.yaml → dashboard.publicacao.ativo` |

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
