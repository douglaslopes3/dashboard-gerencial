# 07 · Catálogo de métricas

## 1. As três métricas do seletor global

| Métrica | Fórmula | Coluna de origem | Unidade | Sinal | Exclusões |
|---|---|---|---|---|---|
| **Valor R$** | `SUM(RECEITA)` | `Receita Líquida` | R$ | preservado (negativo = devolução) | nenhuma |
| **Volume (t)** | `SUM(PESO_KG) / 1000` | `Peso Líquido` | t (armazenado em kg) | preservado | nenhuma |
| **Caixas** | `SUM(CAIXAS)` | `Qtde Faturado` | caixa | sempre ≥ 0 na fonte | nulos ignorados na soma |

### Valor R$

A fonte entrega **receita líquida** — líquida de devoluções e de impostos sobre
venda, conforme o próprio protótipo declara ("valores líquidos de devoluções").
Nada é excluído: as 79.758 linhas negativas **entram** e reduzem o total, que é o
comportamento correto.

Total de controle (24 meses): **R$ 2.260.853.914,86**.

### Volume (t)

`Peso Líquido` já vem em **kg** na fonte — verificado contra a descrição do SKU:
o peso reconstruído a partir de `Qtde × peso da caixa` difere **1,03%** do peso
real, o que só é compatível com kg.

A divisão por 1000 acontece **na apresentação**, nunca no armazenamento.

Total de controle: **161.321.487,32 kg = 161.321,49 t**.

### Caixas

`Qtde Faturado` **é** a quantidade de caixas — medido, não presumido
(`docs/01_INVENTARIO_FONTES.md §1.5`): a mediana de `Peso ÷ Qtde` por SKU bate
com o peso da caixa da descrição em **277 de 277** SKUs parseáveis, e 98,14% das
linhas caem exatamente nesse valor.

**Nenhum fator de conversão por SKU foi criado.** Nenhum SKU ficou sem fator,
porque não há fator.

> **Ressalva que aparece na tela:** Caixas é **bruta**. 93,7% das linhas de
> devolução têm `Qtde Faturado` nula, e as demais trazem quantidade **positiva**.
> Valor e Volume são líquidos; Caixas não. Desvio medido: **0,28%** (GAP-04).

Total de controle: **32.659.819,49 caixas** (75.956 linhas sem informação).

---

## 2. Preço Médio — R$/kg

```
PRECO_MEDIO = SUM(RECEITA) / SUM(PESO_KG)
```

**Razão das somas. Nunca média simples das linhas.**

| Item | Definição |
|---|---|
| Unidade | **R$/kg** |
| Denominador zero ou nulo | resultado **`null`** → a tela mostra `n/d`, nunca `∞`, `NaN` ou erro |
| Devoluções | **incluídas** nos dois termos — é o preço realizado líquido |
| Efeito do seletor global | **nenhum.** Trocar para Volume ou Caixas **não** altera a definição (§11.3 do prompt) |
| Onde aparece | card da Visão Geral e página inteira "R$/kg" |

Preço médio **não é aditivo**: o preço de um total nunca é a média dos preços das
partes. Toda célula é recalculada como razão das somas **do seu próprio recorte**.

Valor de controle (24 meses, sem filtro): `2.260.853.914,86 / 161.321.487,32`
= **R$ 14,0141 /kg**.

---

## 3. Ticket Médio — **é o Preço Médio** (decisão de 26/08/2026)

A devolutiva definiu: ticket médio e preço médio são **a mesma métrica**
(`Σvalor ÷ Σpeso`). Não existem dois indicadores. O card **"Faturamento
médio/mês"** (`receita ÷ nº de meses do período`) existe à parte, com o rótulo
dizendo exatamente o que a fórmula calcula — ele **não** é ticket médio.
Nenhuma divisão por cliente comprador ou por pedido foi criada (as contagens
não existem no grão). Ver D-22 e o adendo (a descrição da decisão não aparece
na interface, só aqui).

---

## 4. Comparações

Todas valem para **Valor R$, Volume (t) e Caixas**, e todas usam
`DIM_CALENDARIO.ANO_MES_LY` — **junção explícita**, nunca deslocamento posicional.

A base de comparação tem **dois estados** — YTD Fiscal e YTD Calendário — e a
comparação contra o ano anterior está **embutida** (Solicitação 02 / D-28):

| Conceito | Regra |
|---|---|
| **Período atual** | exatamente os meses selecionados nos chips |
| **Período anterior** | os **mesmos meses** do ano anterior, mapeados por `ANO_MES_LY` |
| **Papel da base** | decide qual ano emoldura a lista de meses (fiscal set→ago ou calendário jan→dez) e como o card "Comparativo YTD" acumula |

