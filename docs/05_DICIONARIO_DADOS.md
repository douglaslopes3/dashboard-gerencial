# 05 · Dicionário de dados

Da coluna de origem à coluna do modelo. Toda transformação está declarada; **não
há transformação silenciosa**.

## 1. Sell In → `FATO_SELLIN`

| Origem (`Export`) | Destino | Transformação | Regra |
|---|---|---|---|
| `Ano mês` (`2026/08`) | `ANO_MES` (`2026-08`) | `ano_mes()`: aceita `AAAA/MM`, `AAAA-MM` e `AAAA/MMM` | linha sem `Ano mês` é **rodapé** e é descartada |
| `Cód. cliente` (`1000021.0`) | `COD_CLIENTE` (`1000021`) | `digitos()` + `lstrip("0")` | sem isso o join com a estrutura casa com **zero** clientes |
| `Cód. material` (`9012876.0`) | `COD_PRODUTO` (`9012876`) | `digitos()` + `lstrip("0")` | |
| `Receita Líquida` | `RECEITA` | `float`, **sinal preservado** | negativo = devolução; **não é filtrado** |
| `Peso Líquido` | `PESO_KG` | `float` em **kg**, sinal preservado | a fonte já está em kg |
| `Qtde Faturado` | `CAIXAS` | `float`, **nulo preservado** | validado como caixa (`01 §1.5`); nulo ≠ zero |
| `Cliente` | → `DIM_CLIENTE.NOME_CLIENTE` | `texto()` | não vai para a fato |
| `Bandeira cliente` | → `DIM_CLIENTE.BANDEIRA` | `texto()` | |
| `Estado` | → `DIM_CLIENTE.UF` | `texto()` | |
| `Desc. categoria` | → `DIM_PRODUTO.CATEGORIA` (fallback) | `texto()` | |
| `Desc. material sem código` | → `DIM_PRODUTO.DESCRICAO_PRODUTO` (fallback) | `texto()` | |
| `Ano` | — | descartada | redundante; só serve para achar o rodapé `Total` |
| `Comissão Faturada Líquida` | — | descartada | fora do escopo do MVP |
| *(nome do arquivo)* | `ARQUIVO_ORIGEM` | linhagem | §14 |
| *(execução)* | `EXECUCAO_ID`, `PROCESSADO_EM` | linhagem | §14 |

### `texto()` — a única normalização de string aplicada

`strip` → colapso de espaços múltiplos → **MAIÚSCULA** → `""`, `"NAN"`, `"NONE"`,
`"-"` viram nulo.

**Isto não corrige grafia.** `CHOLOCATE` continuaria `CHOLOCATE` e sairia no
relatório de valores não reconhecidos. Toda correção de rótulo é **declarada em
`config/config.yaml`** e registrada no log e no relatório de qualidade.

## 2. `Hierarquia_Consolidada.xlsx` (+ complemento) → `DIM_CLIENTE` (D-34)

Os cabeçalhos do arquivo têm quebra de linha interna — o leitor normaliza todo
espaçamento para um espaço antes de validar. Cada nível vira **um rótulo**
concatenando `código - papel - nome` com `" - "` (parte vazia é omitida).

| Origem | Destino | Transformação |
|---|---|---|
| `CÓDIGO CLIENTE` | chave de junção (`1036022`) | `digitos()` + `lstrip("0")` |
| `(N1) CÓDIGO HEAD` + `CRIAR NO BI (N1) HEAD` + `(N1) NOME HEAD` | `HEAD` | rótulo concatenado + `correcoes_head` |
| `(N2) CÓDIGO GERENTE` + `(N2) GERENTE` + `(N2) NOME GERENTE` | `GERENTE` | rótulo concatenado + `correcoes_gerente` |
| `(N3) CÓDIGO SUP./EXEC.` + `(N3) SUP./EXEC.` + `(N3) NOME SUP./EXEC.` | `SUPERVISOR` | rótulo concatenado + `correcoes_supervisor` |
| `PROJETO` | `PROJETO` | `texto(maiuscula=False)` |

Nível N4 (vendedor/RCA), `CLIENTE`, `BANDEIRA`/`REDE`: **não ingeridos** (a
granularidade do arquivo é cliente × vendedor; a deduplicação por cliente
acontece depois das correções, com checagem de conflito N1–N3).
`ATENDIMENTO_PONTA` deixou de existir com a troca da base.

O **complemento** (`Hierarquia_Complemento.xlsx`, mesmo layout) entra pelo
mesmo leitor; linha cujo cliente já está na oficial é descartada com log.

Cliente com mais de uma linha divergente: vence a primeira, **com aviso**; o
desempate declarado vive em `dimensoes.estrutura_comercial.desempate_cliente`.
Cliente sem linha no de-para: `HEAD = "NÃO ATRIBUÍDO"`, `NA_ESTRUTURA = false`.

## 3. `Produtos.xlsx` → `DIM_PRODUTO`

| Origem | Destino | Transformação |
|---|---|---|
| `Código Produto` | `COD_PRODUTO` | `digitos()` + `lstrip("0")` |
| `Descrição Produto` | `DESCRICAO_PRODUTO` | `texto()` |
| `Categoria` | `CATEGORIA` | `texto()` |
| `Marca` | `MARCA` | `texto()` — **do cadastro, nunca inferida** |

SKU que aparece no sell-in e não está no cadastro entra com
`FORA_DO_CADASTRO = true`, usando descrição e categoria do próprio sell-in e
`MARCA` nula.

## 4. Derivado — `DIM_CALENDARIO`

Não tem fonte de arquivo: é gerada da amplitude de `ANO_MES` presente na fato.
Ver `docs/06_MODELO_ESTRELA.md §2.2` para a lista de colunas e
`config/config.yaml → calendario` para os parâmetros (`fiscal_mes_inicio: 9`,
`fiscal_prefixo: "FY"`).

## 5. Tipos e unidades — declarados

| Grandeza | Unidade **armazenada** | Unidade **exibida** | Conversão |
|---|---|---|---|
| Receita | R$ | R$ (abrev. mil / mi) | nenhuma |
| Peso | **kg** | **t** | `÷ 1000`, **só na apresentação** |
| Caixas | caixa | caixa | nenhuma |
| Preço médio | — | **R$/kg** | `SUM(RECEITA) / SUM(PESO_KG)`, calculado no contexto |

O Parquet guarda sempre **kg**. A tonelada existe só na tela, para que a soma de
qualquer recorte seja exata e reconciliável com a fonte.
