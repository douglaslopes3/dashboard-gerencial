# 10 · Guia operacional

Para quem opera o painel. Não é preciso saber Python, e **nenhuma linha de
código precisa ser editada em nenhuma etapa**. Estado descrito: painel v4
(D-51), um arquivo por colaborador N1 a N3 (D-52), nomes sem sufixo de versão
(D-58), reescrito em 03/09/2026.

---

## O ciclo, em 4 passos

### 1. Largue o arquivo novo de Sell In

Em **qualquer uma** das duas pastas:

```
bases\Sell In\
data\raw\sell_in\
```

Nome do arquivo: livre. **A competência vem do conteúdo** (coluna `Ano mês`),
nunca do nome: renomear um arquivo não muda o mês em que ele entra.

**Substituir, nunca adicionar**: a extração nova do mês corrente substitui a
anterior do mesmo mês. Se as duas ficarem juntas, o pipeline aborta de
propósito (cópia duplicada; ver `docs/14 §1`). Se o mês vier partido pela
extração (`_p1`, `_p2`), largue **as duas partes**: o pipeline soma e confere
contra a soma dos dois gabaritos.

### 1b. Metas (D-74): largue o arquivo em `bases\Metas\`

```
bases\Metas\Metas_FY'27.xlsx
```

Formato: uma linha por `CÓDIGO CLIENTE` × `CATEGORIA` × `Período` × `Tipo
Meta` (`VALOR (R$)` / `VOLUME (KG)`) com o valor na coluna `Valor`. Mês novo
é **linha nova** no mesmo arquivo (ou um arquivo novo na mesma pasta: a
pasta inteira é lida). O mês vem da coluna `Período`, nunca do nome. O mesmo
mês em dois arquivos aborta. Se a meta de um mês já carregado mudar, o
arquivo atual vale e a mudança fica registrada em
`data\quality\metas_revisoes.csv` (aparece como aviso). Categoria com grafia
fora do modelo aborta (corrija no arquivo). **Feche o Excel antes de rodar**:
arquivo aberto derruba a leitura (aconteceu com o sell-in em 08/09).

### 2. Rode o pipeline

```bash
python run_pipeline.py
```

Leva ~2 min na primeira vez e ~20 s nas seguintes (o cache guarda a leitura dos
Excel que não mudaram).

**Só siga se terminar com:**

```
SUCESSO. Rode `python run_dashboard.py` para gerar o painel.
```

Se terminar com `PIPELINE ABORTADO`, veja a seção "Quando dá errado".

### 3. Confira a qualidade

Abra `data\quality\relatorio_qualidade.md`. Olhe quatro coisas:

1. **§1 Arquivos processados**: o arquivo novo está lá, com o mês certo?
2. **§6 Valores não reconhecidos**: apareceu categoria, head ou canal novo?
3. **§7/§7b Registros sem classificação**: a cobertura da estrutura continua
   perto de 97,6%? Os números de RTM e saneamento mudaram?
4. **§10 Avisos**: algum aviso **novo** em relação à execução anterior?
5. **§11 Metas (D-74)**: os meses de meta são os esperados? O total por mês
   bate com o que o Comercial enviou? Alguma revisão de mês já carregado?

### 4. Gere o painel (e publique)

```bash
python run_dashboard.py
```

Uma execução (~10 s) gera **73 arquivos** em `dashboard\build\` e já os
**publica substituindo** nas pastas de `Documentos\Painéis Comerciais\
Gerencial\` (D-52/Q13; `dashboard.publicacao.ativo: false` desliga):

```
Dashboard_Gerencial.html                         painel completo (Full), ~14,2 MB
                                                 publicado na RAIZ do destino
Dashboard_Gerencial_N1_<head>.html               4 arquivos, um por head
Dashboard_Gerencial_N2_<gerente>.html            13 arquivos, um por gerente
Dashboard_Gerencial_N3_<sup-exec>.html           55 arquivos, um por Sup./Exec.
                                                 cada um publicado na PASTA do
                                                 próprio colaborador
