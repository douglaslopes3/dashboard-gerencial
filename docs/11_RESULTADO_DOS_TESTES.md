# 11 · Resultado dos testes

Executado em **26/08/2026**. Todo número abaixo veio de uma execução real; nada
foi estimado. Onde a saída é longa, o comando que a produz está indicado.

## Resumo

| Bateria | Comando | Resultado |
|---|---|---|
| Regras críticas (unitário) | `python tests/test_regras.py` | **26 de 26** |
| Cenários de ponta a ponta | `python tests/cenarios.py` | **6 de 6** |
| Reconciliação painel × fato | ver T-04 | **bate até o centavo** |
| Interface (filtros, LY, YTD, métrica) | ver T-11 a T-13 | **ok** |
| Independência e ausência de IA | ver T-14 e T-15 | **ok** |
| Segunda onda (canal, projeto, Vago, ticket) | ver T-16 a T-21 | **ok** |

---

## T-01 · Arquivos atuais — o pipeline roda ponta a ponta

```
python run_pipeline.py
```

```
arquivos lidos ......... 28
linhas da fato ......... 3.085.119
periodo ................ 2024-09 a 2026-08  (24 meses)
receita ................ R$ 2.260.853.914,86
peso ................... 161.321,49 t
caixas ................. 32.659.819
clientes ............... 16.131
SKUs ................... 494
cobertura da estrutura . 99,98%
avisos ................. 2
tempo total ............ 107,4s  (13,4s com o cache quente)
exit code .............. 0
```

Os dois avisos são os gaps já conhecidos e documentados: 71 clientes sem head e
7 SKUs fora do cadastro. Nenhum deles é descartado.

## T-02 · Reconciliação contra a origem — 28 de 28 arquivos, 3 métricas

Soma da fato × linha `Total` de cada arquivo:

```
maior |diferenca| receita   R$ 0,0000073
maior |diferenca| peso         0,0000020 kg
maior |diferenca| qtde         0,00000000023 cx
```

O passo aborta com `exit 1` se qualquer arquivo estourar a tolerância — provado
em **T-10**.

## T-03 · Integridade referencial e grão

```
grao ANO_MES x COD_CLIENTE x COD_PRODUTO: zero duplicados em 3.085.119 linhas
FK COD_PRODUTO    -> DIM_PRODUTO      ok
FK COD_CLIENTE    -> DIM_CLIENTE      ok
FK ANO_MES        -> DIM_CALENDARIO   ok
cobertura da estrutura sobre a receita: 99,98% (piso 95%)
cubos reconciliados com a FATO_SELLIN nas 3 metricas
```

## T-04 · Reconciliação painel × fato — o teste que vale por todos

Números lidos **do painel em execução no navegador** (via console) e comparados
com a `FATO_SELLIN` lida em pandas.

| Recorte | Fato | Painel | Erro relativo |
|---|---:|---:|---:|
| FY2026 receita | 1.127.251.765,810 | 1.127.251.765,810 | **0** |
| FY2026 peso (kg) | 76.262.628,713 | 76.262.628,713 | **0** |
| FY2026 caixas | 15.948.764,584 | 15.948.764,590 | 3,8e-10 |
| FY2025 receita | 1.133.602.149,048 | 1.133.602.148,980 | 6,0e-11 |
| FY2025 peso (kg) | 85.058.858,608 | 85.058.858,608 | **0** |
| FY2025 caixas | 16.711.054,903 | 16.711.054,900 | 1,8e-10 |
| Geral receita | 2.260.853.914,858 | 2.260.853.914,790 | 3,0e-11 |
| Geral peso (kg) | 161.321.487,321 | 161.321.487,321 | 1,8e-16 |
| Geral caixas | 32.659.819,487 | 32.659.819,490 | 9,2e-11 |

**Quebra por categoria (FY2026, receita) — 12 de 12 categorias com diferença
exatamente `0,0000`:**

