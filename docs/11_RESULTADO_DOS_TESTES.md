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

## T-25 · Drill Head → Gerente (B2 liberado)

```
linhas clicaveis na quebra por head   5
Gerentes de Ademir                    4 · ordenado pela maior queda
  Gerente Sul/CO                      R$ 127,02 mi · −R$ 14,85 mi · −10,5%
  Gerente NENO                        R$ 105,03 mi · −R$ 8,77 mi
  Gerente SP / MG-ES-RJ               −2,2% / −1,3%
total do head = linha agregada        R$ 440,02 mi  (identicos)
com CASH & CARRY filtrado             R$ 10,66 mi — bate com o Ademir x CC
                                      medido na fato (10.660.870,83)
exportacao                            gerentes-ademir_ytd-fiscal_2026-08
                                      · dado cru: [127016771.38, ...]
drill de categoria                    continua funcionando apos o novo
console                               zero erros
```


---

# Reteste pós-correções da auditoria — 27/08/2026

Após aplicar as duas levas do `AUDIT.md` (A1–A7/A9–A15, B1/B3/B4/B5/B7/B8,
C1–C16; `VERSAO_CACHE=3`).

## T-26 · Suites e pipeline

```
python tests/test_regras.py    29 de 29  (novos: paridade pct/div x varPct/razao)
python tests/cenarios.py       6 de 6    (T-07 atualizado: a duplicata e barrada
                                          NA INGESTAO pelo A3 — mesmo recorte =
                                          copia duplicada; o grao e a 2a defesa)
python run_pipeline.py         exit 0 · 129 s com releitura total (cache v3);
                               mesmos totais: R$ 2.260.853.914,86 · 161.321,49 t
                               · 32.659.819 cx · coberturas 99,98% / 100,00%
FATO_SELLIN                    23,2 -> 20,3 MB (zstd + row groups de 1 Mi)
```

## T-27 · Identidade de números no painel (o B1 não pode mudar nada)

Os 4 totais de controle, lidos no navegador após índice+memo+abas sob demanda:

```
FY2026                    R$ 1.127.251.765,81   identico
Geral (24 meses)          R$ 2.260.853.914,97   identico
CASH & CARRY no FY2026    R$   242.860.922,34   identico
Ademir no FY2026          R$   440.020.838,54   identico
memo de total()           mesmo objeto devolvido no segundo acesso
console                   zero erros
```

## T-28 · Comportamentos das correções, na tela

```
A7  granularidade Trimestre em base fiscal    FY2026-T1..T4 (era 2025-T3 rasgado)
A1  FY2025 (sem LY) na aba Bandeiras          rodape LY/Δ = n/d; destaque diz
                                              "Sem base no ano anterior" (era
                                              +R$ 2,26 bi verde)
B1c abas sob demanda                          sujas apos filtro; renderizam no
                                              clique (SUJAS conferido no console)
render()                                      44 ms · modo SKU 51 ms (era o
                                              cenario de segundos em maquina fraca)
```

---

# Reteste do painel V3 (lotes 1 e 2) e arquivos por head — 31/08 a 01/09/2026

Cobre a varredura de diagnóstico de 31/08, a fase 2 aprovada (D-38 a D-41) e a
geração por head. Todo número veio de execução real, a maior parte lida do
painel em execução no navegador.

## T-29 · Suites, pipeline e geração

```
python tests/test_regras.py    30 de 30
python tests/cenarios.py       6 de 6 · T-05 reescrito: o esperado agora e
                               MEDIDO na hora (receita do resumo.json antes do
                               cenario + R$ 1.000,00 do arquivo sintetico,
                               tolerancia de 1 centavo). O literal antigo
                               (R$ 2.260.854.914,86) quebrou sozinho quando o
                               sell-in de ago/26 chegou: base +R$ 48,9 mi sem
                               defeito nenhum (D-41)
python run_pipeline.py         exit 0 · 28 arquivos · 3.110.907 linhas de origem
                               receita R$ 2.309.797.874,70 · 164.510,21 t
                               · 33.384.067 cx · coberturas 99,96% / 100,00%
python run_dashboard.py        exit 0 · ~1,3 s · 5 arquivos:
  Dashboard_Gerencial_Canais_v3.html                            14,39 MB
  ..._v3_HEAD_10-distribuicao-michel-meira.html                  3,90 MB
  ..._v3_HEAD_20-atacado-ademir-tavares.html                     7,52 MB
  ..._v3_HEAD_30-ka-nacional-vago.html                           1,67 MB
  ..._v3_HEAD_40-ka-regional-izabela-santos.html                 2,09 MB
particionamento (log)          heads R$ 2.308.856.707,70 + NAO ATRIBUIDO
                               R$ 941.167,11 = R$ 2.309.797.874,81 (fecha;
                               os 11 centavos vs resumo sao o residuo ja
                               documentado do escalonamento em centavos)
```

## T-30 · Varredura do build no navegador (diagnóstico de 31/08)