```

**Abra por duplo clique.** Não precisa de servidor nem de internet.

**Os arquivos por nível** (config `dashboard.por_nivel`) carregam **somente os
dados do próprio escopo**: o recorte é aplicado na geração, não na interface.
O que é de outro escopo não existe dentro do arquivo, então não há filtro,
link ou parâmetro capaz de trazê-lo de volta (nem as listas de canal,
categoria e SKU: desde a D-54 elas também encolhem junto com o recorte).
Título e cabeçalho declaram o recorte; a matriz hierárquica de cada arquivo
começa no próprio nível. `NÃO ATRIBUÍDO` e `INATIVO (SANEAMENTO)` não geram
arquivo (não são escopo de ninguém); o log confere que cada nível particiona
a base ao centavo.

**Regra de distribuição: cada colaborador recebe só a própria pasta.** A
pasta do colaborador é compartilhada com ele uma vez (ação do Douglas no
SharePoint; pendente para 04/09/2026); as gerações seguintes substituem o
arquivo com o mesmo nome, então o link continua válido. O Full fica na pasta
`Dashboard - Full\` (config `dashboard.publicacao.pasta_full`, D-73),
compartilhada à parte com quem só pode ver a visão corporativa; a raiz não
recebe mais o Full.

**Quando um nome de saída muda** (`dashboard.arquivo_saida`,
`dashboard.por_nivel.prefixo`) ou um colaborador sai da estrutura, a geração
**não apaga** o painel antigo da pasta (regra da D-52). Depois de gerar, rode:

```bash
python ferramentas/limpar_paineis_antigos.py --listar
```

Ele mostra o que sobrou; sem `--listar` move os antigos para
`_ANTIGOS_PARA_APAGAR\` dentro do destino, para você conferir e apagar (D-60).

---

## Quando dá errado

O pipeline **sempre** diz o que aconteceu e onde. Nenhum erro é silencioso, e
**nenhum Parquet é atualizado quando ele aborta**: o painel anterior continua
válido.

| Mensagem | O que aconteceu | O que fazer |
|---|---|---|
| `nenhum arquivo de Sell In encontrado` | pasta vazia ou padrão de nome fora do aceito | a própria mensagem lista as pastas procuradas e se cada uma existe |
| `arquivo REJEITADO: ... colunas obrigatorias ausentes` | a extração veio com colunas diferentes | peça a reextração no layout padrão. Se a coluna mudou de nome de vez, ajuste `config/config.yaml → fontes.sellin.colunas_obrigatorias` |
| `arquivo REJEITADO: nao foi possivel ler a aba 'Export'` | não é um arquivo de Sell In, ou a aba mudou de nome | tire o arquivo da pasta, ou ajuste `fontes.sellin.aba` |
| `o mes X esta partido ... MESMO recorte de extracao` | **cópia duplicada do mesmo mês** (ex.: cópia de conflito do OneDrive, ou o mesmo arquivo nas duas pastas) | apague a cópia e rode de novo; a mensagem lista os arquivos (auditoria A3) |
| `X linha(s) fora do grao declarado` | o mesmo mês/cliente/SKU aparece duas vezes (segunda defesa, para arquivo sem rodapé de filtro) | idem: a mensagem nomeia a chave e os arquivos |
| `a fato NAO bate com a linha 'Total' da fonte` | a soma dos dados não fecha com o rodapé do próprio arquivo | o arquivo veio truncado ou foi editado. Peça a reextração |
| `integridade referencial: ... fora de DIM_...` | chave órfã | não deveria acontecer (as dimensões adotam órfãos). Se acontecer, é bug: abra o log |
| `cobertura da estrutura comercial ... (piso: 95%)` | a hierarquia (`../bases compartilhadas/Hierarquia_AAAAMMDD.xlsx` mais recente, D-83; antes a `Hierarquia_Consolidada.xlsx`) deixou de cobrir a receita | rode `python ferramentas/diagnostico_cobertura.py`: ele diz quem ficou fora e se a causa é a **cascata do RTM** (distribuidor removido da hierarquia arrasta os 1.596 clientes RTM que apontam para ele; foi o caso de 03/09/2026, D-61) ou a chave que parou de casar. Corrija a base; **não** afrouxe `validacao.cobertura_minima_head` para o número passar |
| `cobertura de canal ... (piso: 95%)` | o `Canais.xlsx` deixou de casar com os clientes | conferir se o arquivo mudou de layout (código zero-preenchido é o caso clássico) |
| `cubos.json e resumo.json vem de execucoes DIFERENTES` | gravação anterior interrompida no meio | rode `python run_pipeline.py` de novo antes de gerar o painel |
| `nao foi possivel apagar ... OneDrive` | o sincronizador está segurando o arquivo | pause a sincronização e rode de novo |
| `o marcador ... aparece N vez(es)` | alguém editou o template e duplicou um marcador | ver `docs/09_ARQUITETURA_SOLUCAO.md` |
| `painel(is) da geracao atual nao estao no destino` (ferramenta de limpeza) | rodou a limpeza antes de gerar | `python run_dashboard.py` primeiro; a ferramenta não move nada nesse estado |

O log completo de cada execução fica em `logs\pipeline_<execução>.log`
(os 30 últimos são mantidos). As ferramentas de `ferramentas/` também gravam
um log ali.

---

## Mudanças que se faz no `config/`, não no código

| Quero... | Onde |
|---|---|
| Trocar o arquivo do de-para de canais | `fontes.canais.arquivo` (hoje `bases/Canais/Canais.xlsx`) |
| Mudar o mês de início do ano fiscal | `calendario.fiscal_mes_inicio` (9 = setembro; 1 iguala fiscal e calendário) |
| Corrigir o rótulo de um head/gerente/supervisor/vendedor | `dimensoes.estrutura_comercial.correcoes_head` (e as irmãs). A troca **sai registrada** no log e no relatório |
| Desempatar um cliente com duas linhas conflitantes na hierarquia | `dimensoes.estrutura_comercial.desempate_cliente` (o caminho preferido é corrigir na origem, como na D-56) |
| Cliente RTM herda a bandeira do distribuidor, ou mantém a do ponto final | `saneamento.rtm_herda_bandeira` (`true` desde a D-59; `false` devolve a Q4-a) |
| Janela de inatividade do saneamento | `saneamento.janela_meses` (6) e `ancora_janela` |
| Mudar o corte de exibição de bandeiras do Full e dos heads | `dashboard.top_bandeiras` (300 = 76,7% da receita no Full); `exibir_todas_bandeiras_em` diz quais níveis exibem todas (N2, N3) |
| Trocar o texto de tela das linhas Σ (sem estrutura, inativos) | `dashboard.rotulos_exibicao` (a chave de dado não muda) |
| Mudar quantos itens aparecem em ganhos/quedas | `dashboard.top_ranking` |
| Ligar/desligar os arquivos por nível, ou trocar o prefixo do nome | `dashboard.por_nivel` (`ativo`, `niveis`, `prefixo`) |
| Trocar o nome do painel completo | `dashboard.arquivo_saida` |
| Ligar/desligar a publicação automática, ou trocar o destino | `dashboard.publicacao` (`ativo`, `destino`) |
| Afrouxar/apertar a tolerância de reconciliação | `validacao.tolerancia_*` |
| Adicionar uma pasta de entrada | `fontes.sellin.pastas` |

**O que NUNCA vai para o config:** lista de canais, categorias, heads, UFs,
bandeiras, clientes, SKUs, períodos ou anos. Tudo isso sai das bases.
(A lista em `validacao.valores_esperados` é **só gabarito de conferência**: não
filtra, não corrige e não ordena nada.)

---

## Como ler o painel (v4)

**3 abas.** **Visão Geral** (5 cards de KPI, gráfico de Evolução e a **matriz
hierárquica expansível** Head → Gerente → Sup./Exec. → Vend./RCA), **Bandeiras**
(ganhos/quedas + matriz Bandeira → Categoria) e **Categorias** (ganhos/quedas
+ matriz Categoria → SKU). Toda navegação entre níveis é pela **expansão da
matriz** (clique em ▸); não há drill-down nem "voltar". No arquivo de um
colaborador a matriz começa no nível dele.

**Abertura (D-63).** O painel abre no ano fiscal corrente **até o último mês
fechado**; se o FY corrente ainda não tem mês fechado (setembro), abre no FY
anterior inteiro. O mês parcial está nos chips de Meses.

**Bandeiras (D-65/D-66).** O arquivo carrega **todas** as bandeiras do escopo.
No Full e nos arquivos de head a tabela mostra as N maiores (seletor **Top**) e
soma o resto na linha Σ "DEMAIS BANDEIRAS (N bandeiras)"; nos arquivos de
gerente e Sup./Exec. aparecem todas, sem Top. O campo **Buscar** acha qualquer
bandeira, dentro ou fora do corte. Em Categorias, a busca por SKU (código ou
descrição) abre sozinha a categoria do SKU achado.

**Matrizes (D-67).** Colunas na ordem: nome · **ATUAL · ANT. · Δ · Δ% ·
Part. %** · série de até 12 períodos · TOTAL da série. A exportação segue a
mesma ordem.

**Seletores globais.** Métrica (Valor R$ / Volume t / Caixas), base de
comparação (YTD Fiscal / YTD Calendário; a comparação com o ano anterior está
**embutida**: os meses selecionados contra os mesmos meses do ano anterior),
Ano, Meses (chips, com `Todos`/`Nenhum`), Canal, Categoria, Head (este só no
Full) e, desde a D-69, **Gerente, Sup./Exec. e Vend./RCA** em listas
suspensas de escolha única ("Todos" = sem filtro): é assim que um head vê um
subordinado específico em qualquer aba, e um gerente vê um executivo. As
listas só trazem quem tem dado no recorte; escolher um gerente encolhe a lista
de Sup./Exec.; no arquivo de um Sup./Exec. só a linha de Vend./RCA aparece, e
some se ele mesmo é o único vendedor (D-71). O seletor **Ver por** (Mês /
Trimestre / Semestre / Ano) define a granularidade das colunas e das barras;
grupo com menos meses que a granularidade pede sai rotulado **(parcial)** ou
com `*`. **Onde estão (D-80 e D-81, 15/09/2026):** Métrica, Comparar e Ver
por ficam na barra fixa logo abaixo das abas; o resto fica na **barra lateral
esquerda**, igual à do Scorecard DN: o « recolhe para um trilho estreito (que
mostra em vermelho quantos filtros estão ativos) e o » expande; o navegador
lembra se você deixou aberta ou recolhida. Canal e Categoria são listas com
caixinhas. As abas ficam fixas no topo ao rolar e, com o foco nelas, as setas
do teclado trocam de aba. Barra lateral e barra de leitura são as mesmas nas
três abas.

**Bandeira e Cliente (D-82, 22/09/2026).** Duas linhas abaixo de Vend./RCA,
escolha única. Com até 50 opções com dado a linha é uma lista suspensa como a
de Gerente; com mais, uma caixa de busca: digite parte do nome (ou o código do
cliente) e escolha na lista de sugestões (quem começa com o texto vem
primeiro; Enter pega a primeira; Esc fecha; "Todos (limpar)" ou apagar o
texto e sair da caixa limpam o filtro). Escolher uma bandeira encolhe a lista
de clientes aos dela. Os dois valem em Visão Geral, Bandeiras e nas metas, e
entram no recorte salvo, no link "Copiar recorte" e no nome do arquivo
exportado. Na aba **Categorias** eles **não** valem (os dados por SKU não são
abertos por bandeira nem por cliente) e um aviso laranja no topo da aba diz
isso; período, canal, categoria e hierarquia seguem valendo lá.

**Botão que não tem dado atrás não aparece** (D-54): opção sem linha no
recorte atual some; a que você já selecionou fica com o contador "0"; uma
linha de filtro com menos de duas opções sai inteira; `Limpar filtros` só
existe com filtro ativo; `↓CSV`/`↓XLSX` somem quando a tabela está vazia.
Nada fica cinza ou desabilitado.

**Números** (D-55): a métrica selecionada decide o prefixo, e ele aparece em
todo indicador (card, rótulo de barra, eixo, tooltip, célula de matriz, total):
`R$ 1 mil`, `R$ 25 mil`, `R$ 1,5 mi`, `R$ 1,2 bi`. Volume sai em ` t`, Caixas
em ` cx`; o preço médio (`R$ x,xx /kg`) nunca é abreviado.

**Exportar.** Toda tabela tem `↓ CSV` / `↓ XLSX` no cabeçalho do card. Sai o
que está na tela (filtros valem; nas matrizes, as linhas visíveis na expansão
atual), com **número como número** (sem "R$", decimal com ponto).

**A linha de recorte ativo**, logo abaixo da barra do topo (D-80), sempre diz
o que está ativo: métrica, base, período, quantos meses do ano anterior estão
cobertos e os filtros ligados.

**Sem notas de rodapé** (D-70): os cards não têm texto explicativo; o que
importa está na tabela (rótulo da linha Σ, "Total geral (N de M exibidas)",
`*` de período parcial) e na linha de recorte ativo.

**O que o painel declara na própria tela.**

1. **Caixas é métrica bruta.** Valor e Volume são líquidos de devolução; Caixas
   não. Desvio medido: 0,28%.
2. **Todas as bandeiras do escopo estão no arquivo**; no Full e nos arquivos
   de head o corte é só de exibição (Top N + linha Σ), e **o total continua
   fechando**. Gerentes e Sup./Exec. veem todas.
3. **Ticket médio = preço médio** (`Σvalor ÷ Σpeso`); o card "Fat. médio/mês"
   é `receita ÷ nº de meses`.
4. **Linhas síntese Σ da matriz hierárquica** (`NÃO ATRIBUÍDO`, `INATIVO
   (SANEAMENTO)`) ficam fora da hierarquia com o histórico preservado; o Total
   geral fecha com os cards.

**`n/d`** aparece onde não há base para a conta (LY zero, nulo ou ausente).
Nunca aparece `∞`, `NaN` nem erro técnico. **Ganho e queda nunca são indicados
só por cor**: levam sempre seta (▲/▼) e sinal (+/−).

---

## Rodar os testes

```bash
python tests/test_regras.py      # 63 testes de regra critica
python tests/cenarios.py         # 6 cenarios de ponta a ponta (roda o pipeline)
```

`cenarios.py` cria arquivos de teste, **apaga todos ao terminar** e reexecuta o
pipeline com as bases reais. Nada sintético sobrevive.

---

## Onde fica o quê

```
bases/Sell In/              origem (somente leitura)
bases/RTM-Transicao/        de-para cliente -> distribuidor (D-50)
../bases compartilhadas/     Hierarquia_AAAAMMDD (N1-N4, vale a mais recente)
                            e Estrutura de Clientes_AAAAMMDD (bandeira do
                            cadastro), comuns ao DN e ao ROTA (D-83, 02/10/2026)
