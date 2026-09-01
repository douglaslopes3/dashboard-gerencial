# 10 · Guia operacional

Para quem opera o painel todo mês. Não é preciso saber Python, e **nenhuma linha
de código precisa ser editada em nenhuma etapa**.

---

## O ciclo mensal, em 4 passos

### 1. Largue o arquivo novo de Sell In

Em **qualquer uma** das duas pastas:

```
bases\Sell In\
data\raw\sell_in\
```

Nome do arquivo: livre. **A competência vem do conteúdo** (coluna `Ano mês`),
nunca do nome — renomear um arquivo não muda o mês em que ele entra.

Se o mês vier partido pela extração (`_p1`, `_p2`), largue **as duas partes**.
O pipeline soma e confere contra a soma dos dois gabaritos.

### 2. Rode o pipeline

```bash
python run_pipeline.py
```

Leva ~2 min na primeira vez e ~15 s nas seguintes (o cache guarda a leitura dos
Excel que não mudaram).

**Só siga se terminar com:**

```
SUCESSO. Rode `python run_dashboard.py` para gerar o painel.
```

Se terminar com `PIPELINE ABORTADO`, veja a seção "Quando dá errado".

### 3. Confira a qualidade

Abra `data\quality\relatorio_qualidade.md`. Olhe três coisas:

1. **Arquivos processados** — o arquivo novo está lá, com o mês certo?
2. **Valores não reconhecidos** — apareceu categoria ou head que não existia?
3. **Avisos desta execução** — mudou alguma coisa desde o mês passado?

### 4. Gere o painel

```bash
python run_dashboard.py
```

