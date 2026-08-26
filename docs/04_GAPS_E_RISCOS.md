# 04 · Gaps e riscos

Um gap por bloco. Cada um traz **o que falta**, **quanto custa** (medido),
**de quem depende** e **o que foi feito enquanto isso**.

---

## GAP-01 — `CANAL` não existe em nenhuma base · **BLOQUEIO MATERIAL**

| | |
|---|---|
| **Indicador impactado** | filtro global `Canal`; quebra por canal na Visão Geral e na página R$/kg; visão "Por canal" da página Bandeiras |
| **Coluna/tabela necessária** | coluna `Subcanal` na extração de Sell In, **ou** coluna de canal no `DePara_Estrutura_Comercial.xlsx` |
| **Dono** | **BI / Cadastro de Clientes** |
| **Tamanho** | **100% dos 16.131 clientes** e **100% dos R$ 2,26 bi** ficam sem canal |
| **Estado** | o filtro e as quebras por canal **não foram implementados**. Nada foi inventado |

### O que foi medido

Nenhuma das colunas de nenhuma das bases entregues contém canal. Varredura
completa de `bases/` (inclusive dentro dos quatro `.zip` de
`bases/scorecards-comerciais/kits/`).

A lista de 7 canais do §9 do prompt (`ATACADO ESPECIALIZADO`, `ATACADO
GENERALISTA`, `VAREJO ESPECIALIZADO`, `VAREJO`, `CASH & CARRY`, `NOVOS CANAIS`,
`DISTRIBUIDOR`) aparece **exatamente uma vez cada** no HTML de referência — no
array `DB.dims.canal`, que o próprio rodapé do arquivo declara como **dados
fictícios**.

### Onde a classificação real existe

Dentro de `bases/scorecards-comerciais/kits/Scorecard_Atacado_kit.zip`, o script
`prep_at.py` lê um pickle `v33.pkl` (a **extração "V3.3"** do BI) e usa uma
coluna **`Subcanal`** com 12 valores:

```
Atacado Doceiro · Atacado Generalista · Atacado para VP · Atacado para festas
AtacadoEspecializado · Atacarejo · Cash & Carry · Distribuidor · Novos Canais
Nao informado · Varejo · Varejo Especializado
```

Os 7 canais do protótipo são uma consolidação desses 12.

**Confirmação cruzada:** o registro de lacunas do próprio projeto anterior
(`docs/lacunas.md`) já traz a mesma pendência, com o mesmo dono:

> `SUBCANAL` · DIM_CLIENTE_CANAL · faltam **16.060 de 16.060 (100,0%)** ·
> dono **BI / Cadastro de clientes** · fonte que precisamos: *"coluna Subcanal
> no DePara_Estrutura_Comercial.xlsx ou na extração de sell-in"*.

### Opções, com tamanho medido — decisão do Douglas

| | Opção | Cobertura | Rastreabilidade | Esforço | Risco |
|---|---|---|---|---|---|
| **A** | **Pedir ao BI a extração de Sell In com a coluna `Subcanal`** (V3.3) | 100% dos clientes, 24 meses, série histórica coerente | total — vira coluna de origem | 1 pedido; o ETL já está preparado (basta declarar a coluna no config) | nenhum |
| **B** | Reaproveitar o mapa cliente→subcanal do `at.json` | **11.177 de 16.131 clientes (69,3%)** e **R$ 907,4 mi de R$ 2.260,9 mi (40,1%)** — só o head Ademir | baixa: é artefato derivado, congelado numa data, de outro projeto | ~2 h | **alto** — 60% da receita ficaria "sem canal" e o filtro mentiria por omissão |
| **C** | Derivar canal de `Novo Gerente` / `PROJETO` / bandeira | — | **nenhuma** — seria regra inventada | — | **proibido** pelo §2.2 do prompt |

**Recomendação: A.** Enquanto ela não chega, o eixo de canal fica ausente da
tela (não desabilitado com valor falso, não preenchido com "NÃO INFORMADO").

### O que substitui o canal hoje

A estrutura comercial **real** disponível, com 99,98% de cobertura de receita:
`HEAD` (4) → `GERENTE` (12) → `SUPERVISOR` (57). Os três estão implementados
como filtro e como quebra. **Não são renomeados para "canal".**

---

## GAP-02 — Ticket Médio não tem definição validada

| | |
|---|---|
| **Indicador impactado** | card "Ticket Médio" da Visão Geral (§11 do prompt) |
| **O que falta** | a definição. Ticket médio pede um **denominador de transação** — número de pedidos, notas, ou clientes compradores |
| **Dono** | **Comercial / Controladoria** |
| **Estado** | **não implementado**, conforme a própria regra do §6: *"Sem definição validada: não implementar, registrar como gap"* |

### Por que não dá para inferir

O grão da fonte é `mês × cliente × SKU`. Não há número de pedido, nota fiscal nem
data transacional. Os denominadores possíveis dão respostas diferentes e
incompatíveis:

* `Receita ÷ clientes compradores no mês` → ticket por cliente/mês;
* `Receita ÷ linhas` → média por linha de faturamento, que **não é** ticket;
* `Receita ÷ pedidos` → **impossível**, a base não tem pedido.

