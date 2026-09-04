# 08 · Especificação funcional do dashboard (v4)

Reescrita em 03/09/2026 para o painel **v4** (D-51: 3 abas e matriz
hierárquica expansível), com as regras de visibilidade (D-54), formatação
(D-55) e o balde de bandeiras por arquivo (D-57). A especificação das versões
anteriores (5 páginas, drill-down, filtros de gerente/projeto/UF, rodapé) está
no histórico do git e nas decisões correspondentes do `docs/12`.

## 1. Filtros globais

Todos derivados **dinamicamente** das dimensões. Nenhuma lista fixa no código ou
no template.

| Filtro | Origem | Tipo | Observação |
|---|---|---|---|
| **Métrica** | fixo | 1 de 3 | Valor R$ · Volume (t) · Caixas |
| **Comparar** (base de comparação) | fixo | **1 de 2** | YTD Fiscal · YTD Calendário. O LY está **embutido**: o período é a seleção de meses e o anterior são os mesmos meses do ano anterior (D-28) |
| **Ver por** (granularidade) | fixo | 1 de 4 | Mês · Trimestre · Semestre · Ano (D-38), na barra de Período |
| **Ano** | `DIM_CALENDARIO.ANO_FISCAL_ROTULO` ou `ANO` | 1 | qual dos dois manda depende de "Comparar"; ver §1.1 |
| **Meses** | `DIM_CALENDARIO` | N | multisseleção + `Todos` / `Nenhum` |
| **Canal** | `DIM_CLIENTE.CANAL` | N | de `bases/Canais/Canais.xlsx`, 100% de cobertura (D-19) |
| **Categoria** | `DIM_PRODUTO.CATEGORIA` | N | |
| **Head** | `DIM_CLIENTE.HEAD` | N | seletor de escopo do **Template Full**; não existe nos arquivos por colaborador (D-52) |
| **Gerente** | perfil do cubo (N2) | N | D-69: vale nas três abas; cascata pelo dado; some no arquivo em que só há uma opção |
| **Sup./Exec.** | perfil do cubo (N3) | N | idem |
| **Vend./RCA** | perfil do cubo (N4) | N | idem; no arquivo de um Sup./Exec. é o único filtro hierárquico visível |

Saíram na D-51 (Q9) e não voltaram: Projeto e UF (o eixo UF saiu dos cubos,
Q10; projeto continua no perfil do cubo, sem filtro na tela). Bandeira e SKU
são dimensões das abas Bandeiras e Categorias, com **busca** própria (D-66).
Gerente, Sup./Exec. e Vend./RCA voltaram na **D-69** como filtros globais: é
como o head vê um subordinado específico em qualquer aba.

### 1.1 Ano fiscal e ano calendário — comportamento declarado

O seletor **Comparar** decide qual calendário manda: com `YTD Fiscal` o chip de
Ano lista anos fiscais (`FY2026` = set/25 a ago/26); com `YTD Calendário`,
anos civis. Nunca os dois filtram ao mesmo tempo: escolher "FY2026" e "2025"
ao mesmo tempo produziria a interseção set–dez/2025, um período que ninguém
pediu. Trocar a base recompõe a lista de anos; nada fica desabilitado.

### 1.2 Regras gerais

* **Combináveis**: todos aplicam em `AND` entre dimensões e em `OR` dentro da
  mesma dimensão.
* **Só valores com dado (D-54, 03/09/2026)**: a lista de cada filtro sai da
  dimensão, e a opção que ficou sem dado no recorte atual **não é exibida**.
  Até a D-51 ela aparecia esmaecida; o esmaecimento saiu com a regra global
  "nada cinza" e a D-54 o substituiu por **esconder**:
  * opção sem dado e sem seleção → some;
  * opção sem dado **já selecionada** → fica, com o contador **"0"** (apagar
    uma seleção do usuário em silêncio é pior que exibir o zero). O "0" é um
    contador, não um estado cinza: o chip mantém cor, contraste e clique;
  * **linha de filtro com menos de duas opções some inteira**: botão sem
    escolha é poluição;
  * a regra vale para Canal, Categoria, Head, Ano, Meses e o "Top" de
    Bandeiras, em **todos** os arquivos (Full, N1, N2, N3), e é decidida pelo
    dado, nunca por lista de nomes.
* **Seleção vazia = sem filtro**, nunca "nenhum dado". Desmarcar tudo em Meses é
  o único caso que zera a tela, e ela diz isso em texto.
* **`✕ Limpar filtros`** aparece quando há filtro de dimensão ativo (D-54);
  sem nada para limpar, a linha sai da tela.
* **Escopo se resolve no dado, não na tela**: o arquivo de um colaborador
  (N1/N2/N3) já nasce sem as dimensões que não existem no escopo dele
  (`filtrar_por_nivel`): não há filtro, link ou parâmetro capaz de trazer de
  volta o que não está no arquivo.