```
build antigo em disco          continha "**template_v2.html**" ANTES do
                               <!DOCTYPE> (artefato de colagem: quirks mode e
                               texto visivel no topo). O template commitado ja
                               estava limpo; o build era anterior. Regenerado
                               e conferido: DOCTYPE na primeira linha
carga + interacoes             zero erros de console em: carga, 5 abas, 6
                               dimensoes do Detalhamento, drill Categoria->SKU
                               (108 linhas) e Head->Gerentes (4), ordenacao
                               por cabecalho (desc/asc), filtros, aviso F1-C
                               da pagina de SKU, link de recorte restaurado
                               apos reload (aba SKU + 1 gerente voltaram)
ids referenciados no JS        60 de 60 existem · zero id duplicado no DOM
v1 x v2 x v3                   payload embutido identico nos tres builds
                               (mesma execucao, mesmo tamanho de blob)
```

## T-31 · "Ver por" nas 4 granularidades e período parcial (D-38)

```
Ver por: Trimestre (FY cheio)  grafico FY2026-T1..T4 · titulo "· Trimestre"
Ver por: Ano                   grafico [FY2026] · tabela de periodo [FY2026]
                               · colunas da matriz [FY2025, FY2026]
cenario do bug (antes: alto)   Periodo=Mes (ago/26) + Ver por=Trimestre
                               -> rotulo "FY2026-T4 (parcial)" com
                               R$ 105.058.120,79 (1 mes); a nota explica o
                               "(parcial)". Antes rotulava T4 cheio
                               (R$ 313,5 mi reais no T4)
chips                          Periodo "Mes" aceso + Ver por "Trimestre"
                               aceso ao mesmo tempo: estados independentes e
                               ambos visiveis
sync L3 mantida                clicar num atalho de Periodo realinha a
                               granularidade (Acumulado -> colunas por mes)
barras locais nas abas         removidas; a barra vive no painel de filtros
                               que viaja (T-34)
```

## T-32 · Ordem das barras do comparativo (D-39)

```
posicao renderizada            Ano anterior x=78 (esquerda) · Atual x=85
                               (direita), lidas do Chart.js em execucao
legenda                        [Δ% vs LY, Media do periodo, Ano anterior,
                               Atual] — ano anterior antes do atual
detalhe que pegou              trocar so a ordem do ARRAY de datasets nao
                               muda nada: posicao/legenda/tooltip seguem a
                               propriedade `order` (LY:3, Atual:4; linhas 1
                               e 2 continuam por cima)
rotulo em negrito              segue o LABEL "Atual", nao a posicao di===0
                               (senao o negrito trocaria de barra)
```

## T-33 · Arquivos por head: recorte físico conferido (D-40)

Arquivo do head 20 (ATACADO, Ademir Tavares) aberto no navegador:

```
soma do cubo DO ARQUIVO        92.823.291.482 centavos
mesmo recorte no painel        92.823.291.482 centavos  <- identicos
completo (filtro por perfil)   (R$ 928.232.914,82)
dims.head                      ["20 - ATACADO - ADEMIR TAVARES"] (so ele)
perfil / hc                    nenhuma tupla de outro head
"MICHEL MEIRA" no HTML inteiro ausente (innerHTML varrido)
titulo / h1 / rodape           declaram "Arquivo restrito ao head ..."
console                        zero erros
```

Publicação em `Painéis Comerciais\Gerencial\` (01/09): os 5 arquivos copiados
com nome temporário + renome e conferidos por md5 contra o build, 5 de 5
idênticos byte a byte.

## T-34 · Painel de filtros em todas as abas (D-38, pedido seguinte)

```
posicao por aba                geral: depois do #gridEvo · geo/band/sku/preco:
                               primeiro elemento do panel (medido via DOM nas
                               5 abas, ida e volta)
filtro aplicado de outra aba   na aba Bandeiras, abrir o painel e clicar
                               CASH & CARRY: 1a linha da tabela muda de
                               "DEMAIS BANDEIRAS 29.251" para "ATACADAO
                               6.107" na hora; linha de estado mostra
                               "1 canal(is)" na propria aba
Ver por de dentro da aba SKU   Trimestre reagrupa a matriz (T1/25, T2/25...)
listeners                      preservados na viagem do no (nada re-ligado);
                               zero erros de console no ciclo completo
```

## T-35 · Interface sem emoji e sem travessão (D-41)

```
varredura do texto renderizado (document.body.innerText, pagina inteira):
  emojis (U+1F300..1FAFF, ⬇, ⚠)   0 ocorrencias
  travessao (—)                    0 ocorrencias
trocas conferidas na tela          "Copiar recorte" (sem 🔗) · "↓ CSV/XLSX"
                                   · "Atenção:" nos avisos · intervalos
                                   "set/25 a ago/26" · "SP · São Paulo"
simbolos tipograficos mantidos     ▸ ▾ ▲ ▼ ‹ › Σ ✓ · (nao sao emoji)
```

## T-36 · Código de bandeira da hierarquia na DIM_CLIENTE (D-42)

```
teste novo (test_codigo_de_bandeira_entra_e_ausencia_fica_nula)
  cliente na estrutura           COD_BANDEIRA e BANDEIRA_ESTRUTURA presentes
  cliente fora da estrutura      <NA> (nunca inventado)
  estrutura sem as colunas       colunas existem na DIM, nulas (esquema estavel)
