# 08 · Especificação funcional do dashboard

## 1. Filtros globais

Todos derivados **dinamicamente** das dimensões. Nenhuma lista fixa no código ou
no template.

| Filtro | Origem | Tipo | Observação |
|---|---|---|---|
| **Métrica** | fixo | 1 de 3 | Valor R$ · Volume (t) · Caixas |
| **Granularidade** | fixo | 1 de 3 | Mês · Trimestre · Semestre |
| **Base de comparação** | fixo | **1 de 2** | YTD Fiscal · YTD Calendário — o LY está **embutido**: o período é a seleção de meses e o anterior são os mesmos meses do ano anterior (D-28) |
| **Ano fiscal** | `DIM_CALENDARIO.ANO_FISCAL_ROTULO` | 1 | ver §1.1 |
| **Ano calendário** | `DIM_CALENDARIO.ANO` | 1 | ver §1.1 |
| **Meses** | `DIM_CALENDARIO` | N | multisseleção + `Todos` / `Nenhum` |
| **Canal** | `DIM_CLIENTE.CANAL` | N | de `bases/Canais/Canais.xlsx` — 100% de cobertura (D-19) |
| **Categoria** | `DIM_PRODUTO.CATEGORIA` | N | |
| **Head** | `DIM_CLIENTE.HEAD` | N | inclui `NÃO ATRIBUÍDO` |
| **Gerente** | `DIM_CLIENTE.GERENTE` | N | do de-para de estrutura |
| **Sup./Exec.** | `DIM_CLIENTE.SUPERVISOR` | N | N3 da hierarquia — 56 valores, 99,96% da receita (D-48) |
| **Projeto** | `DIM_CLIENTE.PROJETO` | N | 8 valores do de-para de estrutura (D-25) |
| **UF** | `DIM_CLIENTE.UF` | N | |
| **Bandeira** | `DIM_CLIENTE.BANDEIRA` | busca + N | 11.296 valores: campo de busca, não lista de chips |
| **SKU** | `DIM_PRODUTO` | busca + N | 494 valores |

### 1.1 Ano fiscal e ano calendário usados juntos — comportamento declarado

O seletor de **base de comparação** decide qual dos dois manda:

| Base selecionada | Quem define o período | O outro seletor |
|---|---|---|
| `YTD Fiscal` | **ano fiscal** | fica visível e **desabilitado**, com a nota *"o período segue o ano fiscal"* |
| `YTD Calendário` | **ano calendário** | idem, invertido |


Nunca os dois filtram ao mesmo tempo. Escolher "FY2026" e "2025" ao mesmo tempo
produziria a interseção set–dez/2025 — um período que ninguém pediu e que
ninguém consegue explicar depois.

### 1.2 Regras gerais

* **Combináveis** — todos aplicam em `AND` entre dimensões e em `OR` dentro da
  mesma dimensão.
* **Só valores disponíveis** — a lista de cada filtro sai da dimensão, e a opção
  que ficou sem dado no recorte atual **não é exibida** (D-54, 03/09/2026).
  Até a D-51 ela aparecia **esmaecida**; o esmaecimento saiu com a regra global
  "nada cinza" e, na D-54, foi substituído por **esconder**:
  * opção sem dado e sem seleção → some;
  * opção sem dado **já selecionada** → fica, com o contador **"0"** (apagar
    uma seleção do usuário em silêncio é pior que exibir o zero). O "0" é um
    contador, não um estado cinza: o chip mantém cor, contraste e clique;
  * **linha de filtro com menos de duas opções some inteira** — botão sem
    escolha é poluição;
  * a regra vale para Canal, Categoria, Head, Ano, Meses e o "Top" de
    Bandeiras, em **todos** os níveis (Full, N1, N2, N3), e é decidida pelo
    dado — nunca por lista de nomes.
* **Seleção vazia = sem filtro**, nunca "nenhum dado". Desmarcar tudo em Meses é
  o único caso que zera a tela, e ela diz isso em texto.
