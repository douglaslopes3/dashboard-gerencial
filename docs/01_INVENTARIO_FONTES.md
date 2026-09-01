# 01 · Inventário das fontes

> Tudo aqui foi **medido**, não estimado. Data da medição: 26/08/2026.
> Os comandos e a saída bruta ficam em `docs/11_RESULTADO_DOS_TESTES.md`.

## 1. Fonte principal — Sell In

| | |
|---|---|
| Pasta | `bases/Sell In/` (e também `data/raw/sell_in/`, criada para o ciclo mensal) |
| Formato | `.xlsx`, aba única **`Export`** |
| Arquivos | **28** (~95 MB) |
| Linhas úteis | **3.081.986** (D-36: 3.133 linhas 100% zeradas descartadas na ingestão) |
| Período | **2024/09 a 2026/08** — 24 meses, sem buraco |
| Schemas distintos | **1** — as 28 planilhas têm exatamente as mesmas 13 colunas |

### 1.1 Colunas de origem

| # | Coluna | Tipo | Papel | Nulos |
|---:|---|---|---|---:|
| 0 | `Ano` | int | redundante com `Ano mês`; marca o rodapé com o texto `Total` | 0 |
| 1 | `Ano mês` | texto `AAAA/MM` | **chave temporal** | 0 |
| 2 | `Cód. cliente` | número | **chave de cliente** | 0 |
| 3 | `Cliente` | texto | nome do cliente | 0 |
| 4 | `Bandeira cliente` | texto | **bandeira/rede** | 0 |
| 5 | `Estado` | texto (UF) | **geografia** | 0 |
| 6 | `Desc. categoria` | texto | **categoria do produto** | 0 |
| 7 | `Cód. material` | número | **chave de produto (SKU)** | 0 |
| 8 | `Desc. material sem código` | texto | descrição do SKU | 0 |
| 9 | `Receita Líquida` | float | **métrica Valor R$** | 0 |
| 10 | `Peso Líquido` | float (kg) | **métrica Volume** | 0 |
| 11 | `Qtde Faturado` | float | **métrica Caixas** (ver §1.5) | **75.956 (2,46%)** |
| 12 | `Comissão Faturada Líquida` | float | fora do escopo do MVP | 0 |

**Não existe coluna de canal, head, gerente, supervisor, CNPJ, cidade ou data
transacional.** A estrutura comercial vem do de-para (§2.2) e o canal do
de-para de canais (§2.3, entregue em 26/08/2026).

### 1.2 Rodapé — dois blocos que precisam sair antes de qualquer conta

Todos os 28 arquivos trazem, depois dos dados:

* **1 linha `Total`** (coluna `Ano` = `"Total"`) — vira **gabarito de reconciliação**;
* **2 linhas de `Filtros aplicados`** (só a coluna `Ano` preenchida) — o recorte da extração.

Ignorar esse rodapé dobra a soma de cada arquivo. O ETL descarta as linhas sem
`Ano mês` e usa a linha `Total` como gabarito.

### 1.3 Reconciliação contra o gabarito da própria fonte

Soma dos dados × linha `Total`, arquivo a arquivo, nas três métricas:

```
maior |diferenca| receita   R$ 0,0000073
maior |diferenca| peso         0,0000020 kg
maior |diferenca| qtde         0,00000000023 cx
```

**28 de 28 arquivos fecham nas três métricas.** A linha `Total` traz também
`Qtde Faturado` — a fonte reconhece Caixas como métrica própria.

### 1.4 Filtro da extração — recorte estável, com uma exceção conhecida

Todos os 28 arquivos carregam o mesmo filtro de negócio:

> `Tipo mercado não é B2B, (Em branco), NAO INFORMADO, DIVERSOS, OUTRAS VENDAS ou EXTERNO`

Quatro meses vêm **partidos em `p1`/`p2`** por limite de linhas da extração —
`2024/09`, `2024/10`, `2024/11` e `2025/05`. Nesses, cada parte tem um filtro
**complementar** por `Nome Gerente` (p1 exclui um conjunto de gerentes, p2 exclui
o resto). Os dois pedaços **somam**, e a reconciliação é feita contra a **soma dos
dois gabaritos** — nunca contra um arquivo só.

O ETL normaliza a assinatura do filtro removendo a cláusula `Ano mês é ...`
(que muda por construção) e só alerta quando **meses inteiros** divergem entre si.

### 1.5 `Qtde Faturado` é CAIXA — medido, não presumido

Teste: para cada SKU, a mediana de `Peso Líquido ÷ Qtde Faturado` foi comparada
ao peso da caixa lido na descrição (`12X30X32G`, `24X400G`, `12X1,010KG`...).