* **Estado visível**: uma linha de status permanente diz o que está ativo, por
  ex.: *"FY2026 · set/25–ago/26 · 3 categorias · 1 head · métrica: Valor R$"*.
* **Título dinâmico**: cada card diz período e base de comparação; o título e o
  cabeçalho do arquivo declaram o recorte por colaborador.
* **Nenhum elemento fica desabilitado ou acinzentado** em estado algum (D-51).
* **Recorte persistente**: o estado dos filtros vai para o hash da URL (`#r=`)
  e para o `localStorage`, serializado por rótulo (nunca por índice); "Copiar
  recorte" compartilha a mesma visão.

---

## 2. Abas

O painel de filtros (com a barra de Período, o "Ver por" e a linha de estado)
existe nas três abas: abaixo do gráfico de Evolução na Visão Geral, no topo nas
demais. Toda navegação entre níveis é pela **expansão da matriz** (▸); não há
drill-down nem "voltar".

### Aba 1 — Visão Geral

* **5 cards de KPI:** Valor R$ · Volume (t) · Caixas · **Fat. médio/mês**
  (`receita ÷ nº de meses`) · Preço Médio R$/kg (**= ticket médio**, D-22).
  Cada um com o valor do período, o LY, a variação absoluta e a **variação %
  com sinal e seta**.
* **Evolução:** barras do período atual à direita e do mesmo período do LY à
  esquerda (ordem cronológica, D-39), com **rótulo de dados** sobre cada barra
  (desenhado à mão no `afterDatasetsDraw`, sem plugin externo: zero rede) e a
  **linha laranja de Δ%** de cada período contra o LY (eixo à direita). Período
  sem par no LY fica **sem a barra clara e sem o ponto de Δ%**, nunca zero. A
  granularidade é o "Ver por"; grupo incompleto sai **(parcial)**.
* **Matriz hierárquica expansível** Head → Gerente → Sup./Exec. → Vend./RCA
  (D-51). Colunas, na ordem da D-67 (igual nas três matrizes e na exportação):
  nome · **ATUAL · ANT. · Δ · Δ% · Part. %** · série de até 12 períodos (na
  granularidade do "Ver por") · TOTAL da série. Agregação por caminho: **o pai é a soma dos
  filhos por construção**. As linhas síntese Σ (`NÃO ATRIBUÍDO`, `INATIVO
  (SANEAMENTO)`, rótulos vindos do config) ficam fora da hierarquia, sem
  expansão, e o **Total geral fecha com os cards**. No arquivo de um
  colaborador a matriz começa no nível dele (N2 → Gerente..., N3 →
  Sup./Exec...) e o N4 é a folha.
* **Ordem dos chips de filtro:** rótulos de ausência (`NÃO ATRIBUÍDO`,
  `NAO INFORMADO`, `SEM CANAL`, `SEM BANDEIRA`) sempre **por último**; o resto
  em ordem alfabética pt-BR. A lista espelha `config → dimensoes.rotulo_*`.

### Aba 2 — Bandeiras

* **▲ Maiores ganhos** e **▼ Maiores quedas** (top 10, por Δ absoluto; a linha
  Σ não entra nos destaques, é agregação, não bandeira).
* **Matriz expansível Bandeira → Categoria.** O arquivo carrega **todas** as
  bandeiras do escopo (D-65); o corte é só de exibição:
  * **Full e N1**: seletor **Top** (10 / 50 / 100 / 200 / 300; só os cortes
    abaixo do universo do recorte, mais o primeiro que o cobre inteiro, D-54).
    As N maiores **do próprio arquivo** aparecem nominalmente; as outras são
    somadas na **linha Σ "DEMAIS BANDEIRAS (N bandeiras)"** montada na tela,
    com a contagem do arquivo. A busca (D-66) acha qualquer bandeira, dentro
    ou fora do corte.
  * **N2 e N3**: todas as bandeiras do escopo, sem Top e sem Σ (config
    `dashboard.exibir_todas_bandeiras_em`).
  * Ganhos e quedas consideram todas as bandeiras do escopo.
* A nota diz de qual universo cada número fala, quanto as nominais cobrem
  **neste recorte** e que o Total geral soma todas, exibidas ou não.

### Aba 3 — Categorias

* **▲ Maiores ganhos** e **▼ Maiores quedas** por categoria.
* **Matriz expansível Categoria → SKU**: todos os SKUs da categoria expandida,
  sem corte de cobertura (lê o `CUBO_SKU`, que desde a D-48 cruza com o mesmo
  perfil comercial do cubo principal e com a bandeira: **nenhum filtro é
  ignorado**). A nota diz quantos SKUs existem no arquivo (400 no Full; menos
  nos arquivos por colaborador, D-54).

### Exportação