unitarios                        31/31 (30 anteriores + este)
cenarios ponta a ponta           6/6
pipeline completo (cache v6)     28 Excel relidos · 75 s · exit 0
  receita/peso/caixas            R$ 2.309.797.874,70 · 164.510,21 t ·
                                 33.384.067 cx (IDENTICOS ao centavo)
  cobertura do codigo            13.101 de 16.122 clientes (81,3%)
                                 93,5% da receita de 24 meses
painel regenerado                5 arquivos, tamanhos identicos, particiona-
                                 mento fecha (2.308.856.707,70 + 941.167,11)
correcao de registro             o README dizia "3.110.907 linhas de origem ·
                                 fato 3.107.516": medido nos logs, a origem e
                                 3.114.298 e a fato (pos-descarte D-36) e
                                 3.110.907 - o descarte tinha sido subtraido
                                 duas vezes no texto
```

## T-37 · Leitor de metas e FATO_META (D-43) — **aposentado na D-49** (tema Metas removido; testes e módulos saíram do build)

```
testes novos (4)
  rotulo de mes                  SET26/FY 26/27/XYZ26 -> None; SET26 valido
                                 -> 2026-09 (conteudo, nunca posicao)
  estruturar                     linhas Total fora do dado; total geral vira
                                 gabarito; par SET26 mapeado kg/R$ pelo
                                 indicador da linha de cima
  COD. BANDEIRA 2                fusao so digito puro e != do 1; "Ok",
                                 autorreferencia e chave de balde viram <NA>
  reconciliacao                  detalhe x linha Total: divergencia aborta
unitarios                        35/35 (31 anteriores + 4)
cenarios ponta a ponta           6/6 (T-06 idempotencia inclui a nova carga)
pipeline com o arquivo real      exit 0 · FATO_META 3.282 linhas x 14 col
  meta set/26                    R$ 122.279.463,48 · 7.824,5 t · 4 heads ·
                                 259 bandeiras · reconciliada ao centavo
                                 com a linha Total do proprio arquivo
  cobertura sobre o realizado    73,3% do R$ por CODIGO + 0,7% por nome;
                                 sem par 26,1% = baldes Sem Mudanca/Projeto L
                                 (R$ 30,5 mi) + DISO/UNIVALE/PELLAH
  bonus                          DOCES  TIQUINHO (espaco duplo) casou sozinho
                                 pela normalizacao texto()
sell-in                          intocado: totais identicos ao centavo,
                                 painel regenerado, particionamento fecha
```

## T-38 · CUBO_META e aba Metas (D-44, rota A) — **aposentado na D-49**

```
testes novos (2)
  rota A                         cliente de hierarquia divergente soma no dono
                                 DECLARADO na meta; fusao entra pelo codigo 2;
                                 cauda segue a hierarquia e casa com o balde
                                 na mesma linha DEMAIS BANDEIRAS
  sem base                       construir() devolve None e o painel remove a
                                 aba do DOM
unitarios                        37/37 · cenarios 6/6 · pipeline exit 0
CUBO_META (carga real)           2.547 linhas · 54 grupos · 257 bandeiras ·
                                 reconciliado contra FATO_META (R$ e kg) e
                                 FATO_SELLIN (LY set/25) · +136 KB no pacote
navegador (server painel)        painel completo: meta R$ 122,28 mi · LY
                                 R$ 103,47 mi · +18,2% embutido · realizado
                                 n/d com aviso "sem sell-in do mes ainda" ·
                                 visao head = regua por head ao centavo de
                                 exibicao · 54 executivos · 257 bandeiras ·
                                 11 categorias (1 sem meta) · metrica em t ok
arquivo por head (Izabela)       so grupos dela (18 executivos 4xxx), meta
                                 R$ 20,30 mi · LY 15,60 mi · ECONOMART inteira
                                 no arquivo dela (rota A, decisao declarada)
console                          zero erros nas duas paginas
```

## T-39 · Meta na Evolução (D-45) — **aposentado na D-49**

```
FY2027 · set/26 (sem filtro)     LY 103,47 mi | Atual 1,28 mi | Meta 122,28 mi
                                 legenda ganha "Meta"; nota declara a barra
filtro de canal                  barra some; nota "Meta oculta: a base de
                                 metas nao tem os eixos canal, UF, projeto ou
                                 SKU - limpe esses filtros para ver a meta"
filtro head Izabela              Meta 20,30 mi (rota A) + nota da assimetria
FY2026 (sem mes de meta)         sem barra e sem nota de meta
console                          zero erros
republicacao                     5/5 HTMLs no SharePoint com md5 conferido
                                 (so os do v3; licao da publicacao anterior)
```

## T-40 · Seletores sem "Head" no arquivo por head (D-46)

```
arquivo do head 20               Detalhamento: Canal/Categoria/Gerente/
                                 Projeto/UF (sem Head) · R$/kg idem
recorte salvo com dimGeral=head  recai em Categoria, sem erro
painel completo                  chip Head intacto nos dois seletores
console                          zero erros · republicacao 5/5 md5 ok
```

## T-41 · Remoção do tema Metas (D-49, 02/09/2026)

```
unitarios                        35/35 (os 6 de metas sairam com os modulos)
grep de vestigios                zero referencia de codigo a metas em src/,
                                 run_*.py, config e template (so changelog)