Sai em `dashboard\build\` (template e nome do arquivo vêm do config; hoje o
v3):

```
Dashboard_Gerencial_Canais_v3.html                          painel completo (~14 MB)
Dashboard_Gerencial_Canais_v3_HEAD_<head>.html              um por head (4 arquivos)
```

**Abra por duplo clique.** Não precisa de servidor nem de internet.

**Os arquivos por head** (config `dashboard.por_head`) carregam **somente os
dados do squad do próprio head**: o recorte é aplicado na geração do arquivo,
não na interface. O que é de outro squad não existe dentro do arquivo, então
não há filtro, link ou parâmetro capaz de trazê-lo de volta. Título, cabeçalho
e rodapé declaram a restrição. `NÃO ATRIBUÍDO` não gera arquivo (não é squad
de ninguém); o log da geração confere que heads + não atribuído fecham com a
base completa.

**Regra de distribuição: cada head recebe apenas o SEU arquivo `_HEAD_`.**
O painel completo e os arquivos dos demais heads não devem ser compartilhados
com eles. Quem envia o arquivo errado entrega o dado errado; a segregação é
por arquivo.

---

## Quando dá errado

O pipeline **sempre** diz o que aconteceu e onde. Nenhum erro é silencioso, e
**nenhum Parquet é atualizado quando ele aborta** — o painel anterior continua
válido.

| Mensagem | O que aconteceu | O que fazer |
|---|---|---|
| `nenhum arquivo de Sell In encontrado` | pasta vazia ou padrão de nome fora do aceito | a própria mensagem lista as pastas procuradas e se cada uma existe |
| `arquivo REJEITADO: ... colunas obrigatorias ausentes` | a extração veio com colunas diferentes | peça a reextração no layout padrão. Se a coluna mudou de nome de vez, ajuste `config/config.yaml → fontes.sellin.colunas_obrigatorias` |
| `arquivo REJEITADO: nao foi possivel ler a aba 'Export'` | não é um arquivo de Sell In, ou a aba mudou de nome | tire o arquivo da pasta, ou ajuste `fontes.sellin.aba` |
| `o mes X esta partido ... MESMO recorte de extracao` | **cópia duplicada do mesmo mês** (ex.: cópia de conflito do OneDrive, ou o mesmo arquivo nas duas pastas) | apague a cópia e rode de novo — a mensagem lista os arquivos (auditoria A3) |
| `X linha(s) fora do grao declarado` | o mesmo mês/cliente/SKU aparece duas vezes (segunda defesa, para arquivo sem rodapé de filtro) | idem: a mensagem nomeia a chave e os arquivos |
| `a fato NAO bate com a linha 'Total' da fonte` | a soma dos dados não fecha com o rodapé do próprio arquivo | o arquivo veio truncado ou foi editado. Peça a reextração |
| `integridade referencial: ... fora de DIM_...` | chave órfã | não deveria acontecer (as dimensões adotam órfãos). Se acontecer, é bug — abra o log |
| `cobertura da estrutura comercial ... (piso: 95%)` | o de-para deixou de casar com os clientes | conferir se a `Hierarquia_Consolidada.xlsx` mudou de layout e se o `Hierarquia_Complemento.xlsx` está presente (sem ele a cobertura cai para ~93,95% e aborta — D-34). Se a queda for real, ajuste `validacao.cobertura_minima_head` |
| `nao foi possivel apagar ... OneDrive` | o sincronizador está segurando o arquivo | pause a sincronização e rode de novo |
| `o marcador ... aparece N vez(es)` | alguém editou o `template.html` e duplicou um marcador | ver `docs/09_ARQUITETURA_SOLUCAO.md` |

O log completo de cada execução fica em `logs\pipeline_<execução>.log`
(os 30 últimos são mantidos).

---

## Mudanças que se faz no `config/`, não no código

| Quero... | Onde |
|---|---|
| Trocar o arquivo do de-para de canais | `fontes.canais.arquivo` (hoje `bases/Canais/Canais.xlsx`) |
| Mudar o mês de início do ano fiscal | `calendario.fiscal_mes_inicio` (9 = setembro; 1 iguala fiscal e calendário) |
| Corrigir o rótulo de um head/gerente/supervisor | `dimensoes.estrutura_comercial.correcoes_head` (e as irmãs). A troca **sai registrada** no log e no relatório |
| Desempatar um cliente com dois supervisores | `dimensoes.estrutura_comercial.desempate_cliente` |
| Mostrar mais bandeiras no ranking | `dashboard.top_bandeiras` (300 = 73,4% da receita; 500 = 78,9% e +1,9 MB) |
| Mudar quantos itens aparecem em ganhos/quedas | `dashboard.top_ranking` |
| Ligar/desligar os arquivos por head, ou trocar o prefixo do nome | `dashboard.por_head` (`ativo`, `prefixo`) |
| Afrouxar/apertar a tolerância de reconciliação | `validacao.tolerancia_*` |
| Adicionar uma pasta de entrada | `fontes.sellin.pastas` |

**O que NUNCA vai para o config:** lista de canais, categorias, heads, UFs,
bandeiras, clientes, SKUs, períodos ou anos. Tudo isso sai das bases.
(A lista em `validacao.valores_esperados` é **só gabarito de conferência** — não
filtra, não corrige e não ordena nada.)

---

## Como ler o painel

**Seletores globais** — métrica (Valor R$ / Volume t / Caixas), base de
comparação (YTD Fiscal / YTD Calendário — a comparação com o ano anterior está
**embutida**: o painel compara os meses selecionados com os mesmos meses do LY)
e, na barra de **Período**, a seleção de período com setas e o seletor
**Ver por** (Mês / Trimestre / Semestre / Ano), que define a granularidade das
colunas e das barras. Grupo com menos meses que a granularidade pede sai
rotulado **(parcial)** (ou `*` nas colunas da matriz), nunca como período
cheio. No v3 o painel de filtros (com a barra de Período e a linha de estado)
existe em **todas as abas**: fica logo abaixo do gráfico de Evolução na Visão
Geral e no topo nas demais.

**Exportar** — toda tabela tem botões `↓ CSV` / `↓ XLSX` no cabeçalho do card.
Sai o que está na tela (todos os filtros valem), com **número como número**
(sem "R$", decimal com ponto) e o nome dizendo tabela, recorte, base e mês
(`sku-amendoim_ytd-fiscal_2026-08.xlsx`).

**Drill-down** — no card Detalhamento, a quebra por **Categoria** abre os SKUs
da categoria clicada e a quebra por **Head** abre os gerentes do head, sempre
ordenados pela **maior queda** ("quem puxou o resultado para baixo"), com o
mesmo período, base e filtros da tela, botão "← voltar" e exportação própria.

**A linha azul de estado**, no bloco de controles de cada aba, sempre diz o
que está ativo: métrica, base, período, **quantos meses do ano anterior estão
cobertos** e quais filtros de dimensão estão ligados.

**Cinco coisas que o painel declara de propósito** (rodapé):

1. **Caixas é métrica bruta.** Valor e Volume são líquidos de devolução; Caixas
   não. Desvio medido: 0,28%.
2. **Canal** vem de `bases/Canais/Canais.xlsx` (100,00% da receita classificada);
   quem ficar sem canal sai em `data/quality/clientes_sem_canal.csv`.
3. **Ticket médio = preço médio** (`Σvalor ÷ Σpeso`). O card "Faturamento
   médio/mês" é `receita ÷ nº de meses` — o rótulo diz o que a fórmula calcula.
4. **O ranking de bandeiras é nominal nas 300 maiores** (73,4% do faturamento);
   as demais entram agregadas — **o total continua fechando**.
5. **A camada de SKU cruza com head, canal, categoria e UF** — não com gerente,
   bandeira nem projeto; a tela avisa quando esses filtros ficam juntos.

**`n/d`** aparece onde não há base para a conta (LY zero, nulo ou ausente).
Nunca aparece `∞`, `NaN` nem erro técnico.

**Ganho e queda nunca são indicados só por cor**: levam sempre seta (▲/▼) e
sinal (+/−).

---

## Rodar os testes

```bash
python tests/test_regras.py      # 30 testes de regra critica
python tests/cenarios.py         # 6 cenarios de ponta a ponta (roda o pipeline)
```

`cenarios.py` cria arquivos de teste, **apaga todos ao terminar** e reexecuta o
pipeline com as bases reais. Nada sintético sobrevive.

---

## Onde fica o quê

```
bases/Sell In/          origem (somente leitura)
data/raw/sell_in/       pasta do ciclo mensal
data/staging/           cache de leitura (pode apagar; sera refeito)
data/curated/           modelo estrela + cubos  <- o que o painel consome
data/quality/           relatorio e CSVs de excecao da ultima execucao
logs/                   log completo, um por execucao
dashboard/template_v3.html  interface (editada a mao; v1 e v2 ficam como retorno rapido)
dashboard/build/            o painel gerado + os arquivos por head
config/config.yaml      todos os parametros
docs/                   esta documentacao
```

Apagar `data/` e `logs/` é seguro: `python run_pipeline.py` refaz tudo a partir
das bases.

> Quando a `VERSAO_CACHE` sobe (um leitor mudou — está documentado em
> `src/extract/cache.py`), a primeira execução relê os 28 Excel (~2 min) e
> reconstrói o staging sozinha; as seguintes voltam aos ~20 s. Não é defeito.

A auditoria completa do pipeline, com o que foi corrigido e o que ficou aberto
por decisão, está em [`AUDIT.md`](../AUDIT.md).