* **`✕ Limpar filtros`** aparece quando há filtro de dimensão ativo (D-54);
  sem nada para limpar, a linha sai da tela.
* **Escopo se resolve no dado, não na tela** — o arquivo de um colaborador
  (N1/N2/N3) já nasce sem as dimensões que não existem no escopo dele
  (`filtrar_por_nivel`): não há filtro, link ou parâmetro capaz de trazer de
  volta o que não está no arquivo.
* **Estado visível** — uma linha de status permanente diz o que está ativo, por
  ex.: *"FY2026 · set/25–ago/26 · 3 categorias · 1 head · métrica: Valor R$"*.
* **Título dinâmico** — cada card diz período e base de comparação.

---

## 2. Páginas

### Página 1 — Visão Geral

* **Cards:** Valor R$ · Volume (t) · Caixas · **Faturamento médio/mês**
  (`receita ÷ nº de meses`) · Preço Médio R$/kg (**= ticket médio**, D-22).
  Cada um com o valor do período, o LY, a variação absoluta e a **variação % com
  sinal e seta**.
* **Evolução mensal:** barras do período atual + barras do mesmo período LY
  (28/08/2026 — era linha), com **rótulo de dados** sobre cada barra (desenhado
  à mão no `afterDatasetsDraw`, sem plugin externo — zero rede). Sobre as
  barras, a **linha laranja de Δ%** de cada período contra o mesmo período do
  LY (eixo próprio à direita, rótulo colorido pelo sinal) e a **linha
  tracejada da média do período** (valor declarado na nota do card; para R$
  no mês é o mesmo número do KPI "Faturamento médio/mês"). Período sem par
  no LY fica **sem a barra clara e sem o ponto de Δ%**, nunca zero.
* **Ordem dos chips de filtro:** rótulos de ausência (`NÃO ATRIBUÍDO`,
  `NAO INFORMADO`, `SEM CANAL`, `SEM BANDEIRA`, `SEM UF`) sempre **por
  último**; o resto em ordem alfabética pt-BR. A lista espelha
  `config → dimensoes.rotulo_*` (mesma regra C2 de não deixar divergir).
* **Comparativo YTD:** YTD Fiscal atual × anterior e YTD Calendário atual ×
  anterior, cada um com Δ absoluto e Δ %. **Os dois aparecem sempre**, independente
  da base selecionada — é a comparação que o §11 pede.
* **Detalhamento** com quebra por **Canal**, **Categoria**, **Head**,
  **Gerente**, **Sup./Exec.**, **Projeto** ou **UF**, com colunas:
  `Atual · LY · Δ · Δ% · Participação %`.
* **Drill-down** (Solicitação 02): na quebra por Categoria a linha abre os
  **SKUs da categoria**; na quebra por Head, os **gerentes do head**, e cada
  gerente abre os **Sup./Exec. dele** (D-48) — mesmo período/base/filtros,
  ordenado pela maior queda, com "← voltar" e exportação própria (D-30/D-31).
  A cadeia para em N3 por decisão; o N4 é fase própria.
* **Exportação:** toda tabela tem `⬇ CSV` / `⬇ XLSX` com dado cru (D-29).

### Página 2 — Geografia

* **Performance por UF** — tabela com `Atual · LY · Δ · Δ% · Participação %`,
  ordenável.
* **UF por período** — matriz UF × período, na granularidade selecionada.
* Recortes por categoria, SKU, head e gerente vêm dos **filtros globais**.

### Página 3 — Bandeiras

* **▲ Maiores ganhos** e **▼ Maiores quedas** (top 10, por Δ absoluto).
* Tabela Top 10/50/100/200 com `Atual · LY · Δ · Δ% · Participação %`.

### Página 4 — SKU

* Mesma estrutura da página 3, para `COD_PRODUTO` (Top 25/50/100/todos).

### Página 5 — R$/kg

* Preço médio por Canal / Categoria / Head / Gerente / Projeto / UF, no período.
* Comparativo de preço médio Atual × LY pela dimensão escolhida.
* **O seletor global de métrica não altera a definição do preço** — a página
  declara isso em nota fixa.