```
AMENDOIM 394.246.625,41 · GOMAS 240.856.993,48 · BALA 163.791.044,27
GRANULADO 79.265.889,77 · REGALIZ 57.173.576,93 · CHOCOLATE 54.687.646,96
COMPOUND 51.228.518,61 · GELATINA 43.115.792,41 · PIRULITO 25.409.562,67
JUBES FRUIT SNACKS 17.472.656,81 · NAO INFORMADO 26.774,94
DISPLAY/MAT.PROMOCIONAL −23.316,45
soma = 1.127.251.765,81  (identica ao total da fato)
```

**Quebra por head (FY2026, receita) — 5 de 5 com diferença `0,0000`:**

```
Ademir 440.020.838,54 · Michel - 1000 280.061.405,26
Maykon - 2600 232.432.409,99 · Izabela - 2650 174.320.340,18
NÃO ATRIBUÍDO 416.771,84
soma = 1.127.251.765,81
```

**Somas dos três cubos, dentro do painel, sobre o mesmo período:**

```
soma por bandeira (300 + balde)  dif = -9,5e-7 R$   em 1,13 bi
soma por UF (27)                 dif = +2,4e-7 R$
soma por SKU (352 no periodo)    dif = +2,6e-6 R$
```

As diferenças residuais são de ordem de soma em ponto flutuante — 6 casas
decimais abaixo do centavo.

## T-05 · Inclusão de uma nova base de Sell In

Arquivo de teste com um mês novo (`2026/09`, R$ 1.000,00) largado em
`data/raw/sell_in/`:

```
exit 0 · o mes 2026-09 entrou na serie
receita total: R$ 2.260.853.914,86 -> R$ 2.260.854.914,86  (+R$ 1.000,00 exatos)
```

Nenhuma linha de código foi tocada. **O arquivo de teste foi apagado** e o
pipeline reexecutado com as bases reais.

## T-06 · Reprocessamento (idempotência)

Duas execuções seguidas, sem mudar nada nas bases:

```
4 tabelas conferidas (DIM_CALENDARIO, DIM_CLIENTE, DIM_PRODUTO, FATO_SELLIN)
linhas, colunas e as 3 somas: IDENTICAS
exit 0 nas duas
```

## T-07 · Duplicidade

Mesmo `mês × cliente × SKU` em dois arquivos:

```
exit 1
1 linha(s) fora do grao declarado.
  O grao da fonte e ANO_MES x COD_CLIENTE x COD_PRODUTO e foi medido
  como unico em 24 meses. Duplicidade aqui significa arquivo
  reextraido ou mes duplicado na pasta de entrada.
  Exemplos (chave -> arquivos):
    ('2026-09', '1000021', '9012876') -> ['..dup_a.xlsx', '..dup_b.xlsx']
```

A mensagem nomeia **a chave e os dois arquivos** — quem opera consegue agir sem
abrir o código.

## T-08 · Arquivo inválido

Planilha com aba e colunas erradas na pasta de entrada:

```
exit 1 · arquivo REJEITADO, com a lista de colunas encontradas
```

**Nenhuma ingestão parcial:** o pipeline aborta antes de gravar qualquer Parquet.

## T-09 · Coluna obrigatória ausente

Arquivo sem `Qtde Faturado`:

```
exit 1
arquivo REJEITADO: sellin_TESTE_sem_coluna.xlsx
  colunas obrigatorias ausentes: ['Qtde Faturado']
  colunas encontradas         : [...]
  (config/config.yaml -> fontes.sellin.colunas_obrigatorias)
```

## T-10 · Divergência com o gabarito da fonte

Linha `Total` adulterada dentro do arquivo:

```
exit 1
a fato NAO bate com a linha 'Total' da fonte:
  ...gabarito.xlsx [receita]: calculado 1.000,0000 x gabarito 9.999,0000 (dif -8.999,0000)
```

## T-11 · Seletor de métrica

Mesmo período (FY2026), trocando só a métrica — o rodapé da tabela de período:

```
Valor (R$)   R$ 1,13 bi   LY R$ 1,13 bi    −R$ 6,35 mi     ▼ −0,6%
Volume (t)   76,3 mil t   LY 85,1 mil t    −8,8 mil t      ▼ −10,3%
Caixas       15,95 mi cx  LY 16,71 mi cx   −762,3 mil cx   ▼ −4,6%
```

