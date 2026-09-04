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

## 2. `Hierarquia_Consolidada.xlsx` → `DIM_CLIENTE` (D-34; única fonte desde a D-56)

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
| `CÓDIGO BANDEIRA` | `COD_BANDEIRA` | `digitos()` (D-42, série 82xxxxx; atributo do cadastro desde a D-49) |
| `BANDEIRA` | `BANDEIRA_ESTRUTURA` | `texto()` (D-42, só conferência/rótulo de código) |

`SUPERVISOR` (N3) é lido desde a D-34 e, desde a **D-48** (02/09/2026),
também **chega ao painel**: entra no eixo `perfil` dos dois cubos, vira filtro
em todas as abas com o rótulo **Sup./Exec.** e fecha a cadeia de drill
Head → Gerente → Sup./Exec.

**N4 ingerido desde a D-50** (02/09/2026): `(N4) CÓDIGO VEND./RCA` + `(N4)
VEND./RCA` + `(N4) NOME VEND./RCA` → `VENDEDOR`, rótulo concatenado como os
demais níveis, com `correcoes_vendedor` no config e checagem de conflito
(13 clientes com dois códigos N4 medidos — vale a 1ª linha com aviso).
`CLIENTE` e `REDE` seguem não ingeridos (a deduplicação por cliente acontece
depois das correções, com checagem de conflito N1–N4 e de `COD_BANDEIRA`). `ATENDIMENTO_PONTA` deixou de existir com a troca da base.
`COD_BANDEIRA`/`BANDEIRA_ESTRUTURA` nasceram como ponte por CÓDIGO com a base
de metas FY 26/27; com a remoção do tema Metas (**D-49**) seguem como
ATRIBUTO do cadastro, sem função de join (o sell-in não traz código de
bandeira; a `BANDEIRA` da tela segue vindo do sell-in). O complemento não tem
as colunas: cliente dele fica `<NA>`, nunca inventado. Medido em 01/09/2026:
13.101 de 16.122 clientes com código (81,3%; 93,5% da receita de 24 meses).

O **complemento** (`Hierarquia_Complemento.xlsx`) foi **aposentado na D-49**
(02/09/2026); desde a D-56 a `Hierarquia_Consolidada.xlsx` é a única fonte da
estrutura (o desempate dos 13 clientes com dois códigos N4 foi incorporado na
origem em 03/09/2026).

Cliente com mais de uma linha divergente: vence a primeira, **com aviso**
(hoje: zero); o desempate declarado vive em
`dimensoes.estrutura_comercial.desempate_cliente`. Cliente sem linha no
de-para: `HEAD = "NÃO ATRIBUÍDO"`, `NA_ESTRUTURA = false`; o cliente RTM herda
o vínculo do distribuidor (§2b), por isso um distribuidor removido da base
arrasta os clientes dele (D-61).

## 2b. Reestruturação (D-50) — colunas novas da `DIM_CLIENTE`

Duas bases entram na transformação (`src/transform/saneamento.py`) e agem SÓ
na `DIM_CLIENTE` — a fato nunca é tocada:

`bases/RTM-Transicao/RTM_DePara_Transicao.xlsx` (aba `De-Para RTM`) e
`bases/Bases para tabelas dimensões/Hierarquia_Clientes_Faltando.xlsx`
(aba `Planilha1`) — layouts em `docs/01 §2.6/§2.7`.

| Coluna nova | Conteúdo |
|---|---|
| `ORIGEM_RTM` | cliente está na base RTM-Transicao |
| `COD_DISTRIBUIDOR` | a quem o sell-in foi reatribuído (`<NA>` = sem distribuidor identificado, exceção) |
| `DISTRIBUIDOR` | nome reduzido do distribuidor (da base RTM) |
| `CANAL_ORIGINAL` | canal ANTES da reatribuição (rastreabilidade; só nos reatribuídos) |
| `BANDEIRA_ORIGINAL` | bandeira do ponto final ANTES da reatribuição (D-59; gravada nos dois modos do parâmetro, só nos reatribuídos) |
| `INATIVO` | regra 5.2 aplicada (HIERARQUIA=NÃO e sem sell-in na janela) |
| `MOTIVO_INATIVO` / `DATA_INATIVACAO` | rastreabilidade da inativação |
| `SANEAMENTO_PENDENTE` | HIERARQUIA=NÃO **com** sell-in na janela — caso não coberto (Q5), aguarda decisão |

