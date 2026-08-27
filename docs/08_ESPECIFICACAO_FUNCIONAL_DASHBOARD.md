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
* **Só valores disponíveis** — a lista de cada filtro sai da dimensão, e o chip de
  um valor que ficou sem dado no recorte atual aparece **esmaecido**.
* **Seleção vazia = sem filtro**, nunca "nenhum dado". Desmarcar tudo em Meses é
  o único caso que zera a tela, e ela diz isso em texto.
* **`✕ Limpar filtros`** sempre visível.
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
* **Evolução mensal:** linha do período atual + linha do mesmo período LY, no eixo
  da métrica selecionada, com tooltip trazendo os dois valores e a variação.
* **Comparativo YTD:** YTD Fiscal atual × anterior e YTD Calendário atual ×
  anterior, cada um com Δ absoluto e Δ %. **Os dois aparecem sempre**, independente
  da base selecionada — é a comparação que o §11 pede.
* **Detalhamento** com quebra por **Canal**, **Categoria**, **Head**,
  **Gerente**, **Projeto** ou **UF**, com colunas:
  `Atual · LY · Δ · Δ% · Participação %`.
* **Drill-down** (Solicitação 02): na quebra por Categoria a linha abre os
  **SKUs da categoria**; na quebra por Head, os **gerentes do head** — mesmo
  período/base/filtros, ordenado pela maior queda, com "← voltar" e exportação
  própria (D-30/D-31).
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
| Meses do LY parcialmente cobertos | nota: *"LY cobre N de M meses"* |

**Nunca** aparece `∞`, `NaN`, `#DIV/0!`, `undefined` ou célula em branco sem
explicação.

---

## 4. Formatação (§12 do prompt)

| Grandeza | Formato | Exemplo |
|---|---|---|
| Receita | `R$` + abreviação | `R$ 2,26 bi` · `R$ 106,6 mi` · `R$ 1.234` |
| Volume | toneladas, 1 casa | `161.321,5 t` |
| Caixas | inteiro com separador | `32.659.819` |
| Preço | `R$ 14,01 /kg` | 2 casas |
| Percentual | 1 casa + sinal | `+12,4%` · `−3,1%` |
| Negativo | **sinal `−` e cor**, nunca só cor | `−R$ 1,2 mi` |
| Ganho / queda | **seta + sinal + cor** | `▲ +12,4%` · `▼ −3,1%` |

Abreviação: `mil` a partir de 1.000, `mi` a partir de 1.000.000, `bi` a partir de
1.000.000.000 — **consistente em toda a interface**.

**Cor nunca é o único indicador.** Toda variação leva seta e sinal, o que também
resolve daltonismo e impressão em preto e branco.

---

## 5. O que a interface declara ao leitor

Rodapé fixo, gerado pelo pipeline (nada digitado à mão):

* período coberto e nº de meses;
* nº de arquivos de origem e nº de linhas;
* data/hora do processamento e `EXECUCAO_ID`;
* **as ressalvas medidas:** Caixas bruta (GAP-04), cobertura de canal e onde
  saem as exceções, corte de bandeiras (300 + balde) e o que a camada de SKU
  não cruza (gerente, bandeira, projeto).

Um painel que esconde a ressalva faz quem cruzar com outra fonte concluir que o
painel está errado.