Confere com a fato: 76.262.628,713 kg = 76.262,6 t · 15.948.764 caixas.

## T-12 · YTD Fiscal, YTD Calendário e Mês vs LY

| Base | Período atual | LY | Total |
|---|---|---|---:|
| YTD Fiscal | set/25–ago/26 (12) | 12 de 12 | R$ 1.127.251.765,81 |
| YTD Calendário | jan/26–ago/26 (8) | 8 de 8 | R$ 718.929.361,21 |
| Meses vs LY (padrão) | set/25–ago/26 (12) | 12 de 12 | R$ 1.127.251.765,81 |
| Meses vs LY (`Todos`) | set/24–ago/26 (24) | **12 de 24** | R$ 2.260.853.914,79 |

O card "Comparativo YTD" exibe os dois acumulados ao mesmo tempo:

```
YTD Fiscal      set/25–ago/26 vs set/24–ago/25   R$ 1,13 bi  R$ 1,13 bi  −R$ 6,35 mi   ▼ −0,6%
YTD Calendário  jan/26–ago/26 vs jan/25–ago/25   R$ 718,93 mi R$ 757,78 mi −R$ 38,85 mi ▼ −5,1%
```

Na última linha da tabela, a interface **avisa** a cobertura parcial do LY:
*"LY: 12 de 24 meses cobertos"*. Ela não esconde a assimetria.

## T-13 · Filtros

**Combinados** (categoria `AMENDOIM` + head `Ademir`), estado exibido:

```
Valor (R$) · YTD Fiscal (set→) · período: set/25–ago/26 (12 meses)
· LY: 12 de 12 meses cobertos · filtros: 1 categoria(s) · 1 head(s)
```

**Participação % com filtro de dimensão ativo.** Com `AMENDOIM` selecionado, a
quebra por categoria continua listando as 10 categorias do head e a coluna soma
**100,0%** — porque o denominador remove o filtro da própria dimensão:

```
GOMAS 29,7% · AMENDOIM 19,9% · BALA 19,5% · GRANULADO 7,1% · COMPOUND 6,8%
CHOCOLATE 5,8% · PIRULITO 3,9% · REGALIZ 2,9% · GELATINA 2,7% · JUBES 1,7%
Total  R$ 440,02 mi   100,0%
```

`R$ 440,02 mi` é exatamente o total do head Ademir no FY2026 — confere com T-04.

**Limpar filtros** volta a R$ 1.127.251.765,81 e "sem filtro de dimensão".
**Granularidade:** Mês → 12 linhas · Trimestre → 5 · Semestre → 3.
**Nenhum mês selecionado:** *"Nenhum mês selecionado. Escolha ao menos um mês."*
e os cards somem — não aparecem zerados.

## T-13b · Divisão por zero e ausência de base

Casos-limite avaliados no motor do painel:

```
varPct(100, 0)      -> null   -> tela: "n/d"
varPct(100, null)   -> null   -> tela: "n/d"
varPct(100, -50)    -> +3,0   -> alta com LY negativo NAO vira queda
varPct(0, 100)      -> -1,0   -> "−100,0%"
razao(10, 0)        -> null   -> preco medio: "n/d"
```

Nenhuma tela exibe `∞`, `NaN`, `#DIV/0!` ou célula em branco sem explicação.
Item novo no ranking aparece com o rótulo **"novo"** e `Δ% = n/d`; item que sumiu
aparece com **"sem faturamento"**.

## T-14 · Independência do projeto anterior

```
$ grep -rn -i "Dashboards - Heads|Heads - Canais|Dashboard - Distribui" \
    --include=*.py --include=*.yaml --include=*.html --include=*.json \
    src config dashboard tests run_*.py .claude
  (nenhuma ocorrencia)

$ grep -rn -E "C:\\|/c/Users|senha|password|token|api_key|secret" \
    --include=*.py --include=*.yaml --include=*.html src config dashboard tests run_*.py
  (nenhuma ocorrencia real)

arquivos modificados no projeto anterior desde o inicio da sessao: 0
```