run_dashboard.py                 5 arquivos gerados; particionamento fecha:
                                 R$ 2.317.781.656,27 + 969.705,72 =
                                 R$ 2.318.751.361,99
navegador (server painel)        painel completo: 5 abas (sem Metas), sem
                                 bloco Meta x Realizado, sem serie de meta na
                                 Evolucao; aba Bandeiras renderiza; console
                                 zero erros
arquivo por head (Michel)        abre limpo, filtro Head oculto, titulo
                                 declara o recorte; console zero erros
run_pipeline.py                  ABORTA por cobertura 94,08% < piso 95% —
                                 efeito da EXCLUSAO do Hierarquia_Complemento
                                 .xlsx da pasta bases (2.641 clientes sem
                                 estrutura), NAO da D-49; nenhum parquet foi
                                 gravado. Painel do build vem do curated de
                                 02/09 14:43 (pre-D-49, mesma execucao A6).
                                 Destrava na Fase 2 (RTM + saneamento) ou por
                                 decisao sobre o piso/complemento.
```

Adendo (mesma noite, apos as decisoes "piso 0,93" e "complemento definitivo"):

```
run_pipeline.py                  exit 0 · cobertura 94,08% aceita (piso
                                 temporario 0,93 declarado no config)
curated                          sem FATO_META; caches de meta/complemento
                                 removidos do staging
painel                           9,29 MB · pacote embutido SEM cubo_meta
                                 (verificado descompactando o build)
particionamento                  heads 2.181.581.461,40 + NAO ATRIBUIDO
                                 137.169.900,61 = 2.318.751.362,01
navegador                        recarregado do build novo: 5 abas, zero erro
testes                           35/35
```

## T-42 · Fase 2: N4, reatribuição RTM e saneamento (D-50, 02/09/2026)

```
unitarios                        40/40 (5 novos: heranca do distribuidor com
                                 bandeira/UF preservadas; RTM sem distribuidor
                                 fora da hierarquia com flag; inativacao exige
                                 as DUAS condicoes; janela de CALENDARIO
                                 ancorada na ultima competencia fechada +
                                 virada de ano; precedencia RTM > saneamento)
bug pego pela medicao            1a execucao serviu a estrutura do cache v6
                                 SEM o N4 (1 vendedor no painel inteiro) —
                                 VERSAO_CACHE 6->7, reprocessado
pipeline                         exit 0 · cobertura 97,65% (piso restaurado
                                 a 0,95) · RTM 1.596 reatribuidos a 27
                                 distribuidores · 166 excecao · 612 inativados
                                 · 158 pendentes Q5 · conflito RTM x Faltando 0
DIM_CLIENTE (verificado)         RTM reatribuidos 100% canal DISTRIBUIDOR ·
                                 1.045 bandeiras proprias preservadas ·
                                 CANAL_ORIGINAL 1.596/1.596 · VENDEDOR sem
                                 nulos · 204 N4 atribuidos
canal DISTRIBUIDOR               R$ 559,94 mi na serie (R$ 82,62 mi entram)
particionamento                  heads 2.264.205.766,98 + fora da hierarquia
                                 54.545.595,39 = 2.318.751.362,37
relatorio de qualidade           §7b quantifica os dois lados por distribuidor;
                                 3 CSVs novos de excecao em data/quality/
painel                           12,27 MB (cru 34,8 -> 12,0; teto 25 MB ok) ·
                                 completo e head 20 (7,52 MB) abertos no
                                 navegador: 5 abas, zero erro de console;
                                 balde INATIVO (SANEAMENTO) visivel nos
                                 filtros; NENHUM arquivo por head para os
                                 baldes NAO ATRIBUIDO / INATIVO
```

## T-43 · Painel v4: 3 abas e matriz hierárquica (D-51, 02/09/2026)

```
unitarios                        41/41 (novo: cubos sem eixo UF e posicoes
                                 do contrato com o template v4)
cenarios ponta a ponta           6/6 · pipeline final exit 0
matriz hierarquica               cascata Head -> Gerente -> Sup./Exec. ->
                                 Vend./RCA aberta no navegador; N3 2320 =
                                 soma EXATA dos 21 N4 filhos (61.786);
                                 Total geral ATUAL = card Valor (R$ 1,28 mi)
sintese fora da hierarquia       linhas Σ NAO ATRIBUIDO e INATIVO
                                 (SANEAMENTO) sem expansao, no Total geral
bandeiras                        LASA expande -> AMENDOIM/CHOCOLATE/GOMAS;
                                 balde Σ presente; Total geral soma todas
categorias                       12 categorias; AMENDOIM expande -> 97 SKUs
                                 (12 -> 109 linhas)
filtros                          canal DISTRIBUIDOR recorta KPIs/matrizes;
                                 estado "1 filtro ativo"; Limpar ok
estados cinza                    ZERO elementos [disabled]/.semdado/.off no
                                 DOM (regra global da reestruturacao)