```
SKUs com descricao parseavel                277 de 283
batem dentro de +-2%                        277  (100,0%)
linhas com kg/un igual a mediana do SKU   2.932.756 (98,14%)  +-0,1%
                                          2.959.618 (99,04%)  +-5%
peso reconstruido (Qtde x kg_caixa) vs peso real   +1,03%
```

**Conclusão: `Qtde Faturado` é a quantidade de caixas faturadas.** Não é preciso
fator de conversão por SKU, e nenhum foi inventado. As 1,53% de linhas abaixo da
mediana são caixas fracionadas (remessa parcial), que continuam sendo caixas.

**Ressalva medida (vira nota na tela):** Caixas **não líquida devolução**.
Das 79.758 linhas com receita negativa, **74.749 (93,7%) têm `Qtde Faturado`
nula** e as demais trazem quantidade **positiva**. Valor R$ e Volume são líquidos
de devolução; Caixas é bruto. Tamanho do desvio: **90.289 de 32.659.819 caixas
= 0,28%**.

### 1.6 Grão e duplicidade

```
duplicados em ANO_MES x Cod. cliente x Cod. material   0  de 3.081.986
duplicados de linha inteira                            0
duplicados no grao dentro do mesmo arquivo             0
```

**O grão declarado da fonte se sustenta.** Ver `docs/06_MODELO_ESTRELA.md`.

### 1.7 Cardinalidade

| Coluna | Distintos |
|---|---:|
| `Ano mês` | 24 |
| `Cód. cliente` | **16.092** (16.131 antes da D-36: 39 clientes só tinham linhas zeradas) |
| `Cliente` (nome) | 12.261 |
| `Bandeira cliente` | **11.296** |
| `Estado` | **27** (as 27 UFs) |
| `Desc. categoria` | **12** |
| `Cód. material` | **494** |

### 1.8 Sinais e zeros

| Métrica | Negativos | Zeros | Nulos | Soma (24 meses) |
|---|---:|---:|---:|---:|
| Receita Líquida | 79.758 | 15.174 | 0 | **R$ 2.260.853.914,86** |
| Peso Líquido | 78.679 | 18.055 | 0 | **161.321.487,32 kg** |
| Qtde Faturado | 0 | 2.152 | 75.956 | **32.659.819,49 cx** |

Negativo = devolução. **Não é filtrado**: o valor líquido de devoluções é o que a
fonte entrega e é o que o painel mostra.

---

## 2. Fontes de dimensão

### 2.1 `bases/Bases para tabelas dimensões/Produtos.xlsx` — cadastro de SKU

Aba `Produtos` · 1.712 linhas · colunas `Código Produto`, `Descrição Produto`,
**`Marca`** (90 valores), `Categoria` (11 valores).

```
SKUs no sell-in                    494
SKUs no cadastro                 1.712
linhas de sell-in SEM cadastro   2.036 (0,07%)  R$ 909.647,72 (0,04%)
SKUs sem cadastro                    7
divergencia de categoria sell-in x cadastro   0 linhas
```

A categoria do sell-in e a do cadastro **nunca divergem** nas 3,08 mi de linhas.
O cadastro tem uma categoria a mais que o sell-in (`ESPECIAIS`, sem faturamento
no período) e o sell-in tem duas que o cadastro não tem, nos 7 SKUs órfãos.

> O cadastro **tem** coluna `Marca` (o do projeto anterior não tinha). Marca é
> dado de origem aqui — não é inferido da descrição.

### 2.2 `bases/Bases para tabelas dimensões/Hierarquia_Consolidada.xlsx` (D-34)

Substituiu o `DePara_Estrutura_Comercial.xlsx` em 28/08/2026 (D-34). Aba
`Planilha1` · 14.054 linhas · 13.448 códigos distintos · 71 linhas sem código
(estrutura real, descartadas com aviso — mesmo padrão do C12). A granularidade
é **cliente × vendedor (N4)**: linhas repetidas por cliente são esperadas e os
níveis N1–N3 não conflitam (medido: zero conflitos).

Colunas por nível (os cabeçalhos têm **quebra de linha interna** — o leitor
normaliza todo espaçamento): `CÓDIGO CLIENTE`, N1 head (`(N1) CÓDIGO HEAD`,
`CRIAR NO BI (N1) HEAD`, `(N1) NOME HEAD`), N2 gerente, N3 sup./exec.,
N4 vend./RCA (não ingerido), `PROJETO`, e ainda `CLIENTE` e `REDE` com código
(não ingeridos). `CÓDIGO BANDEIRA`/`BANDEIRA` são ingeridos desde 01/09/2026
(D-42, colunas opcionais): viram `COD_BANDEIRA`/`BANDEIRA_ESTRUTURA` na
DIM_CLIENTE e são a ponte por código com a base de metas FY 26/27 — a
`BANDEIRA` de tela segue vindo do sell-in. O complemento NÃO traz as colunas
(pedido ao Comercial aberto); cobertura medida: 81,3% dos clientes, 93,5% da
receita.