O novo projeto **não importa, não lê e não executa** nada do anterior. A única
coisa que veio de lá é uma **cópia** de `lib/chart.umd.min.js` (biblioteca, não
código de negócio), hoje em `dashboard/lib/`. Apagar o projeto anterior não
afeta nada aqui.

## T-15 · Execução sem IA e sem rede

```
$ grep -rn -E "requests\.|urllib|httpx|openai|anthropic|fetch\(|XMLHttpRequest|WebSocket|cdn\." \
    --include=*.py --include=*.html src config dashboard run_*.py
  (nenhuma ocorrencia)
```

No HTML gerado (8,94 MB), a única ocorrência da palavra `fetch` está **dentro de
um comentário** que explica por que os dados vão embutidos. Zero `src="http`,
zero `href="http`, zero `fetch(`.

O painel abre por duplo clique em `file://`, sem servidor, sem internet, sem
nenhuma API.

---

## O que **não** foi testado, e por quê

| Item | Motivo |
|---|---|
| Volume acima de ~20 mi de linhas | a base tem 3,08 mi; o teste seria com dado sintético, e dado sintético não entra aqui |
| Cruzar SKU com gerente, bandeira ou projeto | fora da camada agregada por decisão medida (D-21); a tela **avisa** quando esses filtros ficam ativos junto com SKU |

> Ticket Médio e canal saíram desta lista na segunda onda: o primeiro foi
> unificado ao preço médio (D-22) e o segundo foi integrado e testado (T-17/T-18).


---

# Reteste da segunda onda — devolutiva de 26/08/2026

Após integrar canal, projeto, a correção do head vago e a nomenclatura do
ticket médio. Tudo executado de novo em 26/08/2026.

## T-16 · Suites completas

```
python tests/test_regras.py    26 de 26 passaram  (2 novos: canal na dimensao)
python tests/cenarios.py       6 de 6 cenarios    (pipeline final exit 0)
python run_pipeline.py         exit 0 · 19,1s com cache
python run_dashboard.py        exit 0 · painel 14,28 MB
```

## T-17 · Canal — cobertura e reconciliação

```
clientes com canal        16.131 de 16.131 (100,0000%)   orfaos: 0
receita classificada      R$ 2.260.853.914,86 (100,0000%)
piso de cobertura         95% (validacao.cobertura_minima_canal) — passou
```

Receita por canal no painel × fato (24 meses) — diferença máxima de **7
centavos** em R$ 503 mi (resíduo do escalonamento em centavos, rel. 1,4e-10):

```
CASH & CARRY          503.065.420,40  ×  503.065.420,47
DISTRIBUIDOR          462.582.450,00  ×  462.582.450,10
ATACADO ESPECIALIZADO 390.470.285,71  ×  390.470.285,75
VAREJO ESPECIALIZADO  349.103.886,16  ×  349.103.886,13
ATACADO GENERALISTA   316.508.716,55  ×  316.508.716,36
VAREJO                236.192.052,79  ×  236.192.052,70
NOVOS CANAIS            2.931.103,36  ×    2.931.103,35
KEY ACCOUNT NACIONAL            0,00  ×            0,00
```

Soma por canal = soma por projeto = total geral = R$ 2.260.853.914,97 no motor
do painel (mesmo denominador, três caminhos).

## T-18 · Filtro de canal nas duas camadas agregadas

Filtro `CASH & CARRY`, FY2026:

```
cubo principal   R$ 242.860.922,34
cubo de SKU      R$ 242.860.922,34   <- identicos ao centavo
```

Quebra por head dentro do canal: Vago - 2600 R$ 133,5 mi · Izabela R$ 93,6 mi ·
Ademir R$ 10,7 mi · Michel R$ 4,9 mi · NÃO ATRIBUÍDO R$ 178 mil.

## T-19 · Quebras novas

* **Por canal** (Visão Geral, dimensão "Canal"): 8 linhas, participação somando
  **100,0%**, `KEY ACCOUNT NACIONAL` exibido com R$ 0,00 e `Δ% = n/d` — não some.