arquivo por head (Ademir, v4)    7,05 MB · so o squad dele nos dims · filtro
                                 Head oculto · titulo declara o recorte ·
                                 console zero erros
painel completo                  11,35 MB (cru 30,8 -> 11,1) · console zero
                                 erros em todas as interacoes testadas
guardiao de erro                 pegou o esquecimento de renderHier na 1a
                                 geracao (tela de erro com a mensagem, nunca
                                 pagina em branco) — corrigido e regerado
```

## T-44 · Arquivos por nível e publicação por pasta (D-52, 02/09/2026)

```
unitarios                        43/43 (novos: recorte por N3 com
                                 particionamento do nivel no mini modelo;
                                 sanitizacao do nome de pasta)
geracao                          73 arquivos (Full + 4 N1 + 13 N2 + 55 N3)
                                 em 12,4s, asserts de recorte por arquivo
particionamento por nivel        N1 = N2 = N3: 2.264.205.766,93 + fora
                                 54.545.595,37 = 2.318.751.362,30 (ao centavo)
publicacao (Q13)                 72 pastas por usuario + Full na raiz de
                                 Paineis Comerciais\Gerencial\ · substituicao
                                 com MD5 conferido · nomes sanitizados
                                 (Superv_RS/SC -> Superv_RS-SC)
navegador (N3 Murilo Cunha)      matriz comeca em Sup./Exec. -> Vend./RCA ·
                                 1 linha propria -> expande ao N4 (leaf sem
                                 expansor) · filtro Head oculto · titulo
                                 declara o recorte · console zero erros
payload (N2 Marcelo Hunter)      85 perfis · um unico gerente no arquivo ·
                                 R$ 270.982.163,63
```

---

## Rodada de 03/09/2026 (D-54 a D-62)

```
unitarios                        55/55  (python tests/test_regras.py)
cenarios ponta a ponta           6/6    (python tests/cenarios.py; pipeline final
                                 com as bases reais: exit 0)
pipeline (20260903-155531)       exit 0 · cobertura estrutura 97,65% · canal 100,00%
                                 · 29/29 arquivos reconciliados · cubos 123.900 /
                                 866.028 · perfis 517 · ~19 s com cache
geracao (20260903-155624)        73 arquivos em 9,7 s · particionamento N1 = N2 =
                                 N3: 2.270.444.756,04 + fora 54.687.559,17 =
                                 2.325.132.315,21 (ao centavo) · 72 publicados +
                                 Full na raiz, MD5 conferido
```

## T-45 · Visibilidade dinamica dos botoes e recorte das dimensoes por nivel (D-54)

```
unitarios (4)                    recorte encolhe canal/categoria/SKU do arquivo
                                 (mini modelo com dois heads em canais distintos:
                                 H1 -> so VAREJO, H2 -> so ATACADO e so BALA);
                                 reindexacao de categoria e SKU aponta para o
                                 rotulo certo nos DOIS cubos, dinheiro identico
                                 (R$ 1.100,00); calendario e corte global
                                 intactos; templates v3 e v4 sem nome de
                                 head/canal e com a funcao de visibilidade
guarda "nada cinza"              .chip.semdado, marcarChipsVazios, [disabled] e
                                 opacity:.38 ausentes do CODIGO dos dois templates
                                 (comentarios fora da leitura)
```

## T-46 · Formatacao unica de valor (D-55)

```
unitario                         rotCurto e escalaFixa ausentes dos templates;
                                 tabela unica ESCALAS presente; prefixo dirigido
                                 pela unidade da metrica (un==="R$")
```

## T-47 · Contagem da linha Σ por arquivo (D-57)

```
unitarios (2)                    com corte artificial de 1 no mini modelo: a
                                 contagem do balde de cada recorte (N1 H1, N1 H2,
                                 N3 S1) bate com demais_por_nivel do gerador; o
                                 rotulo recontado esta em dims.ban; top e
                                 cobertura iguais ao global; o pacote global nao
                                 e mutado; soma dos N1 = total (R$ 2.100,00)
geracao real                     demais_por_nivel N1: Distribuicao 6 · Atacado
                                 9.333 · KA Nacional 4 · KA Regional 25 (o Full
                                 segue com 10.048); assert do rotulo na lista de
                                 bandeiras passou nos 72 arquivos
```

## T-48 · Nomes sem sufixo e recolhimento dos antigos (D-58, D-60)

```
build                            Dashboard_Gerencial.html (11,38 MB) + 72
                                 Dashboard_Gerencial_N1_/N2_/N3_*.html
publicacao                       73 html no destino · 0 com "_Canais_v4" ·
                                 0 pasta de quarentena · raiz so com o Full
ferramenta                       python ferramentas/limpar_paineis_antigos.py
                                 --listar: "a geracao atual produz 73 arquivo(s)
                                 · nenhum arquivo antigo" (antes da limpeza
                                 manual listava 73 antigos, 41 MB)
```

## Rodada de 03/09/2026 à noite (D-63 a D-68, crítica do painel)

```
unitarios                        60/60  (python tests/test_regras.py)
pipeline (20260903-2330)         exit 0 · cobertura 97,65% · reconciliacao ok ·
                                 cubo principal 495.037 (todas as bandeiras) ·
                                 cubo SKU 680.530 (sem bandeira) · ~31 s com cache