---

## 3. Divisão por zero e ausência de dado — na interface

| Situação | Exibição |
|---|---|
| LY zero ou nulo em uma variação % | **`n/d`**, tooltip *"sem base no ano anterior"* |
| Denominador zero no preço médio | **`n/d`** |
| Recorte sem nenhuma linha | *"Sem dados para este recorte"* no lugar do gráfico/tabela |
| Métrica Caixas sem informação na fonte | soma ignora nulos + nota de rodapé com o nº de linhas afetadas |
| Meses do LY parcialmente cobertos | **comparativo desligado (D-35)**: LY, Δ e Δ% do agregado viram `n/d`; a linha de estado diz *"só N de M meses têm par — selecione apenas esses meses"*. As linhas por mês/período continuam comparando cada grupo com par completo (D-32), e o total parcial leva `*` com tooltip |

**Nunca** aparece `∞`, `NaN`, `#DIV/0!`, `undefined` ou célula em branco sem
explicação.

---

## 4. Formatação (§12 do prompt)

| Grandeza | Formato | Exemplo |
|---|---|---|
| Receita | `R$` + abreviação | `R$ 2,3 bi` · `R$ 25 mi` · `R$ 1,5 mi` · `R$ 25 mil` |
| Volume | toneladas | `165,1 mil t` |
| Caixas | caixas | `33,5 mi cx` |
| Preço | `R$ 14,01 /kg` | 2 casas, **nunca abreviado** |
| Percentual | 1 casa + sinal | `+12,4%` · `−3,1%` |
| Negativo | **sinal `−` e cor**, nunca só cor | `−R$ 1,2 mi` |
| Ganho / queda | **seta + sinal + cor** | `▲ +12,4%` · `▼ −3,1%` |

Abreviação (D-55, 03/09/2026): `mil` a partir de 1.000, `mi` a partir de
1.000.000, `bi` a partir de 1.000.000.000, **uma casa decimal, omitida quando
for zero** — `R$ 1 mil`, `R$ 25 mil`, `R$ 1,5 mi`, `R$ 25 mi`, `R$ 1,2 bi`.

**Uma única função formata todo número de métrica** (`abrev`): card, big
number, rótulo de barra, tick de eixo, tooltip, célula de matriz, total,
subtotal e destaque. Não existe segunda escada de arredondamento.

**O prefixo `R$` nunca é literal**: sai da unidade da métrica selecionada, e
por isso **métrica não monetária nunca o recebe** — Volume sai com ` t`,
Caixas com ` cx`, percentual sem nada. A única exceção é o preço médio
(`R$ x,xx /kg`), que não é a métrica selecionada e sim uma razão com moeda
própria (D-22).

**Exportação continua crua**: o CSV/XLSX leva número sem `R$`, sem separador de
milhar e com decimal por ponto. A formatação pt-BR é só de tela.

**Cor nunca é o único indicador.** Toda variação leva seta e sinal, o que também
resolve daltonismo e impressão em preto e branco.

---

## 5. O que a interface declara ao leitor

Rodapé fixo, gerado pelo pipeline (nada digitado à mão):

* período coberto e nº de meses;
* nº de arquivos de origem e nº de linhas;
* data/hora do processamento e `EXECUCAO_ID`;
* **as ressalvas medidas:** Caixas bruta (GAP-04), cobertura de canal e onde
  saem as exceções e o corte de bandeiras (300 + balde).

A ressalva "a camada de SKU não cruza com gerente, bandeira e projeto" **deixou
de existir na D-48**: os dois cubos passaram a ter o mesmo eixo comercial e a
bandeira, e **nenhum filtro é ignorado em nenhuma aba**. Os avisos
correspondentes saíram da tela — aviso que não é mais verdade é pior do que
aviso nenhum.

Um painel que esconde a ressalva faz quem cruzar com outra fonte concluir que o
painel está errado.