* **Por projeto**: 8 valores; dentro de um canal filtrado a participação continua
  somando 100% (denominador remove o filtro da própria dimensão).

## T-20 · Maykon → Vago (aceite do item 3)

```
log do pipeline:  785 linha(s) tiveram HEAD corrigido por
                  `dimensoes.estrutura_comercial.correcoes_head`:
                  {'Maykon - 2600': 'Vago - 2600'}
receita Vago - 2600   R$ 466.521.780,95   (os 466,5 mi esperados)
total geral           R$ 2.260.853.914,86 (inalterado)
heads na dimensao     Ademir · Izabela - 2650 · Michel - 1000 ·
                      Vago - 2600 · NÃO ATRIBUÍDO   (sem codigo orfao)
```

## T-21 · KPIs após a unificação de nomenclatura

```
FATURAMENTO MÉDIO/MÊS      R$ 93,94 mi   LY R$ 94,47 mi  ▼ −0,6%
PREÇO MÉDIO (= ticket médio) R$ 14,78/kg LY R$ 13,33/kg  ▲ +10,9%
```

`R$ 93,94 mi = 1.127.251.765,81 ÷ 12` ✓. A página R$/kg declara a equivalência
e mantém `Σvalor ÷ Σpeso` com guarda `n/d` para divisor zero (T-13b continua
valendo).

## Critérios de aceite gerais da devolutiva

| Critério | Resultado |
|---|---|
| Total geral em R$ 2,26 bi em todas as visões | **ok** — canal, projeto, head e o total batem no mesmo denominador |
| Nenhuma categoria em branco em Canal, Subcanal, Vendedor ou Projeto | **ok** — canal/subcanal 100%; head e projeto têm o rótulo explícito `NÃO ATRIBUÍDO` para os 71 clientes fora do de-para de estrutura (R$ 421 mil, 0,02%, listados em `data/quality/clientes_sem_estrutura.csv` — exceção declarada, não em branco) |
| Preço médio conferido em 3+ recortes | **ok** — total (14,78), por canal, por categoria e por período; razão das somas em todos |
| Rótulos dos KPIs = o que a fórmula calcula | **ok** — "Faturamento médio/mês" e "Preço médio (= ticket médio)" |


---

# Reteste da Solicitação 02 — 26/08/2026

## T-22 · Base de comparação com dois estados (item 1)

```
BASES no motor                      ["fis","cal"]  (chips: 2)
referencias residuais a F.base==="mes"   0  — branch removido, nao comentado
3 meses marcados (set-nov/25)       atual = 2025-09..11 · LY = 2024-09..11
                                    R$ 316.151.022,64 × R$ 302.072.461,81
selecao cheia do FY2026             R$ 1.127.251.765,81  (inalterado)
YTD Calendario                      oferece 8 meses (jan-ago/26), LY 8 de 8
```

## T-23 · Exportação (item 2)

```
tabelas com botao CSV/XLSX          9 + drill = 10
dado registrado e CRU               ["set/25", 103472787.73, 111231519.49,
                                     -7758731.76, -6.98]  <- numeros, nao texto
nome do arquivo                     sku-amendoim_ytd-fiscal_2026-08.xlsx
XLSX validado FORA do navegador     zipfile.testzip() OK · openpyxl le
                                    14 linhas x 6 colunas · valores float
tabela vazia                        limpa o registro; nao exporta dado velho
```

## T-24 · Drill Categoria → SKU (item 3)

```
linhas clicaveis na quebra por categoria   12 (as 12 categorias)
AMENDOIM aberto                     135 SKUs · 1a linha = maior queda
                                    (JAPONES 40X90G, −R$ 17,55 mi, −46,2%)
total do detalhe = linha agregada   R$ 394,25 mi  (identicos)
filtro aplicado com o drill aberto  CASH & CARRY -> detalhe re-renderiza
                                    (AMENDOIM no canal: R$ 50,61 mi, −14,9%)
voltar                              fecha e preserva o agregado
console                             zero erros
```

Drill-downs Canal → Cliente, Projeto → Cliente e Head → Gerente **não
implementados** — bloqueios B1–B3 da Solicitação 02 (ver D-30).