geracao                          73 arquivos em 15,6 s, publicacao DESLIGADA
                                 (config) · particionamento N1 = N2 = N3:
                                 2.270.444.755,76 + fora 54.687.559,19 =
                                 2.325.132.314,95 (26 centavos abaixo da
                                 execucao anterior: arredondamento por grupo
                                 com 4x mais grupos; dentro da tolerancia
                                 relativa 1e-6 da reconciliacao)
tamanhos                         Full 14,24 MB (era 11,38) · Atacado 11,13
                                 (7,17) · Sul/CO 3,78 (2,31) · RS/SC 3,11
                                 (1,82) · Distribuicao 1,24 (2,02: perdeu as
                                 bandeiras fora do escopo que viajavam de nome)
navegador (4 arquivos)           Full, N1 Distribuicao, N2 Sul/CO, N3 RS/SC:
                                 console zero erros nas 3 abas
```

## T-50 · Periodo inicial (D-63)

```
Full, N2 Sul/CO, N3 RS/SC        abrem em "set/25 a ago/26 (12 meses) · LY 12
                                 de 12 meses cobertos" (localStorage limpo);
                                 grafico com 12 pares de barras; KPI Full
                                 R$ 1,2 bi ▲ +4,4% (antes: set/26 parcial,
                                 1 barra, −85% a −94%)
unitario                         periodoInicial + chave de recorte v5
```

## T-51 · Cubo de SKU sem bandeira (D-64)

```
unitarios (5 atualizados)        posicao da receita 3 no cubo de SKU; soma por
                                 sup./exec. bate entre os dois cubos
reconciliacao real               CUBO_SKU 680.530 linhas x fato: ok nas 3 metricas
```

## T-52 · Todas as bandeiras no arquivo, corte de exibicao (D-65)

```
unitarios (3 novos)              cubo sem balde (3 bandeiras do modelo de teste);
                                 recorte H2 leva so REDE C, reindexada, R$ 1.100
                                 intactos; N3 exibir_todas = true, N1 = false;
                                 particionamento fecha
Full (aba Bandeiras)             Top 50: 50 linhas nominais (LASA primeiro) +
                                 "Σ DEMAIS BANDEIRAS (10.298 bandeiras)";
                                 rodape "50 de 10348 exibidas + sintese";
                                 nota: nominais = 50,2% do recorte
N3 RS/SC                         2.930 bandeiras nominais, linha Top oculta,
                                 nota "nao ha corte nem linha Σ"; ganhos agora
                                 listam EURO COMPANY, LUCIBEL... (antes
                                 estavam dentro do Σ e fora dos destaques)
N2 Sul/CO                        3.415 bandeiras nominais, Top oculto, KPI
                                 R$ 129,6 mi
```

## T-53 · Busca (D-66)

```
Full, Bandeiras, "confian"       4 de 10.348: CONFIANÇA, DOCES DO VALE
                                 CONFIANCA..., CONFIANCA LOJA DE CONVENIENCIA,
                                 EMPORIO CONFIANCA... (sem acento, fora do
                                 Top 50); rodape "busca: 4 de 10348; o total
                                 soma todas"
Full, Categorias, "chocolate"    categorias com SKU casando abertas sozinhas
                                 (AMENDOIM > AMENDOIM CHOCOLATE DORI CONF...),
                                 42 linhas
unitario                         campos, semAcento, estado no recorte
```

## T-54 · Colunas de decisao primeiro (D-67)

```
Full (matriz hierarquica)        cabecalho: HEAD › GERENTE › SUP./EXEC. ›
                                 VEND./RCA, ATUAL, ANT., Δ, Δ%, PART. %,
                                 OUT/25, NOV/25, ... TOTAL
unitario                         ordem no cabecalho e na exportacao
```

## T-55 · Rotulos de leitor nas linhas Σ (D-68)

```
Full (matriz hierarquica)        ultimas linhas: "Sem estrutura comercial" e
                                 "Inativos (sem sell-in há 6 meses)" (antes
                                 NÃO ATRIBUÍDO / INATIVO (SANEAMENTO))
unitario                         texto vem do config, nao do template
```

## Rodada de 04/09/2026 (D-69 a D-71) e publicacao

```
unitarios                        63/63
pipeline (20260904-001046)       exit 0 · perfis 517 com 7 elementos (flag D-71)
                                 · 88 perfis "vendedor = sup" · cubos 495.037 /
                                 680.530 · 10.348 bandeiras
geracao + publicacao             73 arquivos em 28 s · particionamento N1 = N2 =
                                 N3 ao centavo (2.325.132.314,95) · 72 pastas +
                                 Full na raiz, MD5 conferido (Full bf487afd...)
                                 · publicacao religada com o ok do Douglas
navegador                        Full, N1 Distribuicao, N2 Sul/CO, N3 RS/SC,
                                 N3 Deodato Carmo: console zero erros