bases/Bases para tabelas dimensões/
                            Produtos; Hierarquia_Consolidada e
                            Hierarquia_Clientes_Faltando sem uso desde a D-83
data/raw/sell_in/           pasta do ciclo diario
data/staging/               cache de leitura (pode apagar; sera refeito)
data/curated/               modelo estrela + cubos  <- o que o painel consome
data/quality/               relatorio e CSVs de excecao da ultima execucao
logs/                       log completo, um por execucao
dashboard/template_v4.html  interface (editada a mao; template_v3 = retorno
                            rapido, exige o pipeline pre-D-51 via git)
dashboard/build/            os 73 paineis gerados
ferramentas/                diagnostico de cobertura, analise da bandeira RTM,
                            limpeza de paineis antigos (ver LEIA-ME de la)
config/config.yaml          todos os parametros
docs/                       esta documentacao
_arquivo/                   fora de uso (D-53); nada lido pelo pipeline
```

Apagar `data/` e `logs/` é seguro: `python run_pipeline.py` refaz tudo a partir
das bases.

> Quando a `VERSAO_CACHE` sobe (um leitor mudou; está documentado em
> `src/extract/cache.py`), a primeira execução relê os 29 Excel (~2 min) e
> reconstrói o staging sozinha; as seguintes voltam aos ~20 s. Não é defeito.

A auditoria completa do pipeline, com o que foi corrigido e o que ficou aberto
por decisão, está em [`AUDIT.md`](../AUDIT.md).