**Pergunta objetiva para o Comercial:** *"Ticket médio do gerencial é receita
líquida dividida por cliente comprador no mês, ou por pedido? Se for por pedido,
precisamos da contagem de pedidos na extração."*

---

## GAP-03 — rótulo do head vago (`Maykon - 2600`)

| | |
|---|---|
| **Impacto** | o filtro Head mostra `Maykon - 2600`; o protótipo mostra `Vago` |
| **Tamanho** | **R$ 466,5 mi (20,6% da receita)** e 787 clientes no de-para |
| **Dono** | **Comercial / RH** |
| **Estado** | **nada foi corrigido.** O valor de origem é exibido como está |

A chave `dimensoes.estrutura_comercial.correcoes_head` existe em
`config/config.yaml`, **vazia**. Basta declarar `"Maykon - 2600": "Vago - 2600"`
para a troca acontecer — e ela sai **registrada no log e no relatório de
qualidade**, nunca em silêncio.

---

## GAP-04 — Caixas não líquida devolução

| | |
|---|---|
| **Impacto** | a métrica Caixas é **bruta**; Valor R$ e Volume são **líquidos** |
| **Tamanho** | **90.289 de 32.659.819 caixas (0,28%)**; 74.749 das 79.758 linhas de devolução têm `Qtde Faturado` nula |
| **Dono** | **BI** |
| **Estado** | **implementado com a ressalva na tela.** O painel exibe a nota, e o relatório de qualidade traz o número a cada execução |

Não foi "consertado": zerar, estimar ou inverter o sinal dessas caixas seria
inventar dado. A pergunta ao BI é se a extração pode trazer `Qtde Faturado`
negativa na devolução, como já traz para receita e peso.

---

## GAP-05 — 71 clientes de sell-in sem head no de-para

| | |
|---|---|
| **Tamanho** | 71 de 16.131 clientes · **R$ 421.421,67 (0,02% da receita)** |
| **Dono** | **Comercial / Cadastro** |
| **Estado** | **entram no fato** com `HEAD = NÃO ATRIBUÍDO`. Não são descartados |

Descartá-los faria o total do painel não bater com o total da fonte. Eles saem
listados em `data/quality/clientes_sem_estrutura.csv`.

## GAP-06 — 7 SKUs de sell-in fora do cadastro `Produtos.xlsx`

| | |
|---|---|
| **Tamanho** | 7 SKUs · 2.036 linhas (0,07%) · **R$ 909.647,72 (0,04%)** |
| **Dono** | **Cadastro de Produtos** |
| **Estado** | entram na `DIM_PRODUTO` com `FORA_DO_CADASTRO = true`, usando a descrição e a categoria do próprio sell-in. **Sem marca** (não é inferida) |

Saem listados em `data/quality/skus_sem_cadastro.csv`.

## GAP-07 — 1 cliente com dois heads no de-para

| | |
|---|---|
| **Tamanho** | 1 cliente |
| **Dono** | **Comercial** |
| **Estado** | vence a primeira linha, **com aviso no log e linha no relatório de qualidade**. O desempate declarado vai em `config/config.yaml → dimensoes.estrutura_comercial.desempate_cliente` |

---

# Riscos residuais

| # | Risco | Probabilidade | Impacto | Mitigação implementada |
|---|---|---|---|---|
| R1 | **Recorte da extração muda em silêncio** — alguém reextrai o Sell In com outro filtro e a série deixa de ser comparável | média | alto | o texto do filtro é lido de dentro do arquivo e comparado entre meses inteiros; divergência vira aviso e linha no relatório de qualidade |
| R2 | **Mês duplicado / competência trocada** — arquivo com nome de um mês e conteúdo de outro | baixa | **alto** (aconteceu no projeto anterior) | a competência vem do **conteúdo** (`Ano mês`), nunca do nome do arquivo; o relatório de qualidade lista mês × arquivo(s) de origem |
| R3 | **`Cód. cliente` zero-preenchido** derruba o join da estrutura em silêncio | — | alto | `lstrip("0")` no leitor + **checagem de cobertura mínima** configurável (`validacao.cobertura_minima_head`); abaixo do piso o pipeline **aborta** |
| R4 | Cache de leitura sobrevive à mudança de um leitor | média | alto | `VERSAO_CACHE` em `src/extract/cache.py`, documentada; subir a versão é parte de mudar um leitor |
| R5 | Crescimento da base além de milhões de linhas | média | médio | fato em Parquet particionado por ano; o painel consome **agregado**, nunca a linha transacional. Ver `docs/09_ARQUITETURA_SOLUCAO.md` |
| R6 | Um mês novo chega partido em `p1`/`p2`/`p3` | média | baixo | o pipeline soma as partes e reconcilia contra a **soma** dos gabaritos; o número de partes é livre |
| R7 | Painel aberto por duplo clique no OneDrive, sem internet | **alta** | alto | a biblioteca de gráfico é **embutida** no HTML e os dados também. Nenhuma requisição de rede. Testado em `file://` |
