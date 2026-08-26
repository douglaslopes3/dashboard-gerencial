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

Sai em `dashboard\build\Dashboard_Gerencial_Canais.html` (~9 MB).
**Abra por duplo clique.** Não precisa de servidor nem de internet.

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
| `X linha(s) fora do grao declarado` | o mesmo mês/cliente/SKU aparece duas vezes | **quase sempre é o mesmo mês largado duas vezes.** A mensagem nomeia a chave e os arquivos |
| `a fato NAO bate com a linha 'Total' da fonte` | a soma dos dados não fecha com o rodapé do próprio arquivo | o arquivo veio truncado ou foi editado. Peça a reextração |
| `integridade referencial: ... fora de DIM_...` | chave órfã | não deveria acontecer (as dimensões adotam órfãos). Se acontecer, é bug — abra o log |
| `cobertura da estrutura comercial ... (piso: 95%)` | o de-para deixou de casar com os clientes | conferir se o `DePara_Estrutura_Comercial.xlsx` mudou de layout. Se a queda for real, ajuste `validacao.cobertura_minima_head` |
| `nao foi possivel apagar ... OneDrive` | o sincronizador está segurando o arquivo | pause a sincronização e rode de novo |
| `o marcador ... aparece N vez(es)` | alguém editou o `template.html` e duplicou um marcador | ver `docs/09_ARQUITETURA_SOLUCAO.md` |

O log completo de cada execução fica em `logs\pipeline_<execução>.log`
(os 30 últimos são mantidos).

---

## Mudanças que se faz no `config/`, não no código

| Quero... | Onde |
|---|---|
| Aceitar uma coluna nova da extração (ex.: **`Subcanal`**) | `fontes.sellin.colunas_opcionais` — já está declarada; basta o BI entregar |
| Mudar o mês de início do ano fiscal | `calendario.fiscal_mes_inicio` (9 = setembro; 1 iguala fiscal e calendário) |
| Corrigir o rótulo de um head/gerente/supervisor | `dimensoes.estrutura_comercial.correcoes_head` (e as irmãs). A troca **sai registrada** no log e no relatório |
| Desempatar um cliente com dois supervisores | `dimensoes.estrutura_comercial.desempate_cliente` |
| Mostrar mais bandeiras no ranking | `dashboard.top_bandeiras` (300 = 73,4% da receita; 500 = 78,9% e +1,9 MB) |
| Mudar quantos itens aparecem em ganhos/quedas | `dashboard.top_ranking` |
| Afrouxar/apertar a tolerância de reconciliação | `validacao.tolerancia_*` |
| Adicionar uma pasta de entrada | `fontes.sellin.pastas` |

**O que NUNCA vai para o config:** lista de canais, categorias, heads, UFs,
bandeiras, clientes, SKUs, períodos ou anos. Tudo isso sai das bases.
(A lista em `validacao.valores_esperados` é **só gabarito de conferência** — não
filtra, não corrige e não ordena nada.)

---

## Como ler o painel

**Seletores globais** — métrica (Valor R$ / Volume t / Caixas), base de
comparação (YTD Fiscal / YTD Calendário / Meses vs LY) e granularidade
(Mês / Trimestre / Semestre).

**A linha azul de estado**, logo abaixo dos filtros, sempre diz o que está
ativo: métrica, base, período, **quantos meses do ano anterior estão cobertos** e
quais filtros de dimensão estão ligados.

**Quatro coisas que o painel declara de propósito** (rodapé):

1. **Caixas é métrica bruta.** Valor e Volume são líquidos de devolução; Caixas
   não. Desvio medido: 0,28%.
2. **Não há filtro de canal.** Nenhuma base entregue traz canal ou subcanal. O
   eixo comercial disponível é head → gerente.
3. **Não há Ticket Médio.** Sem definição validada na fonte.
4. **O ranking de bandeiras é nominal nas 300 maiores** (73,4% do faturamento);
   as demais entram agregadas — **o total continua fechando**.

**`n/d`** aparece onde não há base para a conta (LY zero, nulo ou ausente).
Nunca aparece `∞`, `NaN` nem erro técnico.

**Ganho e queda nunca são indicados só por cor**: levam sempre seta (▲/▼) e
sinal (+/−).

---

## Rodar os testes

```bash
python tests/test_regras.py      # 24 testes de regra critica
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
dashboard/template.html interface (editada a mao)
dashboard/build/        o painel gerado
config/config.yaml      todos os parametros
docs/                   esta documentacao
```

Apagar `data/` e `logs/` é seguro: `python run_pipeline.py` refaz tudo a partir
das bases.
