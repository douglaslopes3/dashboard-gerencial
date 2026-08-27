# 04 · Gaps e riscos

Um gap por bloco. Cada um traz **o que falta**, **quanto custa** (medido),
**de quem depende** e **o que foi feito enquanto isso**.

---

## GAP-01 — Canal · **RESOLVIDO em 26/08/2026**

A base chegou: `bases/Canais/Canais.xlsx` (aba `Export`, chave `Cód. cliente`,
colunas `Cód. canal`, `Canal`, `Subcanal`). Medido na integração:

```
clientes do sell-in com canal   16.131 de 16.131  (100,0000%)
receita classificada            R$ 2.260.853.914,86 (100,0000%)
clientes orfaos                 0
canais com receita              8 (KEY ACCOUNT NACIONAL existe no de-para
                                   com receita zero no periodo)
```

O filtro e as quebras por canal estão implementados nas cinco páginas, e o
piso de cobertura (`validacao.cobertura_minima_canal`, 95%) aborta o pipeline
se o join se perder — o arquivo traz o código zero-preenchido, como o de-para
de estrutura. Clientes sem canal sairiam em
`data/quality/clientes_sem_canal.csv`, nunca escondidos num "Outros".

**Sobra registrada:** o §9 do prompt esperava 7 canais; a base traz **9**
(`KEY ACCOUNT NACIONAL` e `KEY ACCOUNT REGIONAL` a mais). Nada foi agrupado —
os dois saem no relatório de valores não reconhecidos, para o Comercial dizer
se são canais novos ou reclassificação pendente. O rodapé do arquivo traz um
texto de filtro citando só "Nome Gerente é Izabela - 2650", incoerente com a
cobertura total medida — registrado como aviso, sem bloquear.

---

## GAP-02 — Ticket Médio · **RESOLVIDO por decisão em 26/08/2026**

A devolutiva definiu: **ticket médio e preço médio são a mesma métrica** —
`Σvalor ÷ Σpeso`, razão das somas, com guarda contra divisor zero. Não existem
dois indicadores; a interface declara a equivalência no card e na página R$/kg.

O KPI "faturamento ÷ nº de meses" do protótipo **não é ticket médio** e entrou
com o rótulo que diz o que a fórmula calcula: **"Faturamento médio/mês"**.
Nenhuma divisão por cliente comprador ou por pedido foi introduzida — nenhuma
das duas contagens existe no modelo.

---

## GAP-03 — head vago · **RESOLVIDO em 26/08/2026**

O Comercial confirmou: **Maykon = Vago**. A correção foi declarada em
`config/config.yaml → dimensoes.estrutura_comercial.correcoes_head`
(`"Maykon - 2600": "Vago - 2600"`) e sai registrada no log a cada execução
("785 linha(s) tiveram HEAD corrigido..."). Conferido no aceite: os
**R$ 466.521.780,95** trocaram de rótulo e o total geral seguiu em
**R$ 2.260.853.914,86**. O código fica no rótulo pela mesma convenção dos
pares (`Izabela - 2650`, `Michel - 1000`).

---

## GAP-04 — Caixas não líquida devolução

| | |
|---|---|
| **Impacto** | a métrica Caixas é **bruta**; Valor R$ e Volume são **líquidos** |
| **Tamanho** | **90.289 de 32.659.819 caixas (0,28%)**; 74.749 das 79.758 linhas de devolução têm `Qtde Faturado` nula |
| **Dono** | **BI** |
| **Estado** | **comportamento confirmado pela devolutiva de 26/08/2026**: é o padrão da base — não filtrar, não tratar como erro, não aplicar ABS, manter o sinal |

O pipeline já fazia exatamente isso. Uma divergência de fato permanece
registrada: a devolutiva descreve a devolução vindo com **quantidade negativa**,
mas o medido nas 3,08 mi de linhas é outro — 93,7% das linhas de devolução vêm
com a quantidade **nula** e as demais, **positiva** (`Qtde Faturado` nunca é
negativa na base entregue). O tratamento pedido e o implementado coincidem;
só a descrição do dado difere, e fica anotada para quando o BI revisar a
extração.

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