Cada nível vira **um rótulo concatenado** `código - papel - nome` (parte vazia
omitida): `20 - ATACADO - ADEMIR TAVARES`. O código vem SEM zeros à esquerda
(a base anterior vinha zero-preenchida) — `digitos()` cobre os dois formatos.

**Complemento** `Hierarquia_Complemento.xlsx` (mesma pasta, mesmo layout):
2.612 clientes que faturam e não constam da base oficial (554 ativos em
ago/2026, R$ 136,4 mi/24m), mapeados pelo supervisor da base anterior —
pendente de validação do Comercial. A oficial **sempre vence**; quando ela os
incorporar, o complemento esvazia sozinho.

```
cobertura de HEAD sobre o sell-in (oficial + complemento)
  receita com head      99,98%
  clientes sem head     71 de 16.092
  so a oficial          93,95% de receita — ABAIXO do piso de 95%
```

Heads: `20 - ATACADO - ADEMIR TAVARES` (R$ 912,5 mi) · `10 - DISTRIBUICAO -
MICHEL MEIRA` (R$ 543,4 mi) · `30 - KA Nacional - [VAGO]` (R$ 466,5 mi) ·
`40 - KA REGIONAL - IZABELA SANTOS` (R$ 338,0 mi). Gerentes: 13 ·
Supervisores: 55 · `PROJETO`: 6 valores (só os da base oficial: o complemento
tem `PROJETO` **em branco por decisão**, 28/08 — seus 2.612 clientes ficam
`NÃO ATRIBUÍDO` no recorte de projeto até o Comercial classificar).
`Atendimento Ponta` **não existe mais** (a coluna saiu da DIM_CLIENTE; nunca
chegava ao painel).

> A base grafa o mesmo posto vago ora `[VAGO]`, ora `[Vago]`, e o gerente
> 33000 aparece com e sem nome — padronizados por **correção declarada** no
> config (`correcoes_head`/`correcoes_gerente`), nunca em silêncio.

### 2.3 `bases/Canais/Canais.xlsx` — de-para Cliente → Canal (26/08/2026)

Aba `Export` · 43.073 clientes · colunas `Cód. cliente` (zero-preenchido),
`Cód. canal`, `Canal` (9 valores), `Subcanal` (43 valores). Traz rodapé de
`Filtros aplicados`, como o sell-in.

```
cobertura sobre o sell-in    16.092 de 16.092 clientes (100,0000%)
receita classificada         R$ 2.260.853.914,86 (100,0000%)
clientes orfaos              0
clientes com >1 canal        0
```

Canais com receita: CASH & CARRY (22,25%) · DISTRIBUIDOR (20,46%) ·
ATACADO ESPECIALIZADO (17,27%) · VAREJO ESPECIALIZADO (15,44%) ·
ATACADO GENERALISTA (14,00%) · VAREJO (10,45%) · NOVOS CANAIS (0,13%) ·
KEY ACCOUNT NACIONAL (0,00%). `KEY ACCOUNT REGIONAL` existe no de-para sem
cliente faturado. Os dois `KEY ACCOUNT` não estão na lista do §9 e saem no
relatório de valores não reconhecidos.

### 2.4 Demais arquivos de dimensão — fora do escopo deste MVP

| Arquivo | Por que fica fora |
|---|---|
| `Distribuidores_DePara.xlsx` | ponte sell-in ↔ sell-out (79 distribuidores). Sell Out está fora do escopo |
| `FEMSA_DePara_Produtos.xlsx` | de-para de sell-out FEMSA |
| `Supervisores_DePara.xlsx` | aba `DePara` **vazia** — é um "leia-me" pedindo preenchimento |

### 2.5 `bases/Metas/FY 26-27_Meta Set_TT BRASIL.xlsx` → `FATO_META` (D-43, 01/09/2026)

Meta oficial FY 26/27 do Comercial, aba `Meta 26-27_com Bandeira`. Grão
**head x bandeira x categoria**, um PAR de colunas por mês (Volume kg + RL R$).
Hoje só set/26: 3.282 linhas de detalhe, R$ 122.279.463,48 e 7.824,5 t.