O intervalo LY é montado mapeando cada `ANO_MES` do período atual pelo seu
`ANO_MES_LY`. **Comparativo pareado (D-32, 27/08/2026):** mês do período atual
sem par no ano anterior fica **fora do comparativo** — não só do denominador.
O "Atual" exibido continua sendo o período inteiro, mas LY, Δ e Δ% comparam
exclusivamente os meses pareados, nos dois lados. Exemplo: ago/25 não tem
ago/24 na série, então não entra em nenhuma comparação; "ano calendário 2025"
mostra os 12 meses no Atual e compara set–dez/25 × set–dez/24. Nas visões por
período (mês/trimestre/semestre), um grupo só tem comparativo quando **todos**
os seus meses têm par. A linha de estado e os totais marcados com `*` declaram
quando o pareamento é parcial.

### 4.1 Variação absoluta

```
DELTA = ATUAL - LY
```

### 4.2 Variação percentual — o comportamento com LY zero está definido

```
VAR_PCT = (ATUAL - LY) / |LY|
```

| Caso do LY | Resultado | O que a tela mostra |
|---|---|---|
| `LY > 0` | número | `+12,4%` |
| `LY = 0` ou nulo | **`null`** | **`n/d`** com tooltip *"sem base no ano anterior"* |
| `LY < 0` (devolução líquida) | usa `\|LY\|` no denominador | valor com a nota *"base LY negativa"* |
| `LY > 0` e `ATUAL = 0` | `-100,0%` | `−100,0%` |

**Nunca é exibido `∞`, `NaN`, `#DIV/0!` ou string vazia.** O divisor em módulo
existe para que uma base negativa não inverta o sinal da variação — que é o erro
clássico dessa conta.

### 4.3 Participação %

```
PARTICIPACAO = METRICA(linha) / METRICA(denominador do contexto)
```

**Filtros preservados e removidos no denominador — declarado por bloco:**

| Bloco | Denominador | Filtros **preservados** | Filtro **removido** |
|---|---|---|---|
| Quebra por categoria (Visão Geral) | total do recorte | período, canal, head, gerente, projeto, UF, bandeira, SKU | **categoria** |
| Quebra por canal / head / gerente / projeto | total do recorte | todos os demais | **a própria dimensão** |
| Tabela de UF (Geografia) | total do recorte | todos os demais | **UF** |
| Tabela de bandeiras | total do recorte | todos os demais | **bandeira** |
| Tabela de SKUs | total do recorte | todos os demais | **SKU** |

**Regra única:** o denominador é o total do recorte **com o filtro da própria
dimensão removido**. Assim a coluna de participação sempre soma 100%, e um
filtro de categoria não faz "AMENDOIM = 100%" parecer um erro.

O denominador é sempre calculado a partir da mesma agregação da tela — nunca de
um total gravado à parte. Por isso é **reconciliável com a fato**.

---

## 5. Rankings — ganhos e quedas

| Parâmetro | Valor | Onde muda |
|---|---|---|
| Critério de ordenação | **variação absoluta** (`ATUAL − LY`) da métrica selecionada | — |
| Ganhos | `DELTA > 0`, decrescente | — |
| Quedas | `DELTA < 0`, crescente | — |
| Quantos | 10 no bloco de destaque | `config/config.yaml → dashboard.top_ranking` |
| Universo das tabelas | Top 10 / 50 / 100 / 200 (bandeira), 25 / 50 / 100 / todos (SKU) | `dashboard.tops_bandeira`, `dashboard.tops_sku` |

**Por variação absoluta, não percentual:** ordenar por % coloca no topo a
bandeira que saiu de R$ 100 para R$ 400 (+300%) na frente da que perdeu R$ 4
milhões. O % continua na tabela, como coluna.

Item que **não existia** no LY entra nos ganhos com `LY = 0` e `VAR_PCT = n/d` —
com o rótulo **"novo"**. Item que sumiu entra nas quedas com `ATUAL = 0` e
`−100%`, com o rótulo **"sem faturamento"**.

---

## 6. Itens sem classificação

| Situação | Rótulo exibido | Por quê |
|---|---|---|
| Cliente sem linha no de-para | `NÃO ATRIBUÍDO` (head/gerente/supervisor) | 71 clientes, R$ 421 mil. Excluir faria o total não bater |
| SKU fora do cadastro | categoria do próprio sell-in; `MARCA` vazia | 7 SKUs, R$ 910 mil |
| Categoria `NAO INFORMADO` na fonte | `NAO INFORMADO` | é o valor de origem, não um preenchimento nosso |

**Nenhum desses vira "Outros" nem some do total.** Todos são contados no
relatório de qualidade.
