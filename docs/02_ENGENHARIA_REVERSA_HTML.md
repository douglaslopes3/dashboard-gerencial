# 02 · Engenharia reversa funcional do HTML de referência

Arquivo: `Dashboard_Gerencial_Dori.html` · 9,6 MB · `<title>` = "Dashboard Gerencial de Vendas".

## 0. O que o próprio arquivo declara

O rodapé do protótipo diz, com todas as letras:

> `Base 1 + Base 2 + Base 3 · 3.005.227 registros · dados fictícios · valores
> líquidos de devoluções · período set/2024–jul/2026`

**"dados fictícios".** Nenhum número, nenhum array e nenhum cálculo do HTML foi
migrado. O arquivo entra neste projeto como **especificação funcional e
referência visual**, nada mais.

Detalhes técnicos do protótipo (só para contexto): objeto `DB` embutido em
`<script>`, com `months` (23 meses), `dims` (`canal`, `cat`, `uf`, `head`) e um
`cube` posicional `[mês, canal, cat, uf, head, valor, volume]`. Chart.js vem de
CDN — o que o torna inutilizável offline. Ver decisão D-07.

---

## 1. Inventário dos elementos

Legenda da classificação:
**RC** requisito confirmado · **RV** referência visual · **DV** depende de
validação de dados · **FE** fora de escopo · **ME** deve ser melhorado.

### 1.1 Filtros globais

| Elemento do protótipo | Valores | Classe | Observação |
|---|---|:--:|---|
| **Métrica** | `Valor (R$)` · `Volume (t)` | **RC/ME** | o protótipo **não tem Caixas**. O prompt (§6) pede as três — Caixas foi validada na fonte (`01 §1.5`) e **entra** |
| **Período (granularidade)** | `Mês` · `Trimestre` · `Semestre` | **RC** | agregação temporal, ortogonal à base de comparação |
| **Comparar** | `YTD Fiscal (set→)` · `YTD Calendário (jan→)` · `Mês vs mesmo mês LY` | **RC** | idêntico ao §8 do prompt |
| **Meses** (multisseleção + `Todos`/`Nenhum`) | 23 chips | **RC** | vira o seletor de período efetivo |
| **Canal** | 7 valores | **DV → bloqueado** | **não existe na base.** Ver GAP-01 |
| **Categoria** | 11 valores | **RC** | na base são 12 |
| **Head** | 5 valores | **RC** | na base são 4 (`Maykon - 2600` = a vaga) |
| **UF** | 27 valores | **RC** | 27 na base também |
| `✕ Limpar dimensões` + status dos filtros | — | **RC** | exigido pelo §10 do prompt |
| Filtro por **bandeira** e por **SKU** | — | **ME** | o protótipo filtra por essas dimensões só dentro das abas; o §10 pede como filtro global. **Implementado como global** |

### 1.2 Páginas

| Aba do protótipo | Conteúdo | Classe |
|---|---|:--:|
| **Visão Geral** | KPIs · evolução mensal (linha) · "Detalhe por período" com quebra Total/Categoria/Canal/Head · "Comparativo YTD" | **RC** |
| **Geografia** | "Performance YTD por UF" · "UF por período" · comparativo YTD total | **RC** |
| **Bandeiras** | Visão por período / por canal · Top 10/50/100/200 · **maiores ganhos** e **maiores quedas** · tabela de bandeiras | **RC** |
| **SKU** | Top 25/50/100/todos · maiores ganhos e quedas · tabela de SKUs | **RC** |
| **R$/kg** | preço médio por Total/Categoria/Canal/Head + comparativo vs LY | **RC** |

O protótipo tem **5 páginas**; o prompt (§11) descreve **3**. A nota do próprio
prompt reconhece a mistura ("a especificação original mistura os elementos das
páginas 2 e 3"). **Decisão D-01**: prevalece a divisão do HTML (5 páginas),
porque separa ranking de bandeira e de SKU do recorte geográfico — registrada em
`docs/12_REGISTRO_DE_DECISOES.md`.

### 1.3 Cards / KPIs

O protótipo monta os KPIs por JS (`kGeral`), com Valor e Volume. O §11 do prompt
pede **Valor R$, Volume (t), Caixas, Preço Médio e Ticket Médio**.

| KPI | Classe | Situação |
|---|:--:|---|
| Valor R$ | **RC** | implementado |
| Volume (t) | **RC** | implementado (`Peso_KG / 1000`) |
| Caixas | **RC** | implementado — coluna `Qtde Faturado`, validada |
| Preço Médio R$/kg | **RC** | `SUM(Receita) / SUM(Peso_KG)`, razão das somas |
| **Ticket Médio** | **FE** | **não implementado.** Não há definição validada na fonte — ver GAP-02 |

### 1.4 Definição de preço médio — o protótipo acerta

A nota da aba R$/kg diz: *"R$/kg = receita líquida ÷ volume (kg). Independe da
métrica"*. É exatamente a regra do §6 e do §11.3 do prompt: **razão das somas**,
e o seletor global **não** altera a definição. **RC**, mantido.

### 1.5 Identidade visual

**RV.** Aproveitados como referência: tipografia condensada, cards com título
pequeno e nota de rodapé explicativa, chips de filtro (azul = ativo), tabelas
densas com rolagem própria, verde/vermelho para ganho/queda, layout em grade
`2.5fr / 1.3fr`.

**ME — corrigido no projeto novo:** o protótipo usa **só cor** para indicar ganho
e queda. O §12 do prompt proíbe. Na nova interface toda variação leva **sinal
(+/−) e seta (▲/▼)** além da cor.

---

## 2. O que **não** foi trazido do HTML

* nenhum número, série ou total (são fictícios);
* o objeto `DB` e o formato posicional do `cube`;
* os arrays `dims` — as dimensões do projeto novo saem das bases;
* a lista de 7 canais (§9 do prompt manda usá-la só para **validar**, e a
  validação deu negativo — GAP-01);
* o `<script src="https://cdn.jsdelivr.net/...">`: o painel novo embute a
  biblioteca e funciona **offline**, por duplo clique (decisão D-07).

## 3. Um cálculo estar no protótipo não significa que esteja certo

Dois pontos foram conferidos contra a fonte antes de virar requisito:

1. **"valores líquidos de devoluções"** — confere para Valor R$ e Volume. **Não
   confere para Caixas**, que a fonte entrega bruta (`01 §1.5`). O painel novo
   declara isso na tela.
2. **Período `set/2024–jul/2026`** — a base já tem **ago/2026**. O painel novo
   cobre 24 meses, não 23.