Peculiaridades do layout, todas absorvidas pelo leitor (`src/extract/metas.py`):
cabeçalho fora da linha 1 (achado pelo conteúdo: linha com CLIENTE e
CATEGORIA); rótulo do indicador na linha ACIMA do cabeçalho; competência no
rótulo da coluna (`SET'26` → `2026-09` — do conteúdo, nunca do nome do
arquivo); linhas `Total` no meio do dado (a total geral é o GABARITO de
reconciliação: detalhe que não soma a linha Total ABORTA, mesma regra do
sell-in). `CÓD. BANDEIRA 1` é o código de bandeira do Comercial (série
82xxxxx, a mesma do `CÓDIGO BANDEIRA` da Hierarquia_Consolidada, D-42);
`CÓD. BANDEIRA 2` só é fusão quando é dígito puro e diferente do 1 ("Ok",
autorreferência e a chave interna dos baldes não são).

Não ingeridos: N4 (vendedor/RCA), nomes por extenso dos níveis, `CLIENTE
ATIVO` (o join com o realizado é por código; rótulos oficiais moram na
hierarquia). Os baldes `Sem Mudança`/`Projeto L` (R$ 30,5 mi, cauda do
Atacado aberta por gerente/executivo mas sem bandeira) entram como linhas
normais — o tratamento é da fase dos visuais. Cobertura medida na primeira
carga: 73,3% do R$ casa por código + 0,7% por nome; sem par: os 2 baldes +
DISO/UNIVALE/PELLAH (códigos novos 8202xxx, clientes do complemento —
pedidos ao Comercial abertos, ver D-42/D-43).

---

## 3. Fontes presentes na pasta e explicitamente fora do escopo

`bases/Sell Out - MTRIX/` (13 arq.) · `bases/Sell Out - FEMSA/` ·
`bases/Sell Out - KAN/` · `bases/Previsão de Vendas/` ·
`bases/Estoque Mtrix/` · `bases/Alavancas/`. (`bases/Metas/` entrou no
escopo em 01/09/2026 — ver §2.5.)

Nenhuma é lida pelo pipeline (§2.4 do prompt: Sell Out, Metas, Previsão,
Planejamento e Verbas estão fora).

`bases/scorecards-comerciais/` é **código-fonte** dos painéis de canal, não base.
Foi varrido — inclusive dentro dos `.zip` — como **referência**, e é de onde saiu
a única pista concreta sobre o canal (ver GAP-01). **Não é dependência do
pipeline.**

---

## 4. Valores encontrados × valores esperados pelo prompt (§9)

### 4.1 Categorias — 12 encontradas, 10 esperadas

| Valor na base | Linhas | Situação |
|---|---:|---|
| GOMAS | 680.652 | esperado |
| AMENDOIM | 664.191 | esperado |
| BALA | 570.215 | esperado |
| REGALIZ | 288.005 | esperado |
| GRANULADO | 231.422 | esperado |
| GELATINA | 230.675 | esperado |
| CHOCOLATE | 180.941 | esperado |
| PIRULITO | 125.050 | esperado |
| COMPOUND | 68.750 | esperado |
| **JUBES FRUIT SNACKS** | 45.052 | prompt escreve `JUBES FRUIT SNACK` (singular) — **a base manda**, nada foi renomeado |
| **NAO INFORMADO** | 158 | **não previsto** — mantido como está |
| **DISPLAY/MAT.PROMOCIONAL** | 8 | **não previsto** — mantido como está |

Nenhum erro de grafia do tipo `CHOLOCATE` foi encontrado. **Nada foi corrigido.**
O relatório de valores não reconhecidos sai em
`data/quality/valores_nao_reconhecidos.csv` a cada execução.

### 4.2 UFs — 27 de 27, sem valor inválido

`SP` (1.084.078 linhas) ... `AP` (3.517). Todas as 27 UFs brasileiras presentes.

### 4.3 Heads — 4 encontrados, 4 esperados

Esperado `Ademir, Izabela, Michel, Vago`; encontrado `Ademir`, `Izabela - 2650`,
`Michel - 1000`, `Maykon - 2600`. O sufixo numérico é o código do gerente e **faz
parte do valor de origem**. `Vago` ↔ `Maykon - 2600` é a única correspondência que
exige decisão de negócio (GAP-03).

### 4.4 Canais — resolvido em 26/08/2026

Na primeira entrega, nenhum dos 7 canais existia em base alguma (era o GAP-01).
A base `bases/Canais/Canais.xlsx` chegou com a devolutiva e cobre 100,0000% dos
clientes e da receita — ver §2.3 e o GAP-01 em `docs/04_GAPS_E_RISCOS.md`.