Cliente reatribuído herda `HEAD/GERENTE/SUPERVISOR/VENDEDOR/PROJETO/CANAL/
SUBCANAL` do distribuidor e, desde a **D-59** (03/09/2026), também a
`BANDEIRA` (a do distribuidor na própria DIM, vinda do sell-in dele, nunca o
nome do cadastro); a bandeira de origem fica em `BANDEIRA_ORIGINAL`.
Distribuidor sem bandeira própria não transmite `SEM BANDEIRA` (o cliente
mantém a sua). **Preserva** `UF` e o próprio `COD_CLIENTE`. O parâmetro
`saneamento.rtm_herda_bandeira: false` devolve a regra da Q4-a (bandeira do
ponto final) sem tocar em código. Inativado recebe o `rotulo_inativo` do
config nos níveis N1–N4. Parâmetros: `saneamento.janela_meses`,
`ancora_janela` e `rtm_herda_bandeira`.

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

## 3b. `FY 26-27_Meta Set_TT BRASIL.xlsx` → `FATO_META` (D-43 — **REMOVIDA na D-49, 02/09/2026**)

> **D-49:** a `FATO_META` deixou de existir — o tema Metas saiu do produto e o
> novo arquivo de metas, quando chegar, será cruzado pela chave do cliente
> (reintegração em docs/12, D-49). A tabela abaixo fica como registro.

Grão: `ANO_MES` x `COD_HEAD` x `BANDEIRA_META` x `COD_BANDEIRA` x `CATEGORIA`
(duplicidade ABORTA). A competência vem do rótulo da coluna (`SET'26`), e a
soma do detalhe é reconciliada contra a linha `Total` do próprio arquivo.

| Origem | Destino | Transformação |
|---|---|---|
| rótulo da coluna de mês | `ANO_MES` | `SET'26` → `2026-09` (aborta se não casar `MMM'AA`) |
| `CÓDIGO HEAD` | `COD_HEAD` | `digitos()` (10/20/30/40 — os mesmos da hierarquia) |
| `HEAD` | `HEAD_META` | `texto()` (nome como veio, só conferência) |
| `CLUSTER` | `CLUSTER` | `texto()` (Top Atacados, Sem Mudança, Phase 1...) |
| `CLIENTE` | `BANDEIRA_META` | `texto()` (nome da bandeira; espaço duplo colapsa) |
| `CÓD. BANDEIRA 1` | `COD_BANDEIRA` | `digitos()` — série 82xxxxx (D-42) |
| `CÓD. BANDEIRA 2` | `COD_BANDEIRA_2` | só quando dígito puro E ≠ do 1 (fusão); senão `<NA>` |
| `CATEGORIA` | `CATEGORIA` | `texto()` (10/10 batem com a DIM_PRODUTO) |
| `(N2) CÓDIGO GERENTE` | `COD_GERENTE` | `digitos()` (prefixo do rótulo `GERENTE` da DIM) |
| `(N3) CÓDIGO SUP./EXEC.` | `COD_SUPERVISOR` | `digitos()` (prefixo do rótulo `SUPERVISOR`) |
| `STATUS VÍNCULO` | `STATUS_VINCULO` | `texto()` |
| coluna sob rótulo `Volume (kg)` | `META_PESO_KG` | numérico |
| coluna sob rótulo `RL (R$)` | `META_RECEITA` | numérico |
| nome do arquivo | `ARQUIVO_ORIGEM` | linhagem |

Arquivo ausente NÃO derruba o pipeline: `FATO_META` sai vazia com o esquema
estável e o painel fica sem meta (ausente, nunca zero). O cruzamento com o
realizado (fase dos visuais) é por CÓDIGO primeiro (D-42), nome como
fallback declarado.

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