```

## T-56 · Filtro hierarquico em lista suspensa (D-69)

```
Full, Sup./Exec. = RS/SC          KPI R$ 67,7 mi (o mesmo do arquivo N3 dele);
                                 lista de Gerente 16 -> 2 opcoes (Todos + o
                                 dele); Vend./RCA 155 -> 22; matriz so com o
                                 ramo; Bandeiras com as 2.930 do escopo dele
Full, Gerente = Sul/CO (chips,   KPI R$ 129,6 mi = arquivo N2; Sup./Exec.
antes da troca para lista)       57 -> 4; Bandeiras universo 3.415
N3 RS/SC                         linhas Gerente e Sup./Exec. ocultas; Vend./RCA
                                 com 21 opcoes
unitario                         passaPerfil, listas, DIMS_FILTRO, recorte
```

## T-57 · Sem notas de rodape (D-70)

```
DOM                              0 elementos .note nos 73 arquivos (medido no
                                 Full); notaMatriz ausente do template
unitario                         guarda textual
```

## T-58 · Vend./RCA = Sup./Exec. nao desce um nivel (D-71)

```
base                             0 pares com rotulo igual · 0 com codigo igual ·
                                 43 de 203 com o mesmo NOME · 37 de 55 sups com
                                 um unico vendedor (ele mesmo) · 88 perfis
N3 Deodato Carmo                 matriz de UMA linha sem expansor; Gerente,
                                 Sup./Exec. e Vend./RCA ocultos
Full                             gerente Sudeste aberto: os 5 Sup./Exec. sem
                                 expansor; lista Vend./RCA 197 -> 154
unitario                         flag na posicao 6; "[VAGO - JOAO 1]" com " - "
                                 dentro dos colchetes casa; rotulos de ausencia
                                 e nomes diferentes nao casam
```

## T-49 · Cliente RTM herda a bandeira do distribuidor (D-59)

```
unitarios (4)                    ligado: cliente 900 e distribuidor 800 na MESMA
                                 bandeira, BANDEIRA_ORIGINAL guardada, aviso no
                                 log; desligado: Q4-a de volta; distribuidor com
                                 SEM BANDEIRA nao piora o cliente; so a coluna
                                 BANDEIRA e so a linha RTM diferem entre os modos
pipeline real                    "D-59: 1.596 cliente(s) RTM passaram a carregar
                                 a BANDEIRA do distribuidor" · totais e
                                 particionamento identicos aos da execucao com
                                 a regra antiga
medido no curated                bandeiras por head antes -> depois: Distribuicao
                                 1.111 -> 66 (60 nominais + 6 na linha Σ) ·
                                 Atacado 9.490 -> 9.490 · KA Nacional 17 -> 17 ·
                                 KA Regional 92 -> 92 · universo 11.314 -> 10.348
                                 · receita que trocou de rotulo R$ 82.759.658,47
                                 (3,56%)
```

## T-59 · Aba Bandeiras por Cliente, RTM acumulado (D-72, 04/09/2026)

```
unitarios                        68 de 68 (63 + 5 da D-72): cliente e o 5o indice
                                 e a soma por bandeira nao muda; RTM que herdou
                                 a bandeira vira UMA chave com contagem, com
                                 rollback por `cliente_rtm_acumulado: false`;
                                 recorte por nivel reindexa clientes e mantem a
                                 contagem RTM; `BANDEIRA_HERDADA` no saneamento
                                 (ligado/desligado/distribuidor sem bandeira);
                                 guarda do template (niveis, BASE_MET = 5,
                                 BAN_MULTI, chave tipada, rotulo so no config)
cenarios ponta a ponta           6 de 6 (execucao 20260904-184114)
pipeline real                    exit 0 · 3.131.629 linhas · R$ 2.326.876.207,52
                                 · cubos reconciliados nas 3 metricas ·
                                 "clientes: 14.544 nominais + 25 linha(s) RTM
                                 acumulada(s) somando 1.596 clientes" ·
                                 CUBO_PRINCIPAL 730.257 · CUBO_SKU 681.892
geracao (publicacao OFF)         73 arquivos em 20,9 s; particionamento N1/N2/N3
                                 fecha ao centavo (R$ 2.272.064.860,38 + fora
                                 54.811.347,44 = 2.326.876.207,82); assert por
                                 arquivo: toda linha aponta para bandeira E
                                 cliente da lista do arquivo
comparar_paineis.py              publicado (13:16, D-71) x build (D-72), mesma
                                 base: 73 de 73 dentro do teto de arredondamento
                                 em total geral, por mes e por bandeira; cubo de
                                 SKU e dims identicos; pior bandeira 18 centavos;
                                 Full -18 centavos em R$ 2,33 bi. Achou copia
                                 avulsa do Full em "Dashboard - Full\" (P11)
navegador, Full                  abertura 1,8 s · heap 105 MB · aba Bandeiras
                                 1,07 s · Visao Geral 0,27 s · zero erro no
                                 console · cabecalho "Bandeira > Cliente >
                                 Categoria" · 739 bandeiras com expansor de
                                 cliente · ATACADAO -> 415 CNPJs por valor ->
                                 categorias · DIST. LOBO "abrir Categoria"
                                 direto · DIST. CLAUMAR -> 1003318 R$ 20,9 mi +
                                 "Σ RTM (soma de 109 clientes)" R$ 3,1 mi por
                                 ultimo, abre em GOMAS/BALA/AMENDOIM · Total
                                 geral = KPI R$ 1,2 bi
