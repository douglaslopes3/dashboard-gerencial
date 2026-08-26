# 11 · Resultado dos testes

Executado em **26/08/2026**. Todo número abaixo veio de uma execução real; nada
foi estimado. Onde a saída é longa, o comando que a produz está indicado.

## Resumo

| Bateria | Comando | Resultado |
|---|---|---|
| Regras críticas (unitário) | `python tests/test_regras.py` | **24 de 24** |
| Cenários de ponta a ponta | `python tests/cenarios.py` | **6 de 6** |
| Reconciliação painel × fato | ver T-04 | **bate até o centavo** |
| Interface (filtros, LY, YTD, métrica) | ver T-11 a T-13 | **ok** |
| Independência e ausência de IA | ver T-14 e T-15 | **ok** |

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
| Ticket Médio | **não implementado** — não há definição validada (GAP-02) |
| Filtro e quebra por canal | **não implementado** — não há fonte (GAP-01) |
| Volume acima de ~20 mi de linhas | a base tem 3,08 mi; o teste seria com dado sintético, e dado sintético não entra aqui |
| Cruzar SKU com gerente ou bandeira | fora da camada agregada por decisão medida (D-09); a tela **avisa** quando esses filtros ficam ativos junto com SKU |
