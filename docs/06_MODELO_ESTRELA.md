# 06 · Modelo estrela

## 1. O grão da fato — declarado, não presumido

> **Uma linha da `FATO_SELLIN` representa: o faturamento líquido de um SKU para
> um cliente em um mês de competência.**

Chave: **`ANO_MES` × `COD_CLIENTE` × `COD_PRODUTO`**.

### Por que este grão, e não outro

O grão foi **medido** na fonte, não escolhido:

```
duplicados em ANO_MES x Cod. cliente x Cod. material   0  de 3.081.986
duplicados de linha inteira                            0
```

Zero duplicidade em 24 meses. A fonte já entrega nesse grão — o ETL **não
agrega** e **não desagrega**.

### O grão comporta tudo que o painel pede?

| Eixo exigido pelo §4 do prompt | Comporta? | Como |
|---|:--:|---|
| Período | **sim** | `ANO_MES` é a própria chave |
| Cliente / bandeira | **sim** | `COD_CLIENTE` é chave; bandeira é atributo do cliente |
| Produto / SKU | **sim** | `COD_PRODUTO` é chave |
| Categoria | **sim** | atributo do produto |
| UF | **sim** | atributo do cliente |
| Head / Gerente / Supervisor | **sim** | atributo da estrutura comercial, ligada pelo cliente |
| **Canal** | **sim** | atributo do cliente desde 26/08/2026 (`bases/Canais/Canais.xlsx`, 100% de cobertura) |
| Receita, peso, caixas | **sim** | são as três medidas da linha |

**Nenhuma granularidade abaixo do mês existe na fonte** (não há data
transacional, nota nem pedido). Manter mais fino seria inventar; agregar mais
grosso quebraria o recorte por SKU e por cliente.

---

## 2. As tabelas

```
                        DIM_CALENDARIO
                              |  ANO_MES
                              |
  DIM_PRODUTO ----------- FATO_SELLIN ----------- DIM_CLIENTE
   COD_PRODUTO                                     COD_CLIENTE
```

**Três dimensões. Uma fato.** Nenhum snowflake: toda dimensão liga direto na
fato, e nenhuma liga em outra.

### 2.1 `FATO_SELLIN`

| Coluna | Tipo | Papel |
|---|---|---|
| `ANO_MES` | `string` `AAAA-MM` | FK → `DIM_CALENDARIO` |
| `COD_CLIENTE` | `string` | FK → `DIM_CLIENTE` |
| `COD_PRODUTO` | `string` | FK → `DIM_PRODUTO` |
| `RECEITA` | `float64` | R$ líquidos, com sinal |
| `PESO_KG` | `float64` | kg líquidos, com sinal |
| `CAIXAS` | `float64` (nulo permitido) | caixas faturadas, **bruto** |
| `ARQUIVO_ORIGEM` | `string` | linhagem |
| `EXECUCAO_ID` | `string` | linhagem |
| `PROCESSADO_EM` | `timestamp` | linhagem |

`CAIXAS` **permite nulo de propósito**: 2,46% das linhas não têm caixa na fonte,
quase todas devoluções. Preencher com zero somaria uma caixa que não existe e
apagaria a diferença entre "zero caixas" e "a fonte não informou".

> **Perda assumida na camada agregada (27/08/2026, auditoria A13):** os cubos
> publicam grupo 100% nulo de `CAIXAS` como `C=0`, porque o JSON posicional não
> carrega nulo por célula. Medido: 9.519 das 368.699 células do CUBO_SKU
> (2,6%), com −R$ 7,30 mi de receita associada. A **fato preserva o nulo** — a
> distinção se perde só na camada de tela, e o total continua reconciliando
> (a soma ignora nulos nas duas pontas). Quem precisar da distinção lê a fato.

Particionamento: `data/curated/FATO_SELLIN/ANO=AAAA/parte.parquet`.

### 2.2 `DIM_CALENDARIO` — um mês por linha, os dois calendários na mesma tabela

| Coluna | Exemplo | Observação |
|---|---|---|
| `ANO_MES` | `2025-09` | PK |
| `DATA_INICIO`, `DATA_FIM` | `2025-09-01`, `2025-09-30` | |
| `ANO`, `MES` | `2025`, `9` | calendário |
| `MES_NOME`, `MES_ABREV`, `ROTULO` | `Setembro`, `set`, `set/25` | |
| `TRIMESTRE`, `SEMESTRE` | `3`, `2` | calendário |
| `TRIMESTRE_ROTULO`, `SEMESTRE_ROTULO` | `2025-T3`, `2025-S2` | |
| `ANO_FISCAL` | `2026` | ano de **fechamento** (set/25–ago/26 = 2026) |
| `ANO_FISCAL_ROTULO` | `FY2026` | ver decisão D-02 |
| `MES_FISCAL` | `1` | setembro = 1 ... agosto = 12 |
| `TRIMESTRE_FISCAL`, `SEMESTRE_FISCAL` | `1`, `1` | |
| `TRIMESTRE_FISCAL_ROTULO` | `FY2026-T1` | |
| `ANO_MES_LY` | `2024-09` | **pareamento explícito**, nulo se o mês não existir |
| `ORDEM` | `12` | ordenação estável de ano-mês |

**Por que não há tabela de calendário fiscal separada:** duas tabelas de data
obrigam a uma junção dupla e é assim que o total fiscal deixa de bater com o do
calendário. O ano fiscal aqui é **coluna**, não modelo paralelo.