navegador, N1 Distribuicao       66 bandeiras, 36 com expansor · 113 clientes no
                                 arquivo (88 nominais + 25 RTM) · DIST. DISO ->
                                 CNPJ R$ 764,1 mil + Σ RTM (355) R$ 8,5 mi ·
                                 DIST. CHUA -> 2 CNPJs + Σ RTM (2) R$ 19,3 mil ·
                                 Total geral = KPI R$ 278,7 mi
tamanhos                         Full 17,60 MB · Atacado 12,39 · Distribuicao
                                 1,34 · Sul/CO 4,38 · RS/SC 3,49
```

## T-59 · D-74: metas FY27 por cliente (08/09/2026)

```
unitarios                        78 de 78 (9 novos): leitor aceita serial/data/
                                 texto no Periodo e codigo zero-preenchido;
                                 aborta tipo desconhecido, chave duplicada,
                                 periodo invalido e valor nulo; categoria fora
                                 do modelo aborta (Q5-a); cliente so com meta
                                 entra na DIM pela hierarquia com SEM_SELLIN
                                 (Q4-a); cubo_meta usa os indices do principal,
                                 par so com meta ganha linha, mes so com meta
                                 entra no calendario, meta negativa entra como
                                 esta, reconciliacao por mes aborta se faltar
                                 linha; RTM acumula a meta na linha Σ do
                                 distribuidor; filtrar_por_nivel recorta e
                                 reindexa a meta (H1 + H2 = total); revisoes
                                 registram alterado/removido/novo e so avisam
                                 nos dois primeiros; guarda do template D-74;
                                 guarda da D-67 atualizada (META e ATING. %
                                 entre ATUAL e ANT., condicionadas)
cenarios (ponta a ponta)         6 de 6
pipeline (base real)             exit 0 em 37 s · Metas_FY'27.xlsx 146.794
                                 pares em 3,6 s · set/26 R$ 122.279.463,48 /
                                 7.824,458 t · out/26 R$ 119.951.284,00 /
                                 7.693,401 t · DIM_CALENDARIO 26 meses (out/26
                                 so com meta) · CUBO_META 146.106 linhas,
                                 reconciliado nos 2 meses e 2 metricas ·
                                 FATO_META.parquet 2.098 KB · 7 avisos (os
                                 mesmos de antes)
qualidade §11                    36 clientes da meta fora da hierarquia (R$ 201
                                 mil/mes) · 1 inativo · 55 RTM (somam na Σ do
                                 distribuidor) · 0 sem sell-in na serie ·
                                 negativas 1.034 pares / 318 clientes /
                                 R$ -96.066: 568 pares bandeira x categoria x
                                 mes com negativo, 366 ficam negativos na
                                 categoria, 204 na bandeira inteira (102
                                 bandeiras por mes; pior R$ -1.777)
geracao (publicacao OFF)         73 arquivos em 19 s; Full 19,46 MB (17,62 antes:
                                 +0,92 MB por mes de meta), abaixo do teto de
                                 35 MB; particionamento da META N1/N2/N3 fecha
                                 ao centavo (R$ 241.828.369,97 + fora
                                 402.376,18 = 242.230.746,15); 3 asserts por
                                 arquivo tambem sobre o cubo_meta
navegador, Full                  abertura 3,7 s · heap 200 MB · zero erro ·
                                 FY2027 (set+out/26): KPI "Meta R$ 242,2 mi ·
                                 Ating. 4,8% (parcial)", Volume "Meta 15,5 mil
                                 t · 5,0%"; chip out/26 com "0" e titulo "tem
                                 meta"; estado "meta: 2 de 2 meses (mes
                                 parcial)"; matriz hierarquica META/ATING. %
                                 (PARCIAL) apos ATUAL: Atacado R$ 96,7 mi,
                                 Distribuicao 56,7, KA Nacional 48,3, KA
                                 Regional 40,2, Sem estrutura 401,3 mil,
                                 Inativos 1,1 mil, Total geral 242,2 mi = KPI;
                                 Bandeiras: LASA R$ 15,7 mi, ATACADAO 14,2,
                                 ASSAI 14,5, total = KPI; Categorias: AMENDOIM
                                 R$ 75,5 mi, GOMAS 48,4, BALA 39,7, SKU n/d
navegador, N3 RS/SC              abertura 1,1 s · heap 43 MB · KPI "Meta R$ 12,8
                                 mi · Ating. 6,0% (parcial)" = linha do
                                 executivo = Total geral · 855 t
Evolucao (2a onda, mesmo dia)    serie "Meta" so com meta no periodo: FY2027
                                 por mes (Volume t): set/26 meta 7.824 t x
                                 atual 769 t, out/26 meta 7.693 t x atual 0;
                                 por ano: FY2027 (parcial) meta 15.518 t; FY2026
                                 sem serie nem legenda de meta; rotulo com
                                 valor + atingimento; zero erro no console
```