Toda tabela tem `↓ CSV` / `↓ XLSX` no cabeçalho do card (D-29), com dado cru
(sem "R$", decimal com ponto), respeitando os filtros; nas matrizes
expansíveis, as **linhas visíveis** na expansão atual. O XLSX é um zip
escrito à mão no JS (zero dependência). Os botões **somem quando a tabela está
vazia** (D-54) e voltam no primeiro render com dado.

---

## 3. Divisão por zero e ausência de dado — na interface

| Situação | Exibição |
|---|---|
| LY zero ou nulo em uma variação % | **`n/d`**, tooltip *"sem base no ano anterior"* |
| Denominador zero no preço médio | **`n/d`** |
| Recorte sem nenhuma linha | *"Sem dados para este recorte"* no lugar do gráfico/tabela; botões de exportação saem |
| Métrica Caixas sem informação na fonte | soma ignora nulos; a ressalva "Caixas é bruta" fica na tela do card |
| Meses do LY parcialmente cobertos | **comparativo desligado (D-35)**: LY, Δ e Δ% do agregado viram `n/d`; a linha de estado diz *"só N de M meses têm par"*. As colunas por período continuam comparando cada grupo com par completo (D-32), e o período parcial leva `*` ou "(parcial)" |
| Célula de matriz com valor zero | `–` (ausência de faturamento, não zero formatado) |

**Nunca** aparece `∞`, `NaN`, `#DIV/0!`, `undefined` ou célula em branco sem
explicação.

---

## 4. Formatação (§12 do prompt; D-55)

| Grandeza | Formato | Exemplo |
|---|---|---|
| Receita | `R$` + abreviação | `R$ 2,3 bi` · `R$ 25 mi` · `R$ 1,5 mi` · `R$ 25 mil` |
| Volume | toneladas | `165,5 mil t` |
| Caixas | caixas | `33,6 mi cx` |
| Preço | `R$ 14,01 /kg` | 2 casas, **nunca abreviado** |
| Percentual | 1 casa + sinal | `+12,4%` · `−3,1%` |
| Negativo | **sinal `−` e cor**, nunca só cor | `−R$ 1,2 mi` |
| Ganho / queda | **seta + sinal + cor** | `▲ +12,4%` · `▼ −3,1%` |

Abreviação (D-55, 03/09/2026): `mil` a partir de 1.000, `mi` a partir de
1.000.000, `bi` a partir de 1.000.000.000, **uma casa decimal, omitida quando
for zero**: `R$ 1 mil`, `R$ 25 mil`, `R$ 1,5 mi`, `R$ 25 mi`, `R$ 1,2 bi`.

**Uma única função formata todo número de métrica** (`abrev`): card, big
number, rótulo de barra, tick de eixo, tooltip, célula de matriz, total,
subtotal e destaque. Não existe segunda escada de arredondamento.

**O prefixo `R$` nunca é literal**: sai da unidade da métrica selecionada, e
por isso **métrica não monetária nunca o recebe**: Volume sai com ` t`,
Caixas com ` cx`, percentual sem nada. A única exceção é o preço médio
(`R$ x,xx /kg`), que não é a métrica selecionada e sim uma razão com moeda
própria (D-22).

**Exportação continua crua**: o CSV/XLSX leva número sem `R$`, sem separador de
milhar e com decimal por ponto. A formatação pt-BR é só de tela.

**Cor nunca é o único indicador.** Toda variação leva seta e sinal, o que também
resolve daltonismo e impressão em preto e branco.

---

## 5. O que a interface declara ao leitor

Não há rodapé textual desde a D-47 (Q3-b) e, desde a **D-70**, não há notas
explicativas sob os cards. O que o painel declara, e onde:

* **título e cabeçalho:** período coberto, execução e, nos arquivos por
  colaborador, o recorte (nível e nome);
* **linha de estado:** métrica, base, período, quantos meses do LY estão
  pareados e os filtros ativos (um só item hierárquico aparece pelo nome);
* **dentro das tabelas:** rótulo da linha Σ com a contagem ("DEMAIS BANDEIRAS
  (N bandeiras)", "Sem estrutura comercial", "Inativos..."), rodapé "Total
  geral (N de M exibidas + síntese)" ou "(busca: N de M)", `*` no cabeçalho
  para período parcial, `n/d` onde não há base, `–` onde não há faturamento.

As regras que as notas antigas explicavam (LY pareado mês a mês e
tudo-ou-nada no agregado, ordenação pelo TOTAL, corte de exibição por
arquivo, Caixas bruta) vivem neste documento e no docs/10.

A ressalva "a camada de SKU não cruza com gerente, bandeira e projeto" **deixou
de existir na D-48**: os dois cubos passaram a ter o mesmo eixo comercial e a
bandeira, e nenhum filtro é ignorado em nenhuma aba. Aviso que não é mais
verdade é pior do que aviso nenhum; um painel que esconde a ressalva faz quem
cruzar com outra fonte concluir que o painel está errado.