**Por que `ANO_MES_LY` é coluna e não deslocamento:** deslocar por posição erra
sempre que falta um mês na série. Como junção, o LY que não existe simplesmente
**some**, em vez de mentir.

**Nenhuma flag de YTD é gravada.** YTD depende do período selecionado na tela e
seria falso amanhã. Ver §7 do prompt e o `docs/07_CATALOGO_METRICAS.md`.

### 2.3 `DIM_CLIENTE` — cliente, bandeira, UF e estrutura comercial na mesma tabela

| Coluna | Fonte | Nulos |
|---|---|---|
| `COD_CLIENTE` | Sell In (`Cód. cliente`, sem zeros à esquerda) | PK |
| `NOME_CLIENTE` | Sell In (`Cliente`) — vence o **mais recente** | 0 |
| `BANDEIRA` | Sell In (`Bandeira cliente`) | 0 |
| `UF` | Sell In (`Estado`) | 0 |
| `HEAD`, `GERENTE`, `SUPERVISOR` | `Hierarquia_Consolidada.xlsx` + complemento (D-34) — rótulo `código - papel - nome` | 71 clientes |
| `PROJETO` | idem | 71 clientes |
| `CANAL`, `SUBCANAL` | `bases/Canais/Canais.xlsx` (26/08/2026) | 0 clientes — 100% de cobertura |
| `NA_ESTRUTURA`, `TEM_CANAL` | derivados | booleanos |

**Justificativa da consolidação (o §2 da Fase 2 do prompt pede):**

* **UF e bandeira são atributos do cliente**, não dimensões próprias: vêm da
  mesma linha, têm o cliente como única chave e nunca são recortadas sem ele.
  Tabelas separadas seriam snowflake com um atributo cada.
* **Head, gerente e Sup./Exec. também são atributos do cliente.** A
  cardinalidade é 4 / 13 / 56 contra 16.130 clientes — uma
  `DIM_ESTRUTURA_COMERCIAL` separada ligaria na fato **pelo cliente** de
  qualquer forma, e a junção extra não entregaria nenhum atributo novo. Desde a
  **D-48** os três viajam no mesmo índice de `perfil`
  (`[head, gerente, sup./exec., canal, projeto]`) nos **dois** cubos — o cubo de
  SKU deixou de ter o par (head, canal) e passou a carregar também a bandeira,
  o que acabou com os filtros que a aba de SKU ignorava.
* **O nome do cliente vence o mais recente** (`ANO_MES` máximo): cliente
  renomeado no meio da série apareceria duas vezes no ranking.
* **`NA_ESTRUTURA = false`** marca os 71 clientes de GAP-05, que entram com
  `HEAD = "NÃO ATRIBUÍDO"`. Descartá-los faria o total do painel não bater com a
  fonte.

Foi exatamente assim que canal e subcanal entraram em 26/08/2026: como
atributos, sem mudar o modelo.

### 2.4 `DIM_PRODUTO` — SKU, categoria e marca na mesma tabela

| Coluna | Fonte | Observação |
|---|---|---|
| `COD_PRODUTO` | Sell In / cadastro | PK |
| `DESCRICAO_PRODUTO` | `Produtos.xlsx`, com *fallback* na descrição do Sell In | |
| `CATEGORIA` | `Produtos.xlsx`, *fallback* `Desc. categoria` do Sell In | **zero divergência** medida entre as duas fontes |
| `MARCA` | `Produtos.xlsx` | **do cadastro**; nunca inferida da descrição |
| `FORA_DO_CADASTRO` | derivado | 7 SKUs (GAP-06) |

**Categoria é atributo do produto, não dimensão própria.** São 12 valores para
494 SKUs, sempre lidos junto com o SKU. Uma `DIM_CATEGORIA` acrescentaria uma
junção e nenhum atributo.

---

## 3. O que foi deliberadamente **não** criado

| Dimensão candidata | Por quê não |
|---|---|
| `DIM_CANAL` | canal é **atributo do cliente** (`bases/Canais/Canais.xlsx`, 1 canal por cliente — medido: zero conflitos). Uma tabela separada seria snowflake |
| `DIM_CATEGORIA` | atributo de `DIM_PRODUTO` (§2.4) |
| `DIM_UF` / `DIM_GEOGRAFIA` | atributo de `DIM_CLIENTE`. O nome por extenso da UF é **rótulo de apresentação** e vive em `config/geografia.yaml` |
| `DIM_BANDEIRA` | atributo de `DIM_CLIENTE` — 11.296 valores, 1 por cliente |
| `DIM_ESTRUTURA_COMERCIAL` | atributo de `DIM_CLIENTE` (§2.3) |
| Segunda fato | há uma fonte de fato só |

---

## 4. Integridade referencial

O pipeline **aborta** (exit ≠ 0) se qualquer uma falhar:

| Checagem | Regra |
|---|---|
| `FATO.COD_PRODUTO` ⊆ `DIM_PRODUTO` | 100%, sempre — a dimensão adota o SKU órfão |
| `FATO.COD_CLIENTE` ⊆ `DIM_CLIENTE` | 100%, sempre |
| `FATO.ANO_MES` ⊆ `DIM_CALENDARIO` | 100%, sempre |
| chave da fato única | zero duplicados no grão |
| cobertura de `HEAD` | ≥ `validacao.cobertura_minima_head` (padrão 95%) — protege contra o join zero-preenchido de R3 |
| cobertura de `CANAL` | ≥ `validacao.cobertura_minima_canal` (padrão 95%) — o de-para de canais traz o código no mesmo formato |
| soma da fato × gabarito da fonte | dentro da tolerância, nas **três** métricas |
