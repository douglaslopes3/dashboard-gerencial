# 12 · Registro de decisões

Decisões tomadas durante a construção, com o motivo e o que as sustenta. Toda
premissa não confirmada está aqui — nenhuma virou suposição silenciosa no código.

---

## D-01 · O painel tem 5 páginas, não 3

**Contexto.** O §11 do prompt descreve três páginas (Visão Geral, Geográfica,
Preço Médio) e o próprio prompt reconhece que "a especificação original mistura
os elementos das páginas 2 e 3". O HTML de referência tem cinco abas: Visão
Geral, Geografia, Bandeiras, SKU e R$/kg.

**Decisão.** Vale a divisão do HTML: **5 páginas**.

**Por quê.** Bandeira (11.296 valores) e SKU (494) são rankings com lógica
própria — top N, maiores ganhos, maiores quedas. Empurrá-los para dentro da
página geográfica misturaria dois eixos que o leitor usa em momentos diferentes:
"onde caiu" e "o que caiu". A página de R$/kg fica isolada, como o §11.3 pede.

---

## D-02 · Ano fiscal rotulado `FY2026`, com `ANO_FISCAL = 2026`

**Contexto.** O §7 pede validar a convenção "set/2025 a ago/2026 = FY2026". O
projeto anterior usa o mesmo ano de fechamento internamente (`ANO_FISCAL = 2026`)
mas rotula `FY25/26`.

**Decisão.** `ANO_FISCAL = 2026` (ano de fechamento) e rótulo **`FY2026`**, como o
prompt pede. As duas colunas existem na `DIM_CALENDARIO`, e o prefixo vem de
`config/config.yaml → calendario.fiscal_prefixo`.

**Por quê.** A convenção do prompt é a que o leitor do painel vai usar. O número
por trás é o mesmo do projeto anterior, então qualquer conferência cruzada bate.
Trocar `fiscal_mes_inicio` para 1 iguala fiscal e calendário sem tocar em código.

---

## D-03 · Duas pastas de entrada, em vez de mover 95 MB de Excel

**Contexto.** O §5 do prompt sugere `novo_dashboard_gerencial_dori/data/raw/sell_in/`.
Os 28 arquivos já estavam em `bases/Sell In/`, dentro da própria pasta do projeto.

**Decisão.** O projeto mora na pasta que já existe. `data/raw/sell_in/` foi
criada como o §1 pede, e `config/config.yaml → fontes.sellin.pastas` lista **as
duas**. As duas são varridas.

**Por quê.** Criar a subpasta obrigaria a mover 95 MB de Excel dentro do OneDrive
ou a apontar o config para fora do projeto. Uma lista no config resolve com uma
linha, sem mover nada e sem caminho para fora. O operador pode largar o arquivo
novo em qualquer uma das duas.

---

## D-04 · `Qtde Faturado` é a métrica Caixas, sem fator de conversão

**Contexto.** O §6 permite Caixas por coluna existente **ou** por conversão
validada por SKU, e proíbe assumir fator padrão.

**Decisão.** Caixas = coluna `Qtde Faturado`, direto. **Nenhum fator de conversão
foi criado.**

**O que sustenta.** Para cada SKU, a mediana de `Peso Líquido ÷ Qtde Faturado`
foi comparada ao peso da caixa lido na descrição (`12X30X32G`, `24X400G`,
`12X1,010KG`): batem dentro de ±2% em **277 de 277** SKUs parseáveis, e **98,14%
das linhas** caem exatamente nesse valor. A linha `Total` de cada arquivo traz
`Qtde Faturado` — a própria fonte a trata como métrica.

**O que NÃO foi reaproveitado por isso.** O `01_dim_produto.py` do projeto
anterior derivava `UNID_POR_CAIXA` por regex sobre a descrição. Regex não entra
em produção aqui: a caixa é dado de origem.

---

## D-05 · Caixas é bruta e a tela diz isso

**Contexto.** 93,7% das linhas de devolução não têm `Qtde Faturado`, e as demais
trazem quantidade **positiva**. Valor e Volume são líquidos de devolução; Caixas
não.

**Decisão.** A métrica é publicada **como a fonte entrega**, com a ressalva no
rodapé do painel e no relatório de qualidade. Nada foi zerado, estimado nem teve
o sinal invertido.

**Por quê.** Qualquer "correção" seria dado inventado. O desvio é **0,28%**
(90.289 de 32.659.819 caixas) — pequeno, mas quem cruzar com o BI precisa saber
de onde ele vem. Ver GAP-04.

---

## D-06 · Canal fica **ausente** da tela, não desabilitado nem preenchido

> **Superada em 26/08/2026 pela D-19** — a base de canais chegou e foi integrada.

**Contexto.** Nenhuma base entregue traz canal ou subcanal (GAP-01).

**Decisão.** Não existe filtro nem quebra por canal. O eixo comercial exibido é o
que a fonte sustenta: **head → gerente**, com 99,98% de cobertura da receita.

**Por quê.** As três alternativas eram piores: (a) um filtro desabilitado sugere
que o dado virá em breve, e ele depende de um pedido ao BI; (b) preencher com
"NÃO INFORMADO" faria 100% da receita cair num balde; (c) derivar canal de
gerente ou bandeira seria regra inventada — proibida pelo §2.2. As opções, com o
tamanho medido de cada uma, estão em GAP-01, para o Douglas decidir.

---

## D-07 · O painel é um HTML autocontido, gerado por Python

**Contexto.** O §4 manda verificar o ambiente antes de escolher a tecnologia.
Medido: `duckdb`, `streamlit`, `plotly`, `dash` e `polars` **não estão
instalados**; `pandas`, `pyarrow`, `openpyxl`, `python-calamine`, `numpy` e
`PyYAML` estão.

**Decisão.** HTML estático com dados e biblioteca de gráfico **embutidos**.

**Por quê.** O painel é aberto por duplo clique a partir do OneDrive. Streamlit e
Dash exigem instalação no consumidor e um servidor rodando. E `file://` bloqueia
`fetch` de arquivo local — um painel que busca o JSON por rede simplesmente não
abre. É também o modelo que já funciona nesta empresa: os Scorecards de canal são
HTML autocontidos.

**Consequência.** O `Chart.js` do protótipo vinha de CDN, o que o torna inútil
sem internet. Aqui o bundle é **embutido**: o arquivo gerado faz **zero
requisições de rede** (conferido: nenhuma ocorrência de `src="http`, `fetch(`,
`XMLHttpRequest` ou `WebSocket` no HTML final).

---

## D-08 · Ranking de bandeiras nominal nas 300 maiores, com balde para o resto

**Contexto.** 11.296 bandeiras. Cruzá-las todas com categoria, gerente e UF
custaria muito e entregaria ranking irrelevante.

**Decisão.** As **300 maiores** aparecem nominalmente; as outras 10.996 entram
agregadas em `DEMAIS BANDEIRAS (10.996 bandeiras)`.

**O que sustenta.** Medido, em JSON real:

| Universo | Cobertura | Cubo cruzado |
|---|---:|---:|
| top 100 | 57,4% | 1.240 KB |
| top 200 | 68,0% | 1.965 KB |
| **top 300** | **73,4%** | **1.758 KB** |
| top 500 | 78,9% | 3.634 KB |

O protótipo usava 200 (68%). O corte está em
`config/config.yaml → dashboard.top_bandeiras` — subir para 500 custa +1,9 MB e
ganha 5,5 pontos.

**Por que o balde importa.** Sem ele, o total do painel deixaria de bater com o
total da fato. Com ele, **toda soma continua reconciliando** — as bandeiras
pequenas só não aparecem no ranking.

---

## D-09 · O cubo de SKU cruza com head e UF, não com gerente

> **Superada em 26/08/2026 pela D-21** — o eixo virou (head, canal).

**Contexto.** O §11 pede recorte por SKU também na página geográfica.

**Decisão.** `CUBO_SKU` no grão `ANO_MES × SKU × HEAD × UF`.

**O que sustenta.** Medido, em JSON real:

| Alternativa | JSON | SKU responde a |
|---|---:|---|
| `AM × SKU × HEAD` | 442 KB | período, categoria, head |
| `AM × SKU × GERENTE` | 1.045 KB | + gerente, − UF |
| **`AM × SKU × HEAD × UF`** | **4.388 KB** | **período, categoria, head, UF** |
| `AM × SKU × GERENTE × UF` | 7.852 KB | tudo |

Escolhida a terceira: atende o requisito da página geográfica por 3,3 MB a menos
que a completa. O que fica de fora — cruzar SKU com **gerente** e com
**bandeira** — está **avisado na tela** quando esses filtros estão ativos junto
com um filtro de SKU. O painel não finge que o filtro foi aplicado.

---

## D-10 · Os números vão para o JSON como inteiros escalados

**Decisão.** Receita em centavos, peso em gramas, caixas em centésimos.

**Por quê.** Inteiro serializa mais curto que float com decimais — e,
principalmente, a soma volta **exata**. Arredondar para reais faria a soma das
72 mil linhas do cubo divergir da fato em alguns milhares de reais: invisível na
tela, mas suficiente para a reconciliação nunca fechar. Reconciliação que não
fecha vira reconciliação que ninguém olha.

**Conferido.** As três métricas do painel batem com a `FATO_SELLIN` com erro
relativo abaixo de `4e-10`. As quebras por categoria e por head batem **até o
centavo** (ver `docs/11_RESULTADO_DOS_TESTES.md`, T-04).

---

## D-11 · Seleção de meses vazia mostra tela vazia

**Contexto.** Na primeira versão, "Nenhum" caía de volta em "todos os meses" —
o botão era indistinguível de "Todos".

**Decisão.** Seleção vazia é seleção vazia: a tela diz *"Nenhum mês selecionado"*.
Os meses vêm **pré-selecionados** ao abrir e a cada troca de base ou de ano.

**Detalhe que custou uma medição.** Em "Meses vs LY", pré-selecionar a série
inteira daria **24 meses de atual contra 12 de LY** — dois anos comparados com
um, exibido como se fosse válido. O padrão passou a ser o **último ano fiscal**,
que tem LY completo. Marcar os 24 continua possível, e a linha de estado avisa:
*"LY: 12 de 24 meses cobertos"*.

---

## D-12 · Ano fiscal e ano calendário nunca filtram ao mesmo tempo

**Contexto.** O §10 pede documentar o comportamento quando os dois são usados
juntos.

**Decisão.** O seletor de **base de comparação** decide qual manda. O outro fica
visível e **desabilitado**, com a nota do porquê.

**Por quê.** Escolher "FY2026" e "2025" ao mesmo tempo produziria a interseção
set–dez/2025 — um período que ninguém pediu e que ninguém consegue explicar
depois.

---

## D-13 · Variação % com LY negativo usa o módulo no denominador

**Decisão.** `(atual − LY) / |LY|`.

**Por quê.** Com o denominador com sinal, um LY negativo (devolução líquida) faz
uma **alta** aparecer como queda. Com o módulo, o sinal da variação segue o
sinal da diferença, que é o que o leitor espera. LY zero ou nulo devolve `null`,
e a tela mostra **`n/d`** com tooltip — nunca `∞`, `NaN` ou `#DIV/0!`.

---

## D-14 · Cliente e SKU sem cadastro entram no fato

**Decisão.** 71 clientes sem head (R$ 421 mil) entram como `NÃO ATRIBUÍDO`;
7 SKUs fora do cadastro (R$ 910 mil) entram com `FORA_DO_CADASTRO = true`.

**Por quê.** Descartar faria o total do painel deixar de bater com o total da
fonte — e quem cruzasse com o BI concluiria que o painel está errado. Os dois
saem listados em `data/quality/`.

---

## D-15 · Piso de cobertura da estrutura comercial aborta o pipeline

**Decisão.** Cobertura de head sobre a receita abaixo de 95% **derruba** a
execução (`validacao.cobertura_minima_head`).

**Por quê.** O de-para traz `Cód. cliente` zero-preenchido (`0001010846`) e o
sell-in traz o número puro (`1010846`). Sem `lstrip("0")` o join casa com **zero**
clientes — e casa em silêncio: o resultado fica todo nulo e o pipeline segue,
com o painel inteiro em "NÃO ATRIBUÍDO". Medido hoje: **99,98%**.

---

## D-16 · Rótulo de head vago não foi corrigido

**Contexto.** A base traz `Maykon - 2600`; o protótipo mostra `Vago`. São
R$ 466,5 mi (20,6% da receita).

**Decisão.** **Nada foi corrigido.** O valor de origem é exibido como está. A
chave `dimensoes.estrutura_comercial.correcoes_head` existe no config, vazia.

**Por quê.** É decisão do Comercial, não do ETL. Quando alguém preencher a chave,
a troca acontece **e sai registrada** no log e no relatório de qualidade. Ver
GAP-03.

---

## D-17 · `JUBES FRUIT SNACKS` e as duas categorias a mais ficaram como estão

**Contexto.** O §9 lista `JUBES FRUIT SNACK` (singular); a base traz
`JUBES FRUIT SNACKS`. A base ainda tem `NAO INFORMADO` (158 linhas) e
`DISPLAY/MAT.PROMOCIONAL` (8 linhas), que a lista não prevê.

**Decisão.** A base manda. Nada foi renomeado nem agrupado. Os três saem no
relatório `data/quality/valores_nao_reconhecidos.csv`.

**Por quê.** A lista do §9 é gabarito de conferência, não fonte. Nenhum erro de
grafia real (tipo `CHOLOCATE`) foi encontrado nas 3,08 mi de linhas.

---

## D-18 · Sem carga incremental

**Decisão.** Reprocessamento completo a cada execução.

**Por quê.** A fonte não tem chave de controle segura: a competência vem do
**conteúdo** (`Ano mês`), nunca do nome do arquivo — e o projeto anterior já se
queimou com um arquivo cujo nome dizia um mês e o conteúdo dizia outro. Sem chave
segura, o §3 do prompt manda priorizar correção e simplicidade. Custo medido:
**107s a frio, 13s com o cache de leitura quente** para 3,08 mi de linhas.

---

# Devolutiva de 26/08/2026 — decisões da segunda onda

## D-19 · Canal integrado pela base `bases/Canais/Canais.xlsx`

**Contexto.** A devolutiva entregou a base de canais. Perfilada antes de codar:
43.073 clientes, chave `Cód. cliente` (zero-preenchida), 9 canais, 43 subcanais,
rodapé de `Filtros aplicados` como no sell-in.

**Decisão.** Canal e subcanal entram como **atributos do cliente** na
`DIM_CLIENTE` — o modelo estrela não muda. Canal vira filtro global e dimensão
de quebra em todas as páginas.

**O que sustenta.** Cobertura medida: **100,0000%** dos 16.131 clientes e dos
R$ 2,26 bi, **zero órfãos**. Zero clientes com dois canais. O mesmo piso de
cobertura da estrutura (95%) protege o join, porque o arquivo traz o código no
mesmo formato zero-preenchido que já derrubou join uma vez.

**Sobra declarada.** 9 canais na base contra 7 esperados pelo §9
(`KEY ACCOUNT NACIONAL`, com receita zero no período, e `KEY ACCOUNT REGIONAL`,
sem cliente com faturamento). Nada foi agrupado — saem no relatório de valores
não reconhecidos. Subcanal fica armazenado na `DIM_CLIENTE` (14 com receita) e
fora da interface: a devolutiva pediu canal, e subcanal entra quando alguém
pedir, sem reprocessar nada além do cubo.

## D-20 · O eixo comercial do cubo virou o PERFIL do cliente

**Contexto.** Canal e Projeto precisavam entrar no cubo principal sem explodi-lo.

**Decisão.** O par `(head, gerente)` virou o **perfil**
`(head, gerente, canal, projeto)` — um índice só por linha.

**O que sustenta.** Medido: **104 perfis** distintos. Guardar os quatro como
índices separados multiplicaria o cubo por combinações que não existem; guardar
menos perderia filtros. Custo real: cubo principal de 72.378 → **90.644 linhas**
(2,47 → 3,13 MB de JSON).

## D-21 · O cubo de SKU ganhou canal e o eixo virou (head, canal)

**Contexto.** Com canal como dimensão primária, a página de SKU ignorá-lo seria
mentira silenciosa.

**Decisão.** `CUBO_SKU` no grão `ANO_MES × SKU × (HEAD, CANAL) × UF` — 31 pares.

**O que sustenta (medido em JSON real):**

| Alternativa | Linhas | JSON | Perde |
|---|---:|---:|---|
| manter só HEAD | 208.716 | 6,4 MB | canal na página de SKU |
| trocar HEAD por CANAL | 318.235 | ~9,5 MB | head (regressão) |
| **HEAD + CANAL** | **368.699** | **~11,0 MB** | nada do que já funcionava |
| HEAD + CANAL + PROJETO | 418.831 | ~12,4 MB | nada, por +1,4 MB |

Escolhida a terceira: preserva tudo e adiciona canal por +4,6 MB. Projeto ficou
fora do cubo de SKU (a visão de Projetos vive no cubo principal, que é o que a
devolutiva pede) e entrou na lista de filtros **avisados** quando combinados com
SKU — junto de gerente e bandeira. O painel foi de 8,94 para **14,28 MB**;
continua um arquivo só, por duplo clique, sem rede.

## D-22 · Ticket médio = preço médio; o KPI mensal chama o que é

> **Adendo 26/08 (2ª devolutiva):** a pedido do Douglas, a descrição da decisão
> **saiu da interface** — o card voltou a chamar-se só "Preço médio" e a nota da
> página R$/kg ficou apenas com a definição técnica. A decisão vive aqui.

**Contexto.** A devolutiva encerrou o GAP-02: as duas fórmulas do protótipo eram
métricas diferentes com nomes trocados.

**Decisão.** (a) Ticket médio e preço médio são **a mesma métrica**
(`Σvalor ÷ Σpeso`), e a interface declara isso no card e na página R$/kg.
(b) Entrou o card **"Faturamento médio/mês"** (`receita ÷ nº de meses do
período`), com o rótulo dizendo exatamente o que a fórmula calcula.
(c) Nenhuma divisão por cliente comprador ou pedido — as contagens não existem
no modelo.

## D-23 · Maykon - 2600 → Vago - 2600, pelo mecanismo declarado

**Contexto.** O Comercial confirmou a vacância (devolutiva, item 3).

**Decisão.** A troca entrou **no config**, não no código
(`correcoes_head: {"Maykon - 2600": "Vago - 2600"}`), e sai registrada no log a
cada execução. Conferido: R$ 466.521.780,95 trocaram de rótulo, total geral
inalterado em R$ 2.260.853.914,86. O código `2600` fica no rótulo pela
convenção dos pares (`Izabela - 2650`, `Michel - 1000`).

## D-24 · Quantidade negativa: comportamento confirmado, descrição divergente

**Contexto.** A devolutiva pede: não filtrar, não aplicar ABS, manter o sinal,
somar antes de dividir — exatamente o que o pipeline já fazia.

**Decisão.** Nenhuma mudança de código. A divergência de **descrição** ficou
registrada no GAP-04: a devolutiva fala em quantidade negativa na devolução, mas
o medido é quantidade **nula** em 93,7% das devoluções e **positiva** nas demais
— `Qtde Faturado` nunca é negativa na base entregue.

## D-25 · Projeto como dimensão de primeira classe, sem de-para novo

**Contexto.** A devolutiva pediu a visão por Projetos e afirmou que o dado já
existe nas bases.

**Decisão.** Confirmado: coluna `PROJETO` do `DePara_Estrutura_Comercial.xlsx`,
já carregada na `DIM_CLIENTE` (8 valores — `Projeto L`, `Sem mudança`,
`TOP ATACADOS`, `Clientes Novos`, `KAR Phase 1/2`, `Varejo PR (temporário)`,
`White Spaces`). Entrou no perfil do cubo, no filtro global e nas quebras de
todas as páginas, **convivendo** com os filtros atuais — a própria devolutiva
responde a questão 3 ("do mesmo modo que Categoria / Canal / Head"). Nenhum
de-para manual foi criado.

## D-26 · Os 71 "NÃO ATRIBUÍDO" são do Vago — correção vai para a ORIGEM

**Contexto.** 2ª devolutiva de 26/08: os 71 clientes sem linha no de-para de
estrutura (R$ 421.421,67) também pertencem ao Vago.

**Decisão.** A correção é **na origem**, não no ETL: os 71 códigos precisam
entrar no `DePara_Estrutura_Comercial.xlsx`. Foi gerado
`docs/pedidos/incluir_no_DePara_estrutura.xlsx` com as 71 linhas **no layout
exato do de-para**, `Novo Head` já preenchido com `Vago - 2600` e
gerente/supervisor em branco para o Comercial completar (aba de contexto traz
nome, bandeira, canal, UF e receita de cada um). Coladas as linhas, o pipeline
absorve sozinho na execução seguinte — o cache invalida pelo mtime do arquivo.

**Por que não corrigir no ETL:** o de-para tem dono (Comercial). Uma emenda
local que não voltasse ao arquivo-mestre seria desfeita em silêncio na próxima
atualização dele — o painel regrediria sem ninguém perceber.

## D-27 · KEY ACCOUNT NACIONAL/REGIONAL não são canais de cliente — origem

**Contexto.** 2ª devolutiva: o Douglas apontou que os dois não são canais dos
clientes. A verificação confirmou a leitura dele:

* os valores vêm da própria coluna `Canal` do `Canais.xlsx` (88 linhas `KA`,
  2 linhas `KR`);
* as 2 linhas `KR` são **construções de P&L**, não clientes — os "subcanais"
  delas são literalmente `Orçado KR` e `Rateio P&L KR`;
* dos 88 `KA`, só **3** tocam o sell-in — MAKRO LJ 36 e duas razões WMS
  (Walmart) — todos com **R$ 0,00** líquidos no período (classificação legada).

**Decisão.** Impacto no painel: uma linha zerada. A correção é **na origem**
(BI reclassificar/remover os códigos no arquivo de canais) — a lista dos 3 está
em `docs/pedidos/clientes_canal_key_account.csv`. Nada foi reclassificado no
ETL: mapear os 3 por palpite seria regra inventada, e o custo de esperar a
origem é zero real.

---

# Solicitação 02 (26/08/2026) — funcionalidades

## D-28 · A base de comparação tem DOIS estados; o LY está embutido

**Contexto.** O botão "Meses vs mesmo período LY" era redundante (Solicitação
02, item 1).

**Decisão.** `BASES` ficou com `fis` e `cal`. O período passa a ser **exatamente
os meses selecionados**, e o anterior são **os mesmos meses do ano anterior**
(pareados por `ANO_MES_LY`, junção — nunca deslocamento). O botão decide qual
ano emoldura a lista de meses e como o card de YTD acumula; não muda a conta.

**O que isso corrigiu de quebra:** antes, em YTD Fiscal com 3 meses marcados, as
tabelas mostravam o acumulado fiscal inteiro — a seleção parcial era ignorada.
Agora 3 meses selecionados comparam com os mesmos 3 do LY (aceite conferido:
set–nov/25 R$ 316,15 mi × set–nov/24 R$ 302,07 mi), e a seleção cheia devolve o
mesmo total de sempre (R$ 1.127.251.765,81). Os branches do terceiro estado
foram **removidos**, não comentados.

## D-29 · Exportação CSV/XLSX genérica, com dado CRU

**Decisão.** Todas as 9 tabelas (mais o drill) exportam por **uma função
genérica**: cada render registra a versão **crua** dos dados (número é número —
sem "R$", sem separador de milhar, decimal com ponto; % em pontos percentuais),
e a formatação pt-BR fica só na tela. O nome do arquivo carrega tabela, recorte,
base e último mês (`sku-amendoim_ytd-fiscal_2026-08.xlsx`). Exporta **o que está
na tela** — todos os filtros ativos valem.

**Como o XLSX nasce sem biblioteca:** o painel não pode depender de rede, então
o `.xlsx` é um zip *stored* mínimo escrito à mão (5 arquivos XML, CRC32
próprio). Validado fora do navegador: `zipfile.testzip()` OK e `openpyxl` lê
com os valores tipados como `float`. Tabela vazia limpa o registro — não
exporta dado velho.

## D-30 · Drill-down Categoria → SKU; os demais ficam bloqueados

**Decisão.** Na quebra por Categoria do Detalhamento, a linha vira clicável e
abre os SKUs da categoria: mesmo período, mesma base, mesmos filtros (head,
canal, UF — os que a camada de SKU conhece), **ordenado pela maior queda**,
com "← voltar" e exportação própria. O detalhe re-renderiza quando um filtro
muda — é um recorte, não uma tela nova.

**O que NÃO foi feito, por instrução expressa (B1–B3):** Canal → Cliente,
Projeto → Cliente e Head → Gerente. Cliente não é dimensão de nenhum cubo, e a
Solicitação 02 proíbe assumir origem, chave ou estratégia de carga. Registro
para a decisão futura, medido: **(a)** a hierarquia head → gerente **já existe
no cubo principal** como dado do de-para (o par viaja no PERFIL — a quebra
"Gerente" mostra `gerente · head` hoje), então o drill Head → Gerente não
precisa de dado novo, só da liberação de B2; **(b)** para Cliente, o grão
`mês × cliente` tem ~16 mil clientes × 24 meses — embutir multiplicaria o HTML;
a alternativa é um arquivo de detalhe ao lado do painel, carregado sob demanda,
o que quebra o "um arquivo só, duplo clique". É exatamente a decisão B3, e ela
é de quem coordena.

## D-31 · Drill Head → Gerente (B2 liberado em 26/08/2026)

**Contexto.** O Douglas liberou o B2: "a hierarquia já vem do de-para".

**Decisão.** Na quebra por Head do Detalhamento, a linha abre os **gerentes do
head clicado** — mesmo mecanismo do drill de categoria, generalizado
(`F.drill = {tipo, k}`). A hierarquia **não é inferida**: cada cliente carrega
head E gerente no `DePara_Estrutura_Comercial.xlsx`, e o par viaja no PERFIL do
cubo principal.

**Regras do recorte:** respeita canal, categoria, projeto, bandeira e UF (é o
cubo principal — aqui todos existem); ignora o filtro de head (o escopo é o head
clicado) e o de gerente (esconderia quem derrubou o resultado), declarando os
ignorados na nota. Com filtro de SKU ativo o detalhe diz que não existe (a
camada de SKU não tem gerente), em vez de fingir.

**Conferido no aceite:** gerentes de Ademir somam **R$ 440,02 mi** = linha
agregada; ordenado pela maior queda (Gerente Sul/CO, −R$ 14,85 mi, primeiro);
com CASH & CARRY filtrado o total vai a **R$ 10,66 mi** — o mesmo valor
Ademir × CC medido na fato na integração do canal. Exportação própria
(`gerentes-ademir_ytd-fiscal_2026-08.xlsx`).

**Seguem bloqueados:** Canal → Cliente e Projeto → Cliente (B1/B3 — cliente não
é dimensão de cubo nenhum).

## D-32 · Comparativo LY pareado mês a mês (27/08/2026) — agregado endurecido pela D-35

**Contexto.** Com a série começando em set/24, todo período que inclui meses
sem par no ano anterior comparava o acumulado inteiro contra só os meses de LY
existentes: "YTD Calendário 2025" somava jan–dez/25 (12 meses) contra
set–dez/24 (4 meses) — crescimento falso; os rankings e KPIs herdavam o mesmo
viés. O Douglas definiu a regra: **só entra na comparação o mês que tem o
mesmo mês no ano anterior** (ago/25 sem ago/24 na série fica sem comparativo).

**Decisão.** Em todas as visões (KPIs, Comparativo YTD, tabelas, quebras,
rankings, preço médio e drills): a coluna/valor **Atual** continua sendo o
período selecionado inteiro; **LY, Δ e Δ%** são calculados exclusivamente
sobre os meses **pareados** por `ANO_MES_LY`, nos dois lados da conta. Nas
visões por período (mês/trimestre/semestre), o grupo só tem comparativo
quando **todos** os seus meses têm par — comparar um trimestre com 1/3 dele
seria comparação falsa. Quando o pareamento é parcial, a linha de estado
declara ("comparativo pareado: N meses") e os totais levam `*` com tooltip;
a exportação nomeia a linha de total ("Δ sobre os meses/períodos pareados").

**O que isso corrigiu de quebra.** Os drills (Head → Gerente e Categoria →
SKU) acumulavam atual e LY num "ou" exclusivo por mês: quando um mês estava
no período atual E era o LY de outro mês selecionado (ex.: "Todos" com 24
meses), o lado LY do drill perdia esses meses. Os acumuladores passaram a
somar de forma independente.

**Consequência declarada.** Quando o pareamento é parcial, o Δ exibido não é
`Atual − LY` das colunas visíveis (o Atual é cheio; o Δ é pareado) — por isso
o `*` e o tooltip. Com cobertura total (ex.: FY2026), nada muda: todos os
números ficam idênticos aos de antes.

## D-33 · Correções da auditoria aplicadas; três itens ficam abertos por decisão (27/08/2026)

**Contexto.** A auditoria (`AUDIT.md`) levantou 48 achados em cinco camadas,
com zero dado errado armazenado.

**Decisão.** Foram **aplicados** (commits `ce5216e` → `ceff091`): todo o grupo
de risco de dado errado exceto A8 (A1–A7, A9–A15, com A13 virando perda
assumida documentada em docs/06 §2.1), as melhorias de performance B1, B3, B4,
B5, B7 e B8, e todas as limpezas C1–C16. Validado: 29/29 unitários, 6/6
cenários, os 4 totais de controle idênticos ao centavo no painel, render em
44 ms, fato 20,3 MB. A duplicata de mês passou a ser barrada **na ingestão**
(A3: mesmo recorte = cópia duplicada), com o grão como segunda defesa —
o cenário T-07 foi atualizado para refletir isso.

**Ficam abertos, de propósito:**

| Item | Por quê não foi aplicado |
|---|---|
| **A8** (SCD: a história é classificada pela estrutura comercial de hoje — 50,1% da receita é anterior a ela) | é decisão de leitura de negócio; aguarda o Comercial confirmar "carteira atual olhada para trás" e, se preciso, um de-para com vigência |
| **B2** (tirar `data/` e `dashboard/build/` do OneDrive — ~54 MB de churn por execução) | é configuração do sincronizador na máquina de quem opera, não código |
| **B9** (cortar o eixo UF do cubo de SKU: −9,5 MB no painel) | decisão de produto — perde SKU×UF; trade-off documentado no AUDIT |
| **B6/B10** | veredito da própria auditoria: não vale mexer |

## D-34 · Troca da base de estrutura: `Hierarquia_Consolidada.xlsx` + complemento, rótulos concatenados (28/08/2026)

**Contexto.** O Comercial passou a manter a hierarquia na
`Hierarquia_Consolidada.xlsx` (14.054 linhas, granularidade cliente ×
vendedor, 4 níveis N1–N4 com código/papel/nome, cabeçalhos com quebra de
linha interna). Medido antes da troca: a base nova é **subconjunto estrito**
da anterior — 13.448 clientes contra 16.060 — e cobre só **93,95%** da
receita (94,80% no FY2026; 554 dos ausentes faturaram em ago/2026), abaixo do
piso de 95%. Os 2.612 clientes ausentes carregam R$ 136,4 mi em 24 meses.

**Decisão (Douglas, 28/08/2026).**

1. A `Hierarquia_Consolidada.xlsx` é a base oficial daqui para a frente.
2. Cada nível vira **um rótulo concatenado** `código - papel - nome`
   (ex.: `20 - ATACADO - ADEMIR TAVARES`), parte vazia omitida — as 106
   linhas de gerente sem nome ficam com código+papel. `ATENDIMENTO_PONTA`
   deixa de existir (nunca chegava ao painel). O N4 (vendedor) **não** é
   ingerido; a deduplicação por cliente confere conflito N1–N3 (zero, medido).
3. Os 2.612 ausentes entram pelo **`Hierarquia_Complemento.xlsx`** (mesmo
   layout), gerado pelo mapa de migração dos 13.448 clientes comuns
   (supervisor da base anterior → N3 novo dominante; 2.582 com dominância
   ≥ 90%; os 30 restantes entram pelo dominante mesmo assim, marcados).
   **Pendente de validação do Comercial** — o destino certo é a base oficial
   incorporá-los; a oficial sempre vence e o complemento esvazia sozinho.
4. `[VAGO]`/`[Vago]` (mesmo código 30) e o gerente 33000 com/sem nome:
   padronizados para `[VAGO]` por **correção declarada** no config (436 + 783
   linhas corrigidas, no log). A correção do Maykon (base anterior) saiu.
5. O gabarito `valores_esperados.head` guarda o rótulo completo e a
   comparação do relatório de qualidade virou igualdade total (o corte no
   ` - ` da convenção antiga pegaria só o código). `VERSAO_CACHE` 3 → 4.

**Validação da troca.** Cobertura 99,98% (idêntica à anterior); totais de
controle ao centavo (R$ 2.260.853.914,86 · 161.321,49 t · 32.659.819 cx);
os mesmos 71 clientes `NÃO ATRIBUÍDO`; receita por head reconcilia com a
estrutura anterior (Vago 466,5 mi idêntico; demais com migrações pequenas);
29/29 unitários, 6/6 cenários. Perfis do cubo: 104 → 110.

**Consequência declarada.** A história inteira (24 meses) passa a ser lida
pela hierarquia nova — mesma regra do A8 ("carteira atual olhada para trás"),
que segue aberto.

**Complemento sem PROJETO (Douglas, 28/08/2026, mesma data).** O primeiro
complemento herdava o PROJETO da base anterior, o que trazia de volta rótulos
que a base nova abandonou (`Clientes Novos`, 2.422 clientes). Decidido: o
complemento vai com `PROJETO` **em branco** — o eixo do painel mostra só os
6 projetos da hierarquia oficial, e os 2.612 clientes ficam `NÃO ATRIBUÍDO`
no recorte de projeto até o Comercial classificar (o valor antigo segue
visível na coluna de apoio do arquivo). Head/gerente/supervisor continuam
mapeados. O pipeline **não depende da base anterior**: ela foi usada uma
única vez, offline, para gerar o complemento (e já foi apagada da pasta).

## D-35 · Comparativo LY tudo-ou-nada no agregado + retoques de interface (28/08/2026)

**Contexto.** Mesmo com o pareamento da D-32 (Δ e Δ% sempre par a par), a
tela de "ano calendário 2025" mostrava **Atual R$ 1,17 bi (12 meses) ao lado
de LY R$ 375,82 mi (4 meses)** — matematicamente pareado, visualmente uma
comparação de 12 contra 4. O Douglas: *"não adianta comparar 2025 completo
com 2024 sendo que em 2024 só tivemos alguns meses de saldo"*.

**Decisão.** O comparativo **agregado** (KPIs, Comparativo YTD, totais de
tabela, rankings de ganho/queda, totais de drill) passa a ser
**tudo-ou-nada**: só existe quando TODOS os meses selecionados têm par no ano
anterior. Com par incompleto, LY/Δ/Δ% viram `n/d` e a linha de estado diz
o porquê e o caminho ("selecione apenas os N meses pareados"). As **quebras
por mês/período continuam comparando cada grupo com par completo** (regra da
D-32, mantida) — a linha de nov/25 compara com nov/24 mesmo quando o total
não compara. Implementação: `periodo()` e `ytdFiscal/ytdCalendario` devolvem
o par vazio quando incompleto; todo o resto da tela já lia esses campos.

**Junto, no mesmo turno (pedidos da mesma conversa):**

1. **Evolução vira gráfico de BARRAS com rótulo de dados** (era linha).
   Rótulo desenhado à mão no `afterDatasetsDraw` — o painel continua sem
   plugin externo e sem rede. Período sem par fica sem a barra clara.
2. **Bloco de filtros reestilizado** ("está tudo muito branco"): painel com
   fundo azulado em degradê, rótulos das linhas em azul, chips com tinta
   leve, divisórias tracejadas entre as linhas.
3. **Bug real do "voltar ao agregado" corrigido**: o atributo `hidden` perde
   para o `display:grid` da classe `.grid`, então o card do drill **nunca
   sumia** — ficava visível com o conteúdo velho. Corrigido com
   `[hidden]{display:none !important}`; o fechar também rola a vista de
   volta à tabela agregada.

**Validação.** Reproduzido e conferido no navegador: cal/2025 → KPIs `n/d
(par incompleto)` + estado explicando; só set–dez/25 selecionados → KPI
compara R$ 103,47 mi × 111,23 mi (−7,0%); linhas mensais mantêm LY
individual; drill abre e fecha de verdade; FY2026 segue idêntico (12/12
pareados, nada mudou nos números).

**Ajustes do mesmo dia (2ª rodada, pedidos do Douglas):**

1. **Δ% no gráfico de Evolução**: linha laranja com a variação de cada
   período contra o MESMO período do ano anterior, em eixo próprio à
   direita, com rótulo em cada ponto colorido pelo sinal. Período sem par
   completo fica sem o ponto (mesma regra da barra clara).
2. **Média do período no gráfico**: linha tracejada com a média simples dos
   períodos exibidos, declarada na nota do card — para R$ no mês é o mesmo
   número do KPI "Faturamento médio/mês".
3. **Chips de ausência por último**: `NÃO ATRIBUÍDO` (head/gerente/projeto),
   `NAO INFORMADO` (categoria), `SEM CANAL`/`SEM BANDEIRA`/`SEM UF` vão
   sempre para o fim da lista de botões; o resto segue alfabético pt-BR.
   Conferido no navegador: último chip de cada linha correto e Δ% do
   gráfico batendo com a tabela "Evolução por período" (set/25 −7,0%).

## D-36 · Descarte declarado de linhas 100% zeradas; displays/pallets ficam (28/08/2026)

**Contexto.** O canal `KEY ACCOUNT NACIONAL` aparecia no painel inteiro
(chip + linha do Detalhamento, tudo R$ 0,00) sustentado por 19 linhas de
nov/2024 com receita, peso e caixas zerados/nulos — remessas simbólicas de 3
clientes (Makro AM e duas filiais WMS/Sam's). O Douglas: *"esse canal não
deveria existir aqui"*. Medido o universo: **3.133 linhas 100% zeradas** nos
28 arquivos, e **39 clientes** que só existiam por linhas assim.

**Decisão (Douglas, 28/08/2026).**

1. Linha com as **três métricas zeradas/nulas** é **descartada na ingestão**
   (`fontes.sellin.descartar_linhas_100_zeradas`, ligada). Ela não carrega
   fato mensurável, mas cria cliente/canal/SKU fantasma nos eixos. O descarte
   é contado no log e no §1 do relatório de qualidade, por arquivo. Linha com
   QUALQUER métrica diferente de zero fica — negativa inclusive (devolução).
   A reconciliação contra o gabarito não se altera: as linhas somam zero.
2. **DISPLAY/MAT.PROMOCIONAL e PALLETS (NAO INFORMADO) FICAM no painel**
   (opção C, deliberada): têm valores reais (−R$ 23,3 mil; +R$ 50,9 mil e
   54,8 t de peso, 100% SPAL/DISTRIBUIDOR) e descartá-los quebraria a
   reconciliação com a fonte. A correção certa é na origem — se incomodar,
   abrir pedido ao BI para tirar esses 6 SKUs da extração.

**Efeito medido.** Fato 3.085.119 → **3.081.986** linhas (−3.133); clientes
16.131 → **16.092** (−39); canal `KEY ACCOUNT NACIONAL` sumiu do painel
(ficam os 7 do gabarito, cobertura de canal segue 100,0000%); os 71 sem
estrutura seguem os mesmos. **Totais idênticos ao centavo**
(R$ 2.260.853.914,86 · 161.321,49 t · 32.659.819 cx). `VERSAO_CACHE` 4 → 5.
30/30 testes (novo: `test_linha_100_zerada_e_descartada_e_contada`).

---

## D-37 · Painel V3 em arquivo novo, lote 1: confiabilidade e performance (31/08/2026)

**Contexto.** Mesmo arranjo do v1 → v2: o Douglas pede arquivo novo para poder
voltar atrás. `template_v2.html` fica intacto; `config.yaml` passa a gerar o v3
(commit `f6835c0`).

**Decisão.** `dashboard/template_v3.html`, com: barra de Período
(Mês|Trimestre|Semestre|Acumulado) que ESCREVE na seleção de meses (F1-A);
aviso da página de SKU vira aviso da PÁGINA, não só do filtro de SKU (F1-C);
balde "DEMAIS BANDEIRAS" fora dos destaques e cobertura das nominais
recalculada sob o recorte (F1-D); renders de SKU/drills no índice por mês
(F1-E); tabelas de SKU/Bandeiras/Detalhamento viram matriz por período,
limitada aos 12 períodos recentes (F1-G/L3). Nenhum número de negócio muda.

**Por quê.** Os motivos por item estão no cabeçalho do próprio template, que é
o registro de engenharia; aqui fica o marco e o vínculo com o commit.

---

## D-38 · Granularidade unificada no seletor "Ver por", com "Ano" e período parcial declarado (01/09/2026)

**Contexto.** A varredura de 31/08 reproduziu o bug: com Período=Mês (ago/26) e
o chip "Agrupar por"=Trimestre (escondido no painel de filtros), o gráfico
rotulava FY2026-T4 com 1 mês de dados (R$ 105,1 mi contra R$ 313,5 mi do T4
real). Dois controles com os mesmos rótulos dessincronizavam. O Douglas
aprovou o mapa da varredura e pediu a visão de período em QUATRO
granularidades: mês, trimestre, semestre e ano, com o mesmo layout e a mesma
conta, mudando só agrupamento e rótulos.

**Decisão (Douglas, 01/09/2026).**

1. O chip "Agrupar por" SAI do painel de filtros. A granularidade é só o
   seletor **"Ver por"** (Mês|Trimestre|Semestre|**Ano**) na barra de Período;
   os atalhos de Período continuam escrevendo a seleção e sincronizando a
   granularidade (regra L3 mantida).
2. Grupo com menos meses que a granularidade pede (`TAM_GRUPO`: 1/3/6/12) sai
   rotulado **"(parcial)"** no gráfico e nas tabelas, e com `*` nas colunas da
   matriz. Nunca exibir período incompleto como cheio.
3. Os controles descem para perto do conteúdo: bloco de filtros + barra de
   Período + linha de estado logo abaixo do gráfico de Evolução (pedido
   literal). No mesmo dia, pedido seguinte: o painel de filtros passa a
   existir em TODAS as abas. É UM nó no DOM, movido pela `posicionarFiltros()`
   na troca de aba (abaixo do gráfico na Visão Geral, topo nas demais); as
   cópias avulsas da barra de Período saíram.

**Validação.** No navegador, sem erros de console: o cenário do bug agora
mostra "FY2026-T4 (parcial)"; "Ver por: Ano" agrupa em FY2025/FY2026 no
gráfico, nas tabelas por período e nas colunas da matriz; filtro aplicado de
dentro da aba Bandeiras reage na hora. Commits `3e4169c` e `ba791a4`.

---

## D-39 · Barras do comparativo em ordem cronológica: ano anterior à esquerda, atual à direita (01/09/2026)

**Contexto.** Pedido da fase 2: "as barras estão na ordem invertida". Na
confirmação, o Douglas definiu: **o ano atual deve vir à direita** (a leitura
dele de "primeiro/à frente" é a posição da direita, ordem cronológica).

**Decisão.** Ano anterior (barra clara) à esquerda; atual (escura) à direita;
legenda, rótulos de dados e tooltip na mesma ordem.

**Detalhe que sustenta.** No Chart.js a posição lado a lado, a legenda e o
tooltip seguem a propriedade `order` (ascendente), NÃO a ordem do array de
datasets: trocar só o array não muda nada. Ano anterior ficou com `order:3`,
atual com `order:4`; as linhas (Δ% e média) seguem com 1 e 2 para continuarem
desenhadas por cima. Verificado pelas coordenadas renderizadas (clara x=78,
escura x=85) e pela ordem da legenda.

---

## D-40 · Visão por head: um arquivo por head, com recorte físico na geração (01/09/2026)

**Contexto.** Requisito da fase 2: cada head só pode ver o próprio squad, com
o filtro "no nível de dados, não apenas na interface". O painel é HTML
autocontido aberto por duplo clique, sem backend e sem autenticação: qualquer
dado embutido no arquivo é acessível a quem o tem.

**Decisão (Douglas, 01/09/2026: "é um arquivo por head mesmo").**

1. `run_dashboard.py` gera, além do painel completo,
   `Dashboard_Gerencial_Canais_v3_HEAD_<head>.html` por head
   (config `dashboard.por_head`). `filtrar_por_head()` filtra os DOIS cubos
   (perfil no principal, par head/canal no de SKU) ANTES de embutir, remapeia
   os índices e reduz `dims.head`/`perfil`/`hc` ao próprio squad. O que é de
   outro head **não existe** no arquivo; nenhum parâmetro de interface o traz
   de volta.
2. `NÃO ATRIBUÍDO` não gera arquivo: não é squad de ninguém.
3. A geração prova o recorte em vez de confiar nele: asserts de que nenhuma
   linha de outro head vazou + reconciliação do particionamento no log
   (heads R$ 2.308.856.707,70 + não atribuído R$ 941.167,11 = base
   R$ 2.309.797.874,81, medido em 31/08).
4. Título, cabeçalho e rodapé declaram a restrição (`DB.meta.recorte_head`);
   o `localStorage` ganha chave própria por head para o recorte salvo de um
   arquivo não clobberar o do painel completo.
5. Publicação inicial em `Documentos\Painéis Comerciais\Gerencial\`
   (01/09/2026, cópia com nome temporário e renome, hashes conferidos).
   **Regra de distribuição: cada head recebe só o seu arquivo.** As
   permissões no SharePoint ficam com o Douglas; sem elas a segregação por
   arquivo ainda não está em vigor. Decisões D-a a D-e do doc 15 seguem
   abertas.

**Validação.** Arquivo do head 20 conferido no navegador: total idêntico ao
recorte do head no painel completo (R$ 928,23 mi ao centavo), nenhuma menção
a outro head no HTML inteiro, dims reduzidas. Commits `3e4169c` e `f5df0bb`.

---

## D-41 · Interface sem emoji e sem travessão; teste nunca crava total de negócio como literal (01/09/2026)

**Contexto.** Regras gerais da fase 2, literais: nada de emoji em código,
interface, comentários, commits ou mensagens; nada de travessão em textos da
interface, comentários ou documentação (usar vírgula, dois pontos ou ponto
final). E o cenário T-05 quebrou sozinho quando o sell-in de ago/26 chegou:
o total esperado estava cravado como literal (R$ 2.260.854.914,86) e a base
cresceu R$ 48,9 mi.

**Decisão.**

1. Emojis substituídos por texto ou símbolo tipográfico (🔗 removido, ⬇ → ↓,
   ⚠ → "Atenção:", ✕ removido). Símbolos tipográficos (▸ ▾ ▲ ▼ ‹ › Σ ✓ ·)
   ficam. Travessões saíram dos textos VISÍVEIS da interface (intervalos
   viram "a", aposições viram dois-pontos ou vírgula); comentários antigos do
   código ficam como estão, texto novo segue a regra.
2. T-05 passou a MEDIR o esperado na hora (receita do `resumo.json` antes do
   cenário + os R$ 1.000,00 do arquivo sintético, tolerância de 1 centavo).
   Regra derivada: teste de cenário não crava total de negócio como literal,
   porque a base cresce a cada carga e o teste gritaria sem defeito nenhum.

**Validação.** Varredura do texto renderizado da página inteira: zero emoji,
zero travessão. 30/30 regras e 6/6 cenários após a troca do T-05.

---

## D-42 · Código de bandeira lido da Hierarquia_Consolidada: a ponte com a base de metas (01/09/2026)

**Contexto.** As metas de set/26 chegaram no `FY 26-27_Meta Set_TT BRASIL.xlsx`
(grão head x bandeira x categoria, R$ 122,28 mi e 7.824 t, hierarquia N2 a N4
por linha). O cruzamento por NOME de bandeira cobre 250 de 259, mas depende de
grafia (7 órfãs) e quebra em fusão/renomeação. A meta traz `CÓD. BANDEIRA 1/2`
(série 82xxxxx do Comercial), que o sell-in não tem, e a medição de 01/09
mostrou que a Hierarquia_Consolidada JÁ CARREGA esse cadastro nas colunas
`CÓDIGO BANDEIRA`/`BANDEIRA`, que o leitor ignorava.

**Decisão.**

1. O leitor da estrutura passa a ler as duas colunas (opcionais no config):
   `COD_BANDEIRA` (via `digitos()`) e `BANDEIRA_ESTRUTURA` (via `texto()`)
   entram na DIM_CLIENTE. A `BANDEIRA` de tela segue vindo do sell-in: as
   grafias divergem em 9% dos clientes (39,6% da receita), e trocar o rótulo
   mexeria no eixo do painel sem necessidade.
2. O cruzamento meta x realizado (fase seguinte) será por CÓDIGO primeiro e
   nome como fallback declarado. Medido com a hierarquia de hoje: 240 dos 256
   códigos nomeados da meta existem, 97,6% do RL nomeado casa por código; o
   código já resolve sozinho a duplicidade Passarela/Via Atacadista (8200734
   dos dois lados) e a fusão BH+Minas Diet (8201079, Minas Diet já está na
   bandeira SBH na hierarquia).
3. `COD_BANDEIRA` entra na checagem de conflito por cliente (zero conflitos
   medidos; se surgir, vale a 1a linha com aviso). Ausência fica `<NA>`,
   nunca inventada; esquema da DIM é estável mesmo sem estrutura.
4. `VERSAO_CACHE` 5 → 6 (leitor mudou de colunas).

**Aberto (pedidos ao Comercial).** `Hierarquia_Complemento` sem as colunas de
bandeira (2.612 clientes ficam sem código, cobertura para em 81,3% dos
clientes/93,5% da receita); 16 códigos da meta sem par na hierarquia
(R$ 2,17 mi, 2,4% do RL nomeado, série 8202xxx nova); executivo 4210
inexistente; cód. 8200372 cobre LASA e HORTIFRUTTI juntas (meta só tem
HORTIFRUTTI, confirmar se o grupo fundido é intencional).

**Validação.** 31/31 regras + 6/6 cenários; pipeline com totais IDÊNTICOS ao
centavo (R$ 2.309.797.874,70 · 164.510,21 t · 33.384.067 cx); painel
regenerado byte-idêntico em tamanho; log novo: "codigo de bandeira
(hierarquia): 13.101 de 16.122 clientes (81,3%)".

---

## D-43 · Leitor da base de metas FY 26/27 e FATO_META (01/09/2026)

**Contexto.** Douglas colocou o `FY 26-27_Meta Set_TT BRASIL.xlsx` em
`bases\Metas\` (regra da pasta: o arquivo vem como está, o leitor se adapta).
Layout medido: cabeçalho na 4a linha, rótulo do indicador (Volume kg / RL R$)
na linha ACIMA do cabeçalho, o mês só no rótulo da coluna (SET'26), linhas
Total no meio do dado, e a dupla de códigos de bandeira com semântica mista.

**Decisão.**

1. Leitor novo `src/extract/metas.py` (config `fontes.metas`, obrigatorio
   false): acha o cabeçalho pelo CONTEÚDO (linha com CLIENTE e CATEGORIA),
   lê o indicador na linha acima, converte o rótulo do mês em ANO_MES
   (MMM'AA; o que não casar ABORTA — competência nunca vem de posição nem de
   nome de arquivo) e faz o melt para uma linha por mês.
2. **A linha Total geral do arquivo é o gabarito**: detalhe que não soma a
   linha Total aborta, nas duas métricas, com as tolerâncias do sell-in.
   Grão ANO_MES x COD_HEAD x BANDEIRA_META x COD_BANDEIRA x CATEGORIA:
   duplicidade aborta (meta dobrada em silêncio no join é o mesmo defeito da
   fato).
3. **`CÓD. BANDEIRA 2` só é fusão quando é dígito puro E diferente do 1.**
   Medido: "Ok" (2.181 linhas), autorreferência (4 bandeiras) e a chave
   interna dos baldes (`201_AMENDOIM`) não são fusão; sobram 3 fusões reais
   (BH+Minas 1054413, Economart 8202051, Super Adega 8200032).
4. Não ingeridos: N4, nomes por extenso, CLIENTE ATIVO. Baldes Sem Mudança/
   Projeto L entram como linhas normais; o tratamento é da fase dos visuais.
5. FATO_META gravada SEMPRE (vazia se o arquivo faltar): esquema estável,
   meta ausente aparece ausente — nunca zero.
6. `conferir_cobertura()` MEDE e relata o encaixe com o realizado (código
   primeiro, D-42; nome fallback) sem abortar: meta sem par é lacuna de
   cadastro com dono, não defeito do pipeline.

**Validação.** 35/35 regras (31 + 4 do leitor) · 6/6 cenários · pipeline
exit 0 com FATO_META 3.282 linhas · R$ 122.279.463,48 · 7.824,5 t
reconciliados ao centavo com a linha Total. Cobertura primeira carga: 73,3%
do R$ por código + 0,7% por nome; sem par: baldes (R$ 30,5 mi) +
DISO/UNIVALE/PELLAH (códigos 8202xxx — pedidos ao Comercial, D-42). Bônus
medido: o `texto()` colapsa o espaço duplo e o DOCES TIQUINHO casou sozinho.
Sell-in e painel intocados (totais idênticos, particionamento fecha).

---

## D-44 · CUBO_META e a aba Metas: rota A, cruzamento na geração (01/09/2026)

**Contexto.** Com a FATO_META carregada (D-43), Douglas pediu as visões de
Meta x Realizado x mesmo mês do ano anterior para os heads, nos níveis N1/N2/
N3, bandeira e categoria — e escolheu a ROTA A para o dono do realizado no N3
(o vazamento medido entre a hierarquia vigente e o dono declarado na meta era
16,3% do realizado no N3 e 5,2% no N2).

**Decisão.**

1. **Rota A**: na visão de metas, o realizado de bandeira NOMEADA segue o
   head/gerente/executivo DECLARADOS na meta, mesmo quando a hierarquia
   vigente distribui os clientes por outros códigos. É o que faz meta e
   realizado fecharem ao centavo em todos os níveis (N3 soma para N2 e N1).
   A cauda sem bandeira nomeada segue a hierarquia vigente do cliente e entra
   como DEMAIS BANDEIRAS, onde a meta dos baldes (Sem Mudança/Projeto L,
   abertos por gerente/executivo) se encaixa na mesma linha.
2. **Cruzamento na GERAÇÃO** (`src/load/cubo_meta.py`), nunca na tela: o
   painel recebe (mês x grupo da meta x bandeira x categoria) com meta,
   realizado e LY já pareados, como inteiros escalados. Atribuição de cliente:
   código de bandeira primeiro (D-42, código 2 cobre fusão), nome como
   fallback só para entidade sem nenhum cliente por código; código
   reivindicado duas vezes fica com o dono principal, com aviso. Entidade por
   código consolida as linhas duplicadas (Passarela + Via Atacadista) sem
   tocar na planilha.
3. **Ausência é ausência**: mês da meta sem sell-in carregado viaja como null
   e a tela mostra n/d com o aviso "sem sell-in do mês ainda" — nunca 0% de
   atingimento. LY = mesmo mês do ano anterior, mesma atribuição.
4. **Reconciliação aborta**: meta do cubo x FATO_META e realizado/LY do cubo
   x FATO_SELLIN, por mês, com a tolerância RELATIVA dos cubos (meio centavo
   por célula de arredondamento; medido R$ 0,13 em R$ 122,28 mi).
5. **Aba Metas no v3**: fora dos filtros globais (o cubo de meta não tem
   canal/UF/projeto/SKU; o #fPainel não viaja para lá), com mês da meta,
   métrica (R$ ou t) e visão (Head/Gerente/Executivo/Bandeira/Categoria),
   KPIs (meta, realizado, atingimento, ano anterior, crescimento embutido),
   exportação CSV/XLSX e ordenação como as demais tabelas. Sem cubo_meta no
   pacote, a aba é REMOVIDA do DOM (painel antigo republicado não mostra aba
   vazia). Arquivos por head: mesmo recorte físico (grupo do cubo de meta
   pertence ao head do arquivo), com assert na geração; pela rota A, bandeira
   de dono declarado aparece INTEIRA no arquivo do dono (ex.: Economart
   completa no da Izabela, incluindo a fatia que a hierarquia daria ao
   Ademir) — consequência aceita da decisão.

**Validação.** 37/37 regras + 6/6 cenários; CUBO_META 2.547 linhas, 54
grupos, 257 bandeiras, reconciliado (meta, LY; set/26 sem sell-in ainda);
painel completo e 4 por head conferidos no navegador (KPIs R$ 122,28 mi meta,
R$ 103,47 mi LY, +18,2%; visão head bate a régua por head; arquivo da
Izabela só com executivos 4xxx; zero erros de console). cubos.json +136 KB;
painel v3 14,53 MB.

---

## D-45 · Meta no gráfico de Evolução da Visão Geral (01/09/2026)

**Contexto.** Com a aba Metas no ar, Douglas pediu a meta TAMBÉM na Evolução
da Visão Geral, nos meses que possuem meta.

**Decisão.**

1. Barra "Meta" (âmbar, `order` 5, à direita do Atual: passado, presente,
   alvo) só nos períodos que possuem meta; grupo sem mês de meta fica sem
   barra (null), nunca com zero. Na granularidade Tri/Sem/Ano, a meta do
   grupo é a soma dos meses do grupo QUE TÊM meta.
2. **A série só existe onde a base de metas alcança**: métrica R$ ou t
   (caixas não existe na meta) e filtros que o cubo de meta TEM (categoria,
   head, gerente, bandeira). Com canal, UF, projeto ou SKU ativos a barra
   SOME e a nota diz o motivo e o caminho ("limpe esses filtros") — nunca
   uma meta que finge respeitar um recorte que ela não tem.
3. Com filtro de head/gerente, a nota declara a assimetria: a meta segue o
   dono da rota A (D-44) e as barras seguem a hierarquia vigente. Com filtro
   de bandeira, os baldes (DEMAIS BANDEIRAS) ficam de fora, dito na nota.
4. Rótulo da barra em âmbar escuro pelo mesmo desenhador (afterDatasetsDraw);
   tooltip e legenda herdam o padrão. Média do período continua calculada só
   sobre o Atual.

**Validação.** Conferido no navegador (FY2027/set/26): LY 103,47 mi · Atual
1,28 mi · Meta 122,28 mi; filtro de canal esconde com nota; filtro da
Izabela mostra a meta dela (20,30 mi) com a nota da rota A; FY2026 sem barra
e sem nota de meta. Zero erros de console. 5 HTMLs republicados (md5 5/5).

---

## D-46 · Arquivo por head sem a opção "Head" nos seletores "por:" (01/09/2026)

**Contexto.** No arquivo restrito a um head, "Detalhamento por Head" é uma
tabela de uma linha — redundância apontada pelo Douglas.

**Decisão.** Quando `DB.meta.recorte_head` existe (flag `SO_HEAD`), a opção
"Head" sai dos DOIS seletores que compartilham a lista de dimensões
(Detalhamento da Visão Geral e "por:" da aba R$/kg). Recorte salvo antes da
mudança que aponte `dimGeral`/`dimPreco` = "head" cai no padrão (Categoria)
em vez de quebrar. O painel completo não muda.

**Validação.** Arquivo do head 20: seletores sem "Head" nas duas abas;
localStorage com `dimGeral:"head"` recai em Categoria; painel completo com o
chip intacto; zero erros de console. 5 HTMLs republicados (md5 5/5).

---

## D-47 · Lote 3 da Visão Geral: metas na tela, Bandeira no Detalhamento, layout enxuto (01/09/2026)

**Contexto.** Pedido do Douglas com protocolo explícito (plano + dúvidas antes
de editar). As 8 dúvidas levantadas (Q1–Q8) foram respondidas antes de
qualquer alteração. Validação prévia medida no parquet: a FATO_META tem grão
`mês × head × bandeira × categoria` (3.282 linhas, 10 categorias, zero
duplicados, zero nulos, R$ 122.279.463,48 reconciliado) — **meta é por
Categoria**, e toda agregação é soma das metas de categoria.

**Decisões (com a resposta que as fixou):**

1. **(Q1-a)** Os atalhos de Período (Mês|Trimestre|Semestre|Acumulado + setas)
   saíram do layout — redundantes com o "Ver por" na leitura do usuário. A
   seleção de meses continua nos chips "Meses"; o "Ver por" fica.
2. **(Q2)** O rótulo "sem filtro de dimensão" não é mais exibido (linha de
   estado e cabeçalho do painel); com filtros ativos os textos continuam.
3. **(Q3-b)** O rodapé textual saiu de TODOS os arquivos. O contexto da carga
   continua em `resumo.json` e no relatório de qualidade; as ressalvas seguem
   declaradas nas telas que elas afetam; título e cabeçalho continuam
   declarando o recorte por head (P2-D).
4. **(Q4)** "Perfil de Head" = arquivo por head (`SO_HEAD`). A LINHA do filtro
   Head fica `hidden` — componente, lógica e listeners preservados; painel
   completo intacto.
5. **(Q5-a)** Meta no painel = **bloco separado "Meta x Realizado"** na Visão
   Geral, lendo o CUBO_META (rota A) — não tabela única no Detalhamento.
   Motivos: meta não tem os eixos canal/projeto/UF; rota A × hierarquia
   vigente na mesma linha compararia donos diferentes; a matriz já tem ~19
   colunas. Dimensões: Head, Gerente, Executivo, Bandeira, Categoria (Canal
   não existe na base de metas — declarado). Colunas por mês de meta:
   Meta | Realizado | Δ | Δ%, com totalizadores; TOTAL de linha só quando
   houver 2+ meses de meta. Responde aos filtros que a meta TEM (head,
   gerente, categoria, bandeira); com canal/UF/projeto/SKU ativo a tabela
   avisa (mesma regra D-45). Grafico de Evolução perdeu a série "Média do
   período" (o número segue no KPI Faturamento médio/mês).
6. **(Q6)** Drills: cat→SKU e head→gerente continuam; nas demais dimensões do
   Detalhamento o clique abre as **categorias** do item (tipo "dimcat",
   ignorando o filtro da própria dimensão e o de categoria). No bloco de
   metas, o clique abre as categorias do item (CUBO_META).
7. **(Q7)** Bandeira no Detalhamento segue o padrão da aba Bandeiras: top N
   (seletor daquela aba, padrão 50) com o balde Σ na tabela — total fecha.
8. **(Q8)** Ausência é o `n/d` padrão do painel, nunca zero nem célula
   inventada.

**Validação.** 37/37 unitários · 6/6 cenários · pipeline exit 0. No navegador
(painel completo, FY2027): meta R$ 122,28 mi no bloco = FATO_META ao centavo;
realizado do bloco (R$ 1,28 mi) = KPI do painel; drill do Atacado (10
categorias) soma a linha do agregado; Canal→Categoria, Head→Gerente,
Categoria→SKU e Bandeira→Categoria conferidos; filtro de canal esconde meta
com aviso nos dois lugares (gráfico e bloco). Arquivo do head 20: filtro Head
oculto, seletores sem "Head", bloco de metas abrindo por Gerente com total
R$ 48,62 mi (= a meta do próprio head no painel completo), sem rodapé. Zero
erros de console nos dois arquivos. 5 HTMLs republicados.


---

## D-48 · Sup./Exec. (N3) no painel e fim dos filtros ignorados (02/09/2026)

**Contexto.** O painel detalhava ate Gerente (N2). A `Hierarquia_Consolidada`
ja trazia o N3 (`(N3) CODIGO SUP./EXEC.` + papel + nome) e o ETL ja o lia para
a `DIM_CLIENTE` desde a D-34 — a coluna `SUPERVISOR` era gravada no Parquet e
**morria ali**: nao entrava em cubo nenhum e nao virava filtro. Media em
02/09/2026: 56 Sup./Exec. com faturamento, **99,96% da receita atribuida**,
zero cliente com N3 conflitante.

No mesmo levantamento apareceu um problema maior. O cubo de SKU tinha como
eixo comercial o par (head, canal) — por custo, decidido na D-09 — e por isso
a aba de SKU **ignorava gerente, projeto e bandeira**, avisando na tela. Com o
N3 entrando seriam quatro filtros ignorados. Filtro que a tela avisa que esta
ignorando e filtro que alguem le errado.

**Decisao.** (1) `SUPERVISOR` entra no eixo `perfil` dos DOIS cubos; (2) o cubo
de SKU passa a usar o **mesmo perfil** do cubo principal **mais a bandeira** —
nenhum filtro fica fora de nenhuma camada; (3) os cubos passam a viajar
**compactados** dentro do HTML (gzip+base64, descompactados na abertura pelo
proprio navegador, sem rede); (4) a cadeia de drill vai a
**Head -> Gerente -> Sup./Exec.**; (5) o rotulo do nivel e **"Sup./Exec."** no
painel inteiro — a aba de Metas dizia "Executivo".

**Por que assim, com o que foi medido antes de decidir** (`working/medir_n3.py`
e `working/medir_n3b.py`, rodados sobre a camada curada):

| Cenario | Cubo de SKU | Painel projetado |
|---|---:|---:|
| como estava (4 filtros ignorados) | 370.823 linhas | 14,66 MB |
| perfil completo (so bandeira de fora) | 498.045 | 19,05 MB |
| perfil + bandeira, sem compactar | 650.409 | **25,83 MB — acima do teto** |
| perfil + bandeira, **compactado** | 650.409 | **9,65 MB** |

O teto de 25 MB e o alvo de 20 MB foram fixados nesta fase (abertura por duplo
clique em maquina corporativa e limite de anexo de e-mail). Sem compactacao o
cenario correto estourava o teto **e** crescia ~4% por mes novo de sell-in — a
solucao duraria dois meses. Compactado, o painel ficou **menor do que era**
carregando quatro filtros a mais.

**Resultado medido na geracao (02/09/2026):** perfis 123 -> 220; cubo principal
94.085 -> 97.397 linhas (+3,5%); cubo de SKU 370.823 -> 649.112 (+75%); cubos
25,5 MB -> 9,2 MB compactados; **painel 14,66 -> 9,53 MB**; arquivos por head
de 1,7-7,5 MB para 1,07-4,87 MB. Particionamento fecha: R$ 2.317.781.656,27
(heads) + R$ 969.705,72 (NAO ATRIBUIDO) = R$ 2.318.751.361,99.

**O que NAO mudou, de proposito.** O grao da fato, o modelo estrela, as
dimensoes, o corte de bandeira (top 300 + balde), a reconciliacao cubo x fato
(que continua sendo a trava da publicacao) e o recorte fisico por head — que
agora corta os dois cubos pelo mesmo indice de perfil.

**Fora de escopo, por decisao do Douglas:** o N4 (vendedor/RCA). A base tem o
nivel, mas com tres pendencias do Comercial medidas nesta fase: 13 clientes com
dois vendedores (rateio de receita nao tem regra), 992 linhas com
`[Criar Codigo]` no lugar do codigo, e o `Hierarquia_Complemento.xlsx` sem
nenhuma coluna N4 (2.612 clientes, R$ 136,4 mi em 24 meses). Tambem ficaram de
fora, por decisao: arquivo por gerente ou por supervisor (segue so por head) e
qualquer tema de meta/orcamento/target.

**Rollback.** `backup_2026-09-02_pre_N3/` (cubos.py, run_dashboard.py,
template_v3.html, config.yaml e o painel gerado) e
`dashboard/template_v3_pre_D48.html`.

---

## D-49 · Remoção do tema Metas (02/09/2026 — Fase 1 da reestruturação)

**Contexto.** Início da reestruturação do painel (prompt de 02/09/2026, Step 1):
haverá um **novo arquivo de metas, cruzado pela chave do cliente/código do
cliente** — a base FY 26/27 (grão head × bandeira × categoria, ponte por código
de bandeira, rota A) deixa de ser a fonte. A regra da reestruturação proíbe
código morto, visual oculto ou cálculo desativado no build: o tema sai inteiro.

**Decisão.** Remoção integral do tema Metas do produto:

- `src/extract/metas.py` e `src/load/cubo_meta.py` **apagados**;
- `run_pipeline.py` parou de ler a base, de conferir cobertura, de construir o
  `CUBO_META` e de gravar a `FATO_META` (o parquet some na próxima execução);
- `run_dashboard.py` parou de recortar `cubo_meta` por head;
- `config/config.yaml` perdeu o bloco `fontes.metas`;
- template v3: saíram a **aba Metas** (D-44), o bloco **Meta x Realizado** da
  Visão Geral (L3-F/D-47) e a **série de meta na Evolução** (D-45), com todos
  os controles, exportações e estados de recorte; recorte salvo apontando para
  a aba "metas" cai na Visão Geral;
- testes exclusivos de metas removidos (leitor D-43 e cubo D-44); suíte segue
  verde com 35/35;
- `bases/Metas/` **intocada** (origem é só leitura). As decisões D-42 a D-45 e
  a rota A permanecem neste registro como histórico.

**O que fica, de propósito.** `COD_BANDEIRA`/`BANDEIRA_ESTRUTURA` na
`DIM_CLIENTE` (D-42): nasceram como ponte para a meta antiga, seguem como
atributo do cadastro — sem função de join.

**Ponto de reintegração (quando o novo arquivo de metas existir).**
1. Novo leitor em `src/extract/` declarado em `config/config.yaml →
   fontes.metas`, com `COD_CLIENTE` como chave obrigatória e competência vinda
   do conteúdo (nunca do nome do arquivo), `obrigatorio: false` (sem o arquivo
   o painel roda sem meta; ausência é ausência, nunca zero).
2. `FATO_META` por (ANO_MES × COD_CLIENTE [× categoria/SKU se o arquivo
   trouxer]), gravada na curated e reconciliada contra o gabarito do próprio
   arquivo — como toda fonte do projeto.
3. O cruzamento com o realizado passa a ser **join direto pela chave do
   cliente** na camada de agregação (etapa 5 do `run_pipeline.py`), sem rota A,
   sem ponte por código de bandeira e sem fallback por nome: a meta herda
   canal, hierarquia e bandeira da própria `DIM_CLIENTE`, e por isso responde
   aos mesmos filtros do painel.
4. Na interface, o visual de meta nasce de novo sobre a matriz da época —
   nenhum componente antigo ficou oculto para "religar".

**Rollback.** `dashboard/template_v3_pre_D49.html`,
`tests/test_regras.py.pre_D49` e o histórico do git; os módulos apagados
existem no commit anterior.

**Adendo (02/09/2026, decisões do Douglas na mesma rodada).**
(1) **Complemento aposentado em definitivo** (Q1 da auditoria): o
`Hierarquia_Complemento.xlsx` saiu de `bases/` e não volta — a chave
`fontes.estrutura_comercial.complemento` e o mecanismo de concatenação em
`cadastros.py` foram removidos. Os 2.612 clientes dele viraram as bases
`RTM-Transicao` (1.762) e `Hierarquia_Clientes_Faltando` (850), tratadas na
Fase 2. (2) **Piso de cobertura temporário em 0,93**: a aposentadoria derruba
a cobertura medida para 94,08% e o piso de 0,95 abortaria todo ciclo até a
Fase 2; a redução está declarada no config com a instrução de VOLTAR a 0,95
quando a Fase 2 reatribuir os clientes. Estado medido após as duas decisões:
pipeline exit 0 · 35/35 · painel 9,29 MB, 5 abas · particionamento fecha em
R$ 2.181.581.461,40 (heads) + R$ 137.169.900,61 (NÃO ATRIBUÍDO: RTM 89,09 mi
+ saneamento 47,11 mi + antigos 0,97 mi) = R$ 2.318.751.362,01. (3) Da mesma
rodada: a distribuição por nível (Fase 4/5) será **só até o N3** — Full + 4
N1 + 13 N2 + 55 N3 = 73 arquivos; o N4 aparece como nível expansível na
matriz do arquivo do N3, sem arquivo próprio. FATO_META.parquet e os caches
de staging da meta e do complemento foram removidos de `data/` (artefatos
gerados; as origens em `bases/` ficam intocadas).

---

## D-50 · Fase 2 da reestruturação: N4 no modelo, reatribuição RTM e saneamento da hierarquia (02/09/2026)

**Contexto.** Steps 4 e 5 do prompt da reestruturação, executados com as
recomendações da auditoria de 02/09 aprovadas pelo Douglas ("segue as
recomendações da auditoria em Q2-Q7"). Duas bases novas entram no pipeline:
`bases/RTM-Transicao/RTM_DePara_Transicao.xlsx` (1.762 clientes que migraram
do atendimento direto para distribuidor; de-para 1:1, 27 distribuidores) e
`bases/Bases para tabelas dimensões/Hierarquia_Clientes_Faltando.xlsx`
(850 clientes sem vínculo; coluna Hierarquia SIM=70/NÃO=780). Juntas elas são
exatamente os 2.612 clientes do complemento aposentado na D-49.

**Decisões aplicadas (Q2-Q7 da auditoria):**

- **Q2-b** — reatribuição executada para os **1.596** com código de
  distribuidor; os **166** sem código (placeholders "NOVO RIBEIRÃO PRETO" /
  "NOVO SJRP", R$ 6,47 mi) ficam **fora da hierarquia** com flag
  `ORIGEM_RTM` + `COD_DISTRIBUIDOR` vazio, canal ORIGINAL mantido (nada
  inventado) e lista `data/quality/rtm_sem_distribuidor.csv` — pendência do
  Comercial; quando os códigos chegarem, entram sozinhos na próxima execução.
- **Q3** — regra única: TODO sell-in de cliente RTM (histórico e futuro)
  segue o distribuidor. Não há data de corte: a regra vive na dimensão.
- **Q4-a** — a linha reatribuída troca **hierarquia (N1..N4), projeto e
  canal** pelo do distribuidor e **preserva bandeira, UF e o código do
  cliente**: a aba Bandeiras não perde histórico; `CANAL_ORIGINAL` guarda o
  rastro.
- **Q5** — os **158** HIERARQUIA=NÃO **com** sell-in na janela são o caso NÃO
  coberto: nenhuma regra aplicada, flag `SANEAMENTO_PENDENTE`, lista nominal
  `saneamento_pendentes_decisao.csv` (R$ 36,49 mi de histórico) aguardando
  decisão.
- **Q6** — janela de 6 meses **de calendário** ancorada na **última
  competência fechada** (a última do fato estritamente anterior ao mês da
  execução): 2026-03..2026-08 nesta carga. `saneamento.janela_meses` e
  `ancora_janela` são parâmetros de config.
- **Q7-i** — os **612** inativados (NÃO + sem sell-in na janela) saem da
  matriz para o balde declarado `rotulo_inativo` ("INATIVO (SANEAMENTO)"),
  com motivo e data; o histórico deles (R$ 10,62 mi) **permanece em todos os
  totais** — matriz + fora-da-hierarquia = total geral, sempre.
- **5.4** — precedência RTM > saneamento implementada e testada; interseção
  medida: zero.

**Como (mecânica).** Tudo age na **DIM_CLIENTE** (`src/transform/saneamento.py`),
a fato nunca é tocada — é o join que decide a quem o histórico aparece
atribuído. O N4 passou a ser ingerido da Hierarquia_Consolidada (rótulo
concatenado, mesmo padrão dos outros níveis; `correcoes_vendedor` e desempate
disponíveis no config; os 13 clientes com dois códigos N4 saem como aviso) e
entrou no eixo `perfil` dos dois cubos **na posição 5** — as posições 0-4 que
o template v3 lê não mudaram, e a matriz da Fase 3 lê a 5. VERSAO_CACHE 6→7
(a primeira execução serviu a estrutura do cache v6 SEM o N4 e o painel saiu
com 1 vendedor — pego pela medição pós-execução, corrigido com o bump).

**Resultado medido (02/09/2026, 25 meses):**

| Medida | Antes (D-49) | Depois (D-50) |
|---|---:|---:|
| cobertura da estrutura | 94,08% | **97,65%** (piso restaurado a 0,95) |
| fora da hierarquia | R$ 137,17 mi | **R$ 54,55 mi** (47,11 NÃO/inativos+pendentes + 6,47 RTM s/ dist. + 0,97 antigos) |
| canal DISTRIBUIDOR (série) | ~R$ 477 mi | **R$ 559,94 mi** (R$ 82,62 mi entram — YoY do canal e do Varejo/Atacado deixa de distorcer) |
| perfis · cubo principal · cubo SKU | 158 · 96.028 · 645.275 | **516 · 133.700 · 900.065** |
| painel completo | 9,39 MB | **12,27 MB** (cru 34,8 → 12,0 compactado; teto de 25 MB respeitado) |
| arquivos por head | 1,04-4,73 MB | 1,06-7,52 MB (Ademir cresce: squad mais granular) |
| vendedores (N4) atribuídos | — | **204** |
| testes | 35/35 | **40/40** (5 novos da D-50) |

Reatribuição quantificada por distribuidor (os dois lados) em
`data/quality/relatorio_qualidade.md §7b`.

**O que NÃO mudou, de propósito.** A fato, o grão, as reconciliações (fonte,
cubo×fato, particionamento — todas fecham), o template v3 (zero edição nesta
fase) e as bases de origem.

**Rollback.** `git` — commits da D-49 (`687db30`) para trás; esta fase é um
commit próprio.

---

## D-51 · Fase 3 da reestruturação: painel v4 — 3 abas e matriz hierárquica expansível (02/09/2026)

**Contexto.** Steps 2 e "Detalhamento e Hierarquia" do prompt da
reestruturação, com as recomendações Q8-Q11/Q14 da auditoria aprovadas em
bloco pelo Douglas. A interface nova nasceu como **`template_v4.html`**
(padrão da casa: v1/v2/v3 ficam como retorno rápido — com a ressalva de que
o v3 lê cubos COM o eixo UF; reativá-lo exige voltar o pipeline junto, via
git). Saídas renomeadas para `Dashboard_Gerencial_Canais_v4*.html`.

**Decisões aplicadas:**

- **3 abas exatas**: Visão Geral, Bandeiras e **Categorias** (nova). Saíram
  Geografia, SKU e R$/kg. O que se perde e o que fica está na auditoria de
  02/09 (§2 Step 2); o preço médio sobrevive no card da Visão Geral (Q14) e
  o seletor global segue Valor/Volume/Caixas.
- **Q8**: a Visão Geral ficou com os 5 cards (Valor, Volume, Caixas,
  Faturamento médio/mês, Preço médio) + gráfico de Evolução. Comparativo
  YTD e Evolução por período saíram; o seletor "Comparar" continua
  definindo o ano-moldura e o pareamento LY de todo o painel.
- **Q11**: o Detalhamento e TODO o drill-down deram lugar à **MATRIZ
  HIERÁRQUICA EXPANSÍVEL** Head → Gerente → Sup./Exec. → Vend./RCA na Visão
  Geral. Navegação entre níveis é exclusivamente pela expansão (▸/▾). Os
  rótulos "fora da hierarquia" (sem estrutura + inativos, D-50) chegam do
  gerador (`pacote.rotulos_fora`) e viram linhas síntese Σ sem expansão —
  o histórico delas permanece no Total geral (Q7-i).
- **Step 2.3/2.4**: Bandeiras manteve ganhos/quedas + Top e a tabela virou
  matriz expansível **Bandeira → Categoria** (top N nominais + balde Σ;
  Total geral soma todas). Categorias é a nova aba com a mesma estrutura e
  matriz **Categoria → SKU** (todos os 400 SKUs, sem corte), lendo o
  CUBO_SKU. Sem seletor "Top" em Categorias: são 12.
- **Q9 + filtros hierárquicos**: sobraram Métrica, Comparar, Ano, Meses,
  Canal, Categoria e **Head** (seletor de escopo do Template Full; oculto no
  arquivo por head). Gerente, Sup./Exec., Projeto, UF e as linhas inteiras
  de Bandeira/SKU saíram — bandeira e SKU seguem como dimensões nas
  matrizes.
- **Q10**: o **eixo UF saiu dos dois cubos** (UF segue na DIM_CLIENTE).
  Cubos com 4 índices + 3 métricas; `geografia.yaml`/`nome_uf` deixaram de
  ir ao painel.
- **Regra global "nada cinza"**: `.chip.semdado`, `.chip.off` e
  `.mini[disabled]` saíram do CSS e a marcação de chips sem dado
  (`marcarChipsVazios`) saiu do código — verificado no navegador: zero
  elementos `[disabled]`/esmaecidos em qualquer estado.

**Mecânica da matriz** (`matrizNiveis`, template v4): UMA agregação por
coluna, chaveada pelo caminho completo dos níveis; cada nó acumula de baixo
para cima, então **pai = soma dos filhos por construção** e o Total geral
fecha com os cards em qualquer estado de expansão. Colunas idênticas à
matriz da F1-G (12 últimos períodos + TOTAL/ATUAL/ANT./Δ/Δ%/Part.%);
exportação CSV/XLSX leva as linhas visíveis; ordenação por clique fica
desligada nas matrizes por níveis (reordenar rasgaria pai/filho — nota diz).
Estado de expansão não persiste no recorte (como o drill nunca persistiu).

**Verificado no navegador (T-43):** cascata N1→N4 aberta; N3 = soma exata
dos 21 N4 filhos; Total geral ATUAL = card Valor; LASA → categorias;
AMENDOIM → 97 SKUs; filtro de canal recorta tudo; arquivo por head sem
filtro Head e só com o próprio squad; zero erro de console.

**Resultado medido:** cubos 124.493 (principal) e 866.562 (SKU) linhas —
−7% e −4% sobre a D-50, pelo fim do eixo UF; painel **11,35 MB** (cru
30,8 MB); template v4 com 1.853 linhas (v3: 2.547); 41/41 unitários +
6/6 cenários.

**Rollback.** git (commit da D-50) + `template_v3.html` na pasta (exige o
pipeline da época, ver acima).

---

## D-52 · Fase 4: um arquivo por colaborador (N1–N3) e publicação por pasta de usuário (02/09/2026)

**Contexto.** Step 3 do prompt da reestruturação, com duas decisões do
Douglas: publicação **só até o N3** (02/09: "vamos publicar arquivos só até
N3" — o N4 é o nível expansível dentro do arquivo do N3, sem arquivo
próprio) e **Q13**: pastas com o nome de cada usuário em
`Documentos\Painéis Comerciais\Gerencial\`, que ele compartilha no
SharePoint com o próprio usuário (permissão por herança da pasta), e toda
atualização **substitui** o arquivo dentro da pasta — mesmo nome, links
preservados.

**Decisão/implementação.**

- `filtrar_por_head` generalizou para **`filtrar_por_nivel(pacote, pos,
  rotulo)`**: o mesmo recorte físico de sempre, pela posição do componente
  no perfil (0=head, 1=gerente, 2=sup./exec.), com assert de prova por
  arquivo e a lista de heads do arquivo encolhida junto. Config em
  `dashboard.por_nivel` (níveis e posições declarados) e
  `dashboard.publicacao` (destino; `ativo: false` desliga a publicação).
- Cada nível **particiona a base inteira** e a reconciliação roda nível a
  nível: N1, N2 e N3 fecham idênticos em R$ 2.264.205.766,93 + fora da
  hierarquia R$ 54.545.595,37 = R$ 2.318.751.362,30.
- Template v4: `recorte`/`recorte_nivel` no lugar de `recorte_head`; a
  matriz hierárquica **começa no nível do template** (Full/N1 em Head; N2
  em Gerente; N3 em Sup./Exec. — profundidades exatas dos Templates 2-5 do
  prompt; o Template 1/N4 não existe por decisão); cadeia declarada no
  cabeçalho do card; filtro Head só no Full (oculto nos restritos).
- Publicação: 72 pastas (4 N1 + 13 N2 + 55 N3) com o rótulo completo do
  colaborador (caracteres inválidos → "-"), arquivo substituído com hash
  MD5 conferido; **o Full vai para a raiz**, fora das pastas compartilhadas.
  Postos [VAGO] (1 N2, 8 N3) geram pasta e arquivo normalmente — o Douglas
  decide não compartilhar ou apontar o interino.

**Medido (02/09/2026):** 73 arquivos (Full 11,35 MB · N1 0,93–7,05 MB · N2
0,26–1,05 MB · N3 dezenas a centenas de KB) · geração + publicação em
**12,4 s** · 95 MB no destino · verificado no navegador: arquivo N3 abre com
matriz Sup./Exec. → Vend./RCA, uma linha própria expandindo aos N4, filtro
Head oculto, título declarando o recorte, zero erro de console; payload do
N2 contém um único gerente. Testes 43/43 + 6/6.

**Pendências operacionais (do Douglas):** compartilhar as 72 pastas com os
respectivos usuários (uma vez); apagar da raiz do destino os 5 arquivos v3
de 01/09/2026 (substituídos pelo v4 — a geração não apaga nada que ela não
criou); P7/docs-15 segue como registro histórico.

**Rollback.** git (commit da D-51); a publicação é regenerável do build.

---

## D-53 · Arrumação do ambiente: pasta `_arquivo/` (03/09/2026)

**Contexto.** Pedido do Douglas: despoluir a raiz do projeto para achar as
coisas com facilidade. **Nada foi apagado** — tudo que não é lido pelo
pipeline foi movido para `_arquivo/` (inventário e motivos em
`_arquivo/LEIA-ME.md`): bases fora do escopo (Sell Out MTRIX/FEMSA/KAN,
Previsão, Estoque, Alavancas, scorecards-comerciais, de-paras de sell-out —
~518 MB), o protótipo e o prompt originais, os templates v1/v2 (o retorno
rápido documentado é o v3), os backups pré-fases (conteúdo todo no git),
o cache do DePara aposentado (D-34) e a `working/`. Verificado ANTES de
mover: o projeto vizinho dos Scorecards não referencia esta pasta (grep).
Verificado DEPOIS: pipeline exit 0 e testes verdes. `_arquivo/` entrou no
`.gitignore` (os poucos arquivos versionados lá dentro seguem rastreados,
movidos com `git mv`). A raiz ficou com: bases, config, dashboard, data,
docs, logs, src, tests, os dois run_*.py, README, AUDIT e requirements.

---

## D-54 · Visibilidade dinâmica dos botões: opção sem dado **some** (03/09/2026)

**Contexto.** Teste do Douglas no painel do head **Michel Meira**: o botão de
Canal aparecia mesmo sem conteúdo, dado ou opção por trás dele. A varredura do
projeto mostrou que o caso não era do canal nem daquele head.

**Diagnóstico (medido no código, 03/09/2026).**

1. A regra "só valores disponíveis" existia na `docs/08 §1.2` e era
   implementada como **esmaecimento** (`.chip.semdado`, `marcarChipsVazios`).
   A **D-51 removeu o mecanismo inteiro** pela regra global "nada cinza", e
   **nada ficou no lugar**: desde então nenhum chip tem validação de conteúdo.
2. A causa raiz do caso do Michel é da **geração**, não da interface:
   `run_dashboard.py → filtrar_por_nivel` recortava fisicamente os cubos e
   recalculava **só** `perfil` e `head`. `canal`, `cat` e `sku` viajavam do
   tamanho da empresa inteira para dentro dos 72 arquivos por nível. O painel
   do head oferecia canais em que o squad dele não tem uma única linha, e a
   nota da aba Categorias prometia "os 400 SKUs da base" em arquivos que têm
   uma fração disso.
3. O mesmo valia para **Categoria**, **Ano** e **Meses**, para **todos** os
   níveis (N1, N2 e N3) e também para o Template Full sob filtros.
4. Achados menores da mesma varredura: os botões **↓CSV/↓XLSX** ficavam na tela
   com a tabela vazia e o clique não fazia nada (`registrarExport` os criava
   uma vez e nunca os removia; `vazio()` apagava o `RAW[id]` que
   `exportarTabela` procura); **Limpar filtros** aparecia sem nada para
   limpar; e os cortes do seletor **Top** de Bandeiras eram idênticos entre si
   quando o recorte tem menos bandeiras que o corte.

**Decisão (aprovada pelo Douglas em 03/09/2026).** Uma regra só, para todo
botão do painel e todo nível da hierarquia: **um botão só aparece quando existe
pelo menos uma linha de dado por trás dele no contexto atual** — recorte do
arquivo + filtros de dimensão + meses selecionados.

- opção sem dado e **sem seleção** → não é desenhada;
- opção sem dado **já selecionada** → fica, com o contador **"0"**. Apagar uma
  seleção do usuário em silêncio é pior que exibir o zero. O "0" é um
  contador, **não** um esmaecimento: o chip mantém cor, contraste e clique, e
  a regra global da D-51 continua verificada (zero `[disabled]`, zero cinza);
- **linha de filtro com menos de duas opções some inteira** — botão sem
  escolha é poluição. O que era exceção de um filtro (Head oculto no arquivo
  por nível, L3-D/D-52) virou a regra geral;
- ↓CSV/↓XLSX saem do cabeçalho do card quando a tabela fica vazia e voltam
  sozinhos no primeiro render com dado; **Limpar filtros** só existe com
  filtro ativo; o **Top** oferece os cortes abaixo do universo do recorte mais
  o primeiro que o cobre inteiro.

**Onde mora, em duas camadas — e por quê.**

| Camada | Arquivo | O que faz |
|---|---|---|
| Geração | `run_dashboard.py → filtrar_por_nivel` | `canal`, `cat` e `sku` passam a ser recalculados sobre o cubo **já recortado**, como `head` e `perfil` já eram. Escopo se resolve no DADO: o que não está no arquivo não pode ser exibido nem recuperado por parâmetro de interface |
| Interface | `dashboard/template_v4.html → atualizarOpcoes` / `chips` | dentro do arquivo, o que os filtros ativos zeram também sai da tela |

**Sem hardcode.** Não há lista de nomes, cargos, canais ou pessoas em lugar
nenhum: quem decide é o cubo. A varredura confirmou que a única lista nominal
do projeto é `validacao.valores_esperados`, que segue sendo só gabarito de
conferência. Guardas de regressão em `tests/test_regras.py`.

**Custo.** `passaPrincipal(l, ignorar)` já sabia remover uma dimensão do filtro
(era assim que o denominador da participação % era montado): a mesma função
responde "esta opção teria dado se ela mesma não estivesse filtrando?" — nenhuma
linha de agregação foi duplicada. A varredura é **uma só** para todas as
dimensões, por render.

**O que NÃO encolhe, de propósito.** `cal` (remapear mês reindexaria os dois
cubos e os ponteiros de LY — mês sem faturamento é resolvido na interface) e o
corte de bandeira, que a própria tela declara como calculado sobre a base
inteira, **antes** dos filtros.

**Nenhum número muda.** As listas de chip não entram em nenhuma soma; o recorte
físico já garantia os totais. Reconciliação e particionamento por nível
seguem idênticos.

**Aplicado também no `template_v3.html`** (decisão do Douglas), para o retorno
rápido não divergir no comportamento — lá vale só a camada de interface, porque
reativar o v3 exige `git checkout` do pipeline pré-D-51, e nesse checkout volta
o `run_dashboard.py` daquela data.

**Rollback.** git (commit da D-53).

---

## D-55 · Formatação única de valor: um "R$" para todo o painel (03/09/2026)

**Contexto.** Pedido do Douglas: com a métrica **Valor R$** selecionada, todo
indicador monetário deve sair com prefixo, escala abreviada e formato
consistente — e métrica não monetária **nunca** pode receber R$.

**Diagnóstico (medido, 03/09/2026).** A formatação já era razoavelmente
central (`abrev` + `fmtMetrica`) e o R$ já vinha da métrica ativa
(`METRICAS[F.metrica].un`), então **não havia R$ aplicado indevidamente** em
Volume, Caixas ou percentuais. Os problemas eram três:

1. **`rotCurto`** — uma segunda função de abreviação, privada do gráfico de
   Evolução, que **não recebia unidade**: os rótulos desenhados sobre as barras
   saíam sem R$ enquanto o eixo e o tooltip da mesma barra saíam com R$;
2. **casas decimais divergentes** entre as duas escadas (mi com 2 casas em
   `abrev`, 1 em `rotCurto`): a mesma barra mostrava `112,7 mi` no rótulo e
   `R$ 112,74 mi` no tooltip;
3. **`escalaFixa`** — as matrizes imprimiam número puro nas colunas de série e
   declaravam a escala uma vez no cabeçalho (F1-G), convivendo com as colunas
   ATUAL/ANT./Δ que traziam R$. Dentro da mesma tabela, parte tinha moeda e
   parte não.

**Decisão (aprovada pelo Douglas em 03/09/2026).**

- **`abrev(v, un)` é a única formatação de métrica do painel** — card, big
  number, rótulo de barra, tick de eixo, tooltip, célula de matriz, total,
  subtotal e destaque de ganho/queda. `rotCurto` e `escalaFixa` **saíram**;
- escala **mil / mi / bi**, **uma casa decimal, omitida quando for zero**:
  `R$ 1 mil` · `R$ 25 mil` · `R$ 1,5 mi` · `R$ 25 mi` · `R$ 1,2 bi`;
- o prefixo **nunca é literal**: vem sempre de `METRICAS[F.metrica].un`, que é
  `R$` só em Valor. Volume sai ` t`, Caixas ` cx`, percentual não passa por
  aqui. A única exceção legítima é `fmtPreco` (`R$ x,xx /kg`), porque R$/kg não
  é a métrica selecionada — é uma razão com moeda própria, e o seletor global
  não altera essa definição (D-22);
- **isto SUPERA a F1-G**: a célula da matriz passou a repetir o prefixo. O
  motivo declarado da F1-G era legibilidade; o motivo de superá-la é que número
  que só faz sentido depois de ler a nota é número que alguém lê errado. As
  colunas ficam mais largas de propósito (`white-space:nowrap` impede que
  "R$ 7 mi" quebre em duas linhas).

**Preservado.** Negativo com o sinal "−" de verdade sobre o módulo; zero como
`–` na matriz; nulo como `n/d` (nunca `R$ NaN`, nunca falso −100%); `varPct` e
`razao` inalteradas; e a **exportação CSV/XLSX continua levando número cru**,
sem R$, sem separador de milhar e com decimal por ponto — a formatação pt-BR é
só de tela.

**Nenhum número muda** — só a forma de escrevê-lo. Guardas de regressão em
`tests/test_regras.py`. **Aplicado também no `template_v3.html`.**

**Rollback.** git (commit da D-53).

---

## D-56 · `desempate_vendedor_N4.csv` aposentado: a Hierarquia_Consolidada é a única fonte (03/09/2026)

**Contexto.** O Douglas informou que o desempate dos vendedores N4 foi
incorporado direto na `Hierarquia_Consolidada.xlsx` e que as linhas duplicadas
foram removidas, e pediu a verificação antes de aposentar o arquivo de pedido.

**Verificado (varredura de 03/09/2026).** `docs/pedidos/desempate_vendedor_N4.csv`
**não tem nenhuma dependência de código**: zero ocorrências do nome em
`run_pipeline.py`, `run_dashboard.py`, `cadastros.py`, `dimensoes.py`,
`cubos.py`, `saneamento.py`, `qualidade.py`, `config.yaml` e `tests/`. Ele
nunca foi lido nem escrito pelo pipeline — `qualidade.py` só grava em
`data/quality/`, nunca em `docs/pedidos/`. Era um artefato de **pedido ao
Comercial**: 13 linhas com a coluna `VENDEDOR CORRETO (preencher)` em branco.

**Decisão.** Aposentado. Movido para `_arquivo/pedidos-encerrados/`
(inventário em `_arquivo/LEIA-ME.md`), com o registro do encerramento em
`docs/pedidos/LEIA-ME.md`. A `Hierarquia_Consolidada.xlsx` é a **única fonte**
da estrutura comercial N1→N4.

**O que NÃO sai.** O detector que gerou o pedido continua no lugar
(`cadastros.py`: `HEAD/SUPERVISOR/VENDEDOR/COD_BANDEIRA` conflitantes por
cliente → vale a 1ª linha COM AVISO) e a chave declarativa
`dimensoes.estrutura_comercial.desempate_cliente` continua vazia no config.
Nenhum dos dois é workaround de duplicidade antiga: o `drop_duplicates` é a
**garantia de cardinalidade** que sustenta o `validate="m:1"` de `dim_cliente`
(sem ela, uma duplicata futura multiplicaria o cubo em silêncio), e o detector
é justamente o que **prova** que a base está limpa — quando está, ele não
imprime nada.

**Condição de aceite: cumprida em 03/09/2026.** No momento da decisão a última
execução (`logs/pipeline_20260902-220859-7291ab.log`) ainda registrava
`aviso 13 cliente(s) com VENDEDOR conflitante no de-para`, e a
`Hierarquia_Consolidada.xlsx` tinha sido modificada depois disso. O
reprocessamento sobre a base nova (`20260903-155531`, 15:55) **não traz mais o
aviso**: o desempate na origem está confirmado. As correções declaradas
`correcoes_head`/`correcoes_gerente` (`[Vago]` → `[VAGO]`) **continuam ativas**
(433 + 780 linhas nessa execução; eram 436 + 783), portanto não ficaram
ociosas e ficam no config. (A mesma edição da base derrubou os distribuidores
no primeiro momento; ver D-61.)

**Legado identificado e mantido por ora.** `ROT_AUSENCIA` no template ainda
carrega `"SEM UF"`, que é rótulo morto desde a D-51/Q10 (o eixo UF saiu dos
cubos). Documentado aqui; a limpeza não foi feita junto com a D-54/D-55 para
não misturar assuntos.


---

## D-57 · A contagem da linha Σ de bandeiras passa a ser a DO ARQUIVO (03/09/2026)

**Contexto.** Observação do Douglas no painel do head Michel Meira: a linha Σ
anunciava `DEMAIS BANDEIRAS (11.008 bandeiras)` — o número do universo Dori —
dentro de um arquivo que só contém o squad dele.

**Diagnóstico.** Achado da mesma família da D-54, e uma decisão errada minha
naquela: ao recortar as dimensões por nível eu preservei `ban` e
`corte_bandeira` inteiros, justificando que "o corte das N maiores é calculado
sobre a base inteira, antes dos filtros". Isso é verdade para **o corte** e
continua valendo — mas eu estendi a mesma justificativa para **a contagem do
balde**, e ela não se sustenta: a linha Σ do arquivo de um head não agrega
11.008 bandeiras, agrega só as que têm faturamento no escopo dele.

A nota da aba chegava a misturar os dois universos na mesma frase: "as outras
**11.008**" (base inteira) e, duas linhas abaixo, "**neste recorte** as nominais
somam X%" (recorte do leitor). O `X%` já era recalculado desde a F1-D; o 11.008
ficou para trás.

**Decisão (aprovada pelo Douglas, opção A de duas apresentadas).**

- A **contagem** do balde e o **rótulo** passam a ser os do arquivo. No painel
  do Michel sai `DEMAIS BANDEIRAS (N bandeiras)` com o N do escopo dele.
- O **corte continua global**: as N maiores são as mesmas em todos os arquivos.
  A opção B — recalcular o top N dentro de cada head — foi **recusada**: os
  arquivos deixariam de ser comparáveis entre si e com o Full, e uma bandeira
  nominal no painel de um head poderia aparecer no balde do painel corporativo.
  A tela declara essa escolha ("o ranking das N maiores é calculado sobre a base
  inteira, antes dos filtros e do recorte por nível").
- A nota passa a dizer **de qual universo cada número fala**, e trata o caso em
  que nenhuma bandeira ficou fora do ranking (não escreve "0 bandeiras").

**Onde mora.** A contagem **tem** de nascer em `cubos.py`: depois do `groupby` a
identidade das bandeiras do balde se perde (viram todas o mesmo rótulo), e nem
`filtrar_por_nivel` nem o template conseguem recuperá-la. O pacote passou a
carregar `demais_por_nivel` (~72 inteiros: 4 heads + 13 gerentes + 55
sup./exec.) e `corte_bandeira.rotulo_base`; `run_dashboard.py → _balde_do_nivel`
remonta o rótulo no recorte, reescrevendo `dims.ban` e `corte_bandeira` **na
mesma passada** — o rótulo é a chave que o template usa para localizar o balde
(`D.ban.indexOf(c.rotulo_demais)`), e um assert na geração garante que ele
continua na lista.

**Nenhum número muda** — receita, particionamento por nível e reconciliação com
a fato seguem idênticos; a D-57 troca um rótulo, não um valor. Uma bandeira que
fatura em dois squads conta nos dois arquivos, e o total global continua sendo o
distinto (não a soma dos níveis) — comportamento correto e coberto por teste.

**Não aplicado ao `template_v3.html`:** o v3 não tem geração por nível (a D-52 é
posterior a ele), então o balde lá é sempre o global — que é o número certo para
o arquivo único que ele produz.

**Rollback.** git (commit da D-56).


---

## D-58 · "_Canais_v4" sai dos nomes de arquivo (03/09/2026)

**Pedido do Douglas.** Os entregáveis passam a se chamar:

| Antes | Agora |
|---|---|
| `Dashboard_Gerencial_Canais_v4.html` | `Dashboard_Gerencial.html` |
| `Dashboard_Gerencial_Canais_v4_N1_10-distribuicao-michel-meira.html` | `Dashboard_Gerencial_N1_10-distribuicao-michel-meira.html` |

**Como.** Dois parâmetros do `config/config.yaml` (`dashboard.arquivo_saida` e
`dashboard.por_nivel.prefixo`) mais o valor de fallback em `run_dashboard.py`,
que existe só para o caso de a chave sumir do config. **Nenhuma linha de lógica
mudou**; o nome do arquivo nunca foi hardcode.

**Por quê faz sentido.** Sufixo de versão no nome do entregável envelhece: o
leitor não precisa saber que template gerou o painel dele, e a versão já é
rastreada onde importa: em `dashboard.template` no config e no git.

**Consequência operacional (atenção).** A publicação copia **substituindo pelo
mesmo nome**, e a geração **não apaga o que ela não criou** (D-52). Então, na
primeira execução com os nomes novos, cada uma das 72 pastas de usuário ficou com
**dois** arquivos: o novo e o `..._Canais_v4...` antigo, congelado nos dados de
03/09/2026. O recolhimento dos antigos é tratado na D-60.

**Links já compartilhados apontam para o nome antigo** e passariam a servir um
arquivo que nunca mais se atualiza. Como as 72 pastas ainda não haviam sido
compartilhadas (pendência aberta desde a D-52), este é o momento de menor custo
para renomear; depois de distribuídos, os links quebrariam.

**Rollback.** Devolver as duas strings no config; nada mais muda.


---

## D-59 · O cliente RTM passa a herdar também a BANDEIRA do distribuidor (03/09/2026)

**Contexto.** Observação do Douglas: o painel do head de Distribuição mostrava
bandeiras de mercadinho, não os distribuidores, que são os clientes dele. A
Q4-a (D-50) preservava a bandeira do ponto final para "a aba Bandeiras não
perder histórico".

**Medido antes de decidir** (`ferramentas/analise_bandeira_rtm.py`, 03/09/2026,
sobre a fato inteira) e **remedido depois de implementar** (curated da execução
`20260903-155531`):

| | Simulação (antes) | Implementado (depois) |
|---|---:|---:|
| Clientes próprios do head de Distribuição | 89 | 89 |
| Clientes RTM que caem nele | 1.596 | 1.596 |
| Bandeiras que o head de Distribuição vê | 1.111 → **66** | **66** (60 nominais + 6 na linha Σ do arquivo dele) |
| Bandeiras nos outros 3 heads (Atacado / KA Nacional / KA Regional) | 9.490 / 17 / 92 | 9.490 / 17 / 92 (**efeito zero**) |
| Universo de bandeiras da base | 11.308 → 10.342 | 11.314 → **10.348** (carga de set/26 maior) |
| Receita que troca de rótulo | R$ 82.626.906 (3,56%) | R$ 82.759.658,47 (**3,56%**) |
| Bandeiras afetadas | 1.040 | 1.040 |

**O que derrubou a premissa da Q4-a.** O histórico que ela protegia quase não
existe: das 20 maiores bandeiras afetadas, **17 ficam com R$ 0,00** depois da
mudança: elas vivem SÓ através de clientes RTM, então não se partem ao meio,
mudam de rótulo inteiras. A única divisão material é MASTER (perde R$ 766 mil,
mantém R$ 2,08 mi).

**Achado colateral, registrado para o Comercial.** A receita RTM **não é
histórica**: R$ 18,93 mi nas 6 competências fechadas mais recentes contra uma
média histórica de R$ 3,30 mi/mês, praticamente o mesmo ritmo. Os 1.596
clientes continuam comprando direto da Dori no mesmo volume; a transição para o
distribuidor não reduziu a compra direta deles até ago/2026. Isso não muda a
regra (o sell-in deles soma no distribuidor de qualquer jeito, decisão do
Douglas), mas significa que as bandeiras consolidadas são informação **viva**,
não resíduo do passado.

**Decisão (do Douglas).** Herdar. Implementado como **parâmetro declarado**,
não como regra fixa: `saneamento.rtm_herda_bandeira: true`. `false` devolve a
Q4-a sem tocar em código, e o log declara qual regra rodou (mesma mecânica das
`correcoes_head` e do `desempate_cliente`). O relatório de qualidade (§7b) lê a
medida do saneamento e escreve qual regra de bandeira rodou; nunca um texto
fixo.

**Detalhe de implementação que importa.** A bandeira herdada é a do
**distribuidor na DIM_CLIENTE** (a do sell-in dele), **não** o nome do cadastro
("DIST. X" da `Hierarquia_Consolidada`). É o único jeito de o distribuidor e os
clientes dele caírem na MESMA linha da aba Bandeiras: usar o rótulo do cadastro
partiria cada distribuidor em duas bandeiras, a dele próprio (sell-in) e a dos
clientes (cadastro). A simulação usou o cadastro e a implementação usa a DIM;
a contagem bateu nos dois caminhos (66), medido acima.

**Duas garantias.** (1) `DIM_CLIENTE.BANDEIRA_ORIGINAL` guarda sempre a bandeira
do ponto final, nos dois modos: nada se perde, só muda o rótulo de exibição,
e quem precisar do ponto final continua achando. (2) Guarda contra piora:
distribuidor sem bandeira própria não transmite `SEM BANDEIRA` ao cliente;
trocar um rótulo real por um balde de ausência seria o oposto do objetivo.

**Nenhum número muda.** A fato não é tocada; a D-59 age só na DIM_CLIENTE. O
total, a reconciliação e o particionamento por nível seguem idênticos; muda sob
qual bandeira a receita aparece.

**Textos alinhados na mesma entrega** (a Q4-a continuava escrita em quatro
lugares): docstring de `saneamento.py`, comentário `fontes.rtm_transicao` do
config, `docs/05 §2b`, `docs/06 §2.3` e o §7b do relatório de qualidade.

**Rollback.** `rtm_herda_bandeira: false` no config + reprocessamento. Sem git.


---

## D-60 · Recolhimento dos painéis antigos da publicação: ferramenta, não regra do gerador (03/09/2026)

**Contexto.** A D-58 renomeou as saídas e a publicação copia substituindo pelo
mesmo nome; a geração **não apaga o que ela não criou** (D-52, deliberado: um
script que apaga arquivo na pasta de outra pessoa é um script que um dia apaga
o errado). Resultado medido às 15:08 de 03/09: cada uma das 72 pastas de usuário
com **dois** painéis, o novo e o `..._Canais_v4...` congelado.

**Decisão.** O gerador continua sem apagar nada. O recolhimento vira uma
**ferramenta separada**, `ferramentas/limpar_paineis_antigos.py`, com três
propriedades:

- decide o que é "antigo" **calculando** a lista que a geração atual produz
  (mesmo config, mesmo `cubos.json`, mesmas funções de nome do gerador), e não
  por lista de nomes nem por "contém `_Canais_v4`": assim pega também restos de
  versões anteriores e de colaboradores que saíram da estrutura;
- **não apaga**: move para `_ANTIGOS_PARA_APAGAR/` dentro do próprio destino,
  preservando de qual pasta cada arquivo veio (mesmo padrão da `_arquivo/`,
  D-53); apagar a quarentena é ato humano;
- **guarda**: se faltar qualquer painel da geração atual no destino, aborta sem
  mover nada. Arquivo esperado faltando significa que a geração não rodou
  depois da renomeação, e nesse estado o "antigo" pode ser o único painel que a
  pessoa tem.

**O que aconteceu em 03/09.** O script rodou em modo de listagem (73 antigos,
41 MB) e o Douglas **apagou os 73 à mão** na sequência; a publicação das 15:56
já saiu limpa: 73 arquivos, zero `_Canais_v4`, zero quarentena (medido). O
pendente da D-52 ("apagar os v3 de 01/09 na raiz") também já estava resolvido
desde 02/09 à noite.

**Quando rodar.** Depois de `python run_dashboard.py`, sempre que
`dashboard.arquivo_saida` ou `dashboard.por_nivel.prefixo` mudar, ou quando um
colaborador sair da estrutura (a pasta dele fica com um painel que ninguém mais
gera). Registrado em `docs/10` e `docs/14`.

**Rollback.** Não há: a ferramenta não altera o gerador.


---

## D-61 · Cobertura despencou para 75,40% depois de uma edição da hierarquia: a cascata do RTM (03/09/2026)

**O que aconteceu.** Para incorporar o desempate dos vendedores N4 na origem
(D-56), o Douglas ajustou a `Hierarquia_Consolidada.xlsx` (11:54; 14.054 →
13.427 linhas) e, no ajuste, os **distribuidores ficaram de fora** da base. A
execução `20260903-134305` abortou no piso:

```
cobertura de estrutura comercial sobre a receita: 75.40% (piso: 95%)
```

A execução anterior (`20260902-220859`) media 97,65% sobre a **mesma fato**; só
a hierarquia tinha mudado. O Douglas restaurou os distribuidores (14:06) e o
pipeline voltou a 97,64% (`20260903-150325`), depois 97,65% com a carga nova de
set/26 (`20260903-155531`; base final 13.516 clientes na hierarquia).

**Por que um punhado de códigos derruba um quarto da receita.** O saneamento
faz o cliente RTM herdar do distribuidor a hierarquia **e o `NA_ESTRUTURA`**
(`_HERDA_DO_DISTRIBUIDOR`, D-50). Se um distribuidor sai da hierarquia, **todos
os clientes que apontam para ele caem junto**: os 27 distribuidores carregam,
além do próprio faturamento, os 1.596 clientes RTM (R$ 82,76 mi). É a cascata
funcionando como desenhada, e o piso de 95% abortando como desenhado: ele
existe exatamente para não publicar um painel com um quarto da receita num
balde de "NÃO ATRIBUÍDO".

**Decisão.** Nenhuma regra muda. O que muda é o **diagnóstico**, que passou a
existir como ferramenta (`ferramentas/diagnostico_cobertura.py`, que repete o
caminho do pipeline até a DIM_CLIENTE com as mesmas funções): mede o tamanho do
buraco, lista quem ficou fora, testa a hipótese da cascata (distribuidores do
de-para RTM sem linha na hierarquia, e quanto cada um arrasta) e separa causa
de conteúdo (linhas removidas) de causa técnica (chave zero-preenchida que
parou de casar). A tabela de erros do `docs/10` e a ficha da
`Hierarquia_Consolidada` no `docs/14 §2.2` passam a apontar para ele; o
texto antigo mandava conferir o `Hierarquia_Complemento`, aposentado na D-49.

**Lição operacional, para quem editar a hierarquia.** Antes de salvar a
`Hierarquia_Consolidada.xlsx`, conferir que os códigos dos **27 distribuidores**
do `RTM_DePara_Transicao.xlsx` continuam nela. Depois de salvar, rodar o
pipeline; se abortar no piso, rodar o diagnóstico antes de mexer em
`validacao.cobertura_minima_head` (afrouxar o piso aqui seria esconder o erro,
não corrigi-lo).

**Rollback.** Não se aplica: nada foi alterado no pipeline.


---

## D-62 · Q5 (158 clientes ativos sem hierarquia): pedido ao Comercial, nenhuma regra inferida (03/09/2026)

**Contexto.** A D-50 deixou um caso "não coberto": cliente com
`Hierarquia = NÃO` na `Hierarquia_Clientes_Faltando.xlsx` **com** sell-in na
janela de 6 meses fechados. A regra 5.2 só inativa quem não fatura; quem
fatura ficou listado para decisão. Em 03/09 não houve decisão de negócio; a
memória do projeto dizia que haveria, e não houve.

**Medido (execução `20260903-155531`):**

| | |
|---|---:|
| Clientes | 158 |
| Receita em 24 meses | R$ 36.497.295,26 |
| Receita na janela mar–ago/26 | R$ 5.463.631,09 |
| Último sell-in em jul ou ago/26 | 100 de 158 |
| Já faturaram em set/26 | 6 |
| Canal DISTRIBUIDOR | 17 clientes, R$ 2,25 mi na janela (41%) |
| Destino de cliente RTM (cascata) | 0 |
| Com código de bandeira do cadastro | 0 |

São clientes **vivos** (dois terços compraram nos últimos dois meses fechados),
nenhum é distribuidor-destino do RTM, e os cinco maiores da janela são EPOCA,
CASA E VIDEO, KRUPER, AVANT e FALEKA.

**Opções apresentadas ao Douglas:**

| Opção | O que faz | Custo |
|---|---|---|
| **A. Pedido ao Comercial (escolhida)** | os 158 continuam `NÃO ATRIBUÍDO` até a `Hierarquia_Consolidada` incorporá-los (ou marcá-los como inativos) | R$ 5,46 mi/6 meses fora da matriz, que já é o estado atual |
| B. Inativar todos (estender a 5.2) | vão para o balde INATIVO | esconderia R$ 2,25 mi de distribuidores ativos; contraria "nada simulado" |
| C. Inferir hierarquia por UF/canal | entrariam na matriz | inventa vínculo; proibido pelas regras do projeto |

**Decisão.** Opção A. Gerados `docs/pedidos/pedido_Q5_hierarquia_158.xlsx`
(aba `clientes` ordenada pela receita da janela, colunas N1–N4 e INATIVAR em
branco; abas `LEIA-ME` e `por canal`) e o texto de e-mail
`pedido_Q5_hierarquia_158.md`. O `saneamento_Q5_hierarquia_NAO_com_sellin.csv`
de 02/09 (mesma lista, sem as colunas de resposta) foi para
`_arquivo/pedidos-encerrados/`. A lista viva continua saindo em
`data/quality/saneamento_pendentes_decisao.csv` a cada execução; quando o
Comercial incorporar os clientes à `Hierarquia_Consolidada`, ela esvazia
sozinha. Nenhuma linha de código ou config muda.

**Rollback.** Não se aplica.


---

## D-63 · Período inicial: FY corrente até o último mês fechado (03/09/2026)

**Contexto (crítica do painel, 03/09/2026, capturas dos 4 arquivos de
referência).** O v4 abria no último ano fiscal da série com todos os meses
dele marcados. Em setembro o FY2027 tem um mês, parcial: KPIs a −85%/−90%,
"Maiores quedas" com sete de dez itens "sem faturamento −100%", gráfico com uma
barra, em todos os 73 arquivos. O Douglas confirmou que isso nunca foi decisão.

**Decisão.** O painel abre no **FY corrente até o último mês fechado**; se o FY
corrente ainda não tem mês fechado, abre no **FY anterior inteiro** (que tem par
completo no ano anterior). "Fechado" = competência estritamente anterior ao mês
da geração, lido de `meta.gerado_em`; é a mesma régua do saneamento (D-50/Q6).
O mês parcial continua nos chips de Meses. Trocar de base ou de ano pelos chips
segue marcando o ano inteiro: ali a escolha é do usuário.

**Efeito colateral tratado.** O recorte salvo no navegador vence o padrão, e
todo mundo tinha "set/26" salvo. A chave do `localStorage` subiu de `v4` para
`v5`: cada arquivo abre uma vez no período novo e volta a lembrar o que o
usuário escolher.

**Onde.** `template_v4.html` (`periodoInicial`, `mesDaGeracao`, `CHAVE_LS`);
guarda em `tests/test_regras.py`. Nenhum número muda.

**Rollback.** git.


---

## D-64 · O eixo bandeira sai do cubo de SKU (03/09/2026)

**Contexto.** A bandeira entrou no cubo de SKU na D-48 para o filtro de
bandeira valer na aba de SKU. A D-51 removeu esse filtro e a matriz
Categoria → SKU nunca leu o eixo: no template v4 o acessor `BANDE` só estava
definido (medido por grep, zero usos). Era peso morto que multiplicava o cubo.

**Medido (fato de 03/09):** cubo de SKU 866.028 linhas com bandeira →
**680.530 sem** (base inteira); Atacado 501.706; Sul/CO 143.340; RS/SC
118.891. É a folga que paga a D-65.

**Decisão.** `cubo_sku` passa a ser `[mês, SKU, perfil, R, P, C]` (3 índices +
3 métricas; o principal segue com 4 + 3). `cubos.py`, `reconciliar` (base 3),
`filtrar_por_nivel` (remapeamento) e o template (`BASE_SKU`, `matrizNiveis`)
acompanham; 5 testes atualizaram a posição da receita. Reconciliação cubo ×
fato continua ao centavo. O template v3 já não lia este formato (D-51).

**Rollback.** git.


---

## D-65 · Bandeiras: todas no arquivo, corte só de exibição; N2/N3 exibem tudo (03/09/2026)

**Contexto (crítica do painel, 03/09/2026).** O corte das 300 maiores era
aplicado na geração, sobre a base inteira, antes de qualquer recorte. Medido
nos arquivos gerados: o executivo RS/SC via 13 bandeiras nominais e **2.917
dentro da linha Σ** (89% do faturamento dele numa linha que não abre); 14 dos
55 executivos e 4 dos 13 gerentes tinham mais escondido do que exibido; e
"Maiores ganhos/quedas" eram calculados só sobre as bandeiras que por acaso
estavam no top 300 corporativo. O Douglas pediu: cada nível vê as **suas**
bandeiras, todas se possível, com busca.

**Medido antes de decidir (fato de 03/09):** cubo principal sem corte
495.037 linhas (contra 123.900); com a D-64 os dois cubos somam 1.175.567
linhas ≈ 39 MB crus (hoje 30,7 MB), Full estimado em ~14 MB no arquivo.
Por arquivo: Atacado ~31 MB crus, Sul/CO ~10, RS/SC ~8. O dado cabe; o que
não cabe é **exibir** 9.490 linhas no Atacado.

**Decisão.**

- `cubos.py` para de agregar: **toda bandeira com sell-in é linha do cubo**;
  a ordem dos índices é o ranking global por receita.
- `filtrar_por_nivel` leva só as bandeiras do escopo, reindexadas (nem o nome
  das outras viaja mais; fecha o vazamento de metadado apontado na crítica).
- O corte vira **de exibição**, no template: Full e N1 mostram as N maiores
  **do próprio arquivo** (seletor Top, `dashboard.top_bandeiras`) e somam o
  resto numa linha Σ montada na tela (`__resto__` em `matrizNiveis`), com a
  contagem do arquivo. Níveis em `dashboard.exibir_todas_bandeiras_em`
  (N2, N3) exibem todas, sem seletor Top nem Σ.
- Ganhos e quedas consideram todas as bandeiras do escopo.
- A nota da aba diz de qual universo cada número fala; "as nominais somam X%"
  passa a ser sobre as exibidas.

**Consequência aceita pelo Douglas.** A mesma bandeira pode ser nominal no
arquivo do executivo e estar no Σ do arquivo do head (o corte é por arquivo).
Isto **supera a D-57** (Σ recontado por nível) e a justificativa de
comparabilidade entre arquivos que ela carregava.

**Nenhum número muda** nos totais: reconciliação e particionamento por nível
seguem ao centavo (teste). Muda o que é nominal e o que é Σ em cada arquivo.
`relatorio_qualidade.md §8` passou a declarar "todas no cubo; corte de
exibição". Busca por bandeira e por SKU: D-66.

**Rollback.** git (commits da D-64 e D-65 juntos: um sem o outro não cabe).


---

## D-66 · Busca por bandeira e por SKU (03/09/2026)

**Contexto.** As buscas saíram na D-51 junto com os filtros de bandeira e SKU.
Com todas as bandeiras no arquivo (D-65) e 157 a 9.490 linhas possíveis no
Atacado, "achar uma bandeira específica" voltou a ser pedido do Douglas.

**Decisão.** Campo de busca **dentro do card da matriz**, logo acima da
tabela, na aba **Bandeiras** (por nome de bandeira) e na aba **Categorias**
(por código ou descrição de SKU). Primeiro ficou no topo da aba, antes dos
destaques; o Douglas pediu mais perto da matriz que ele filtra (03/09, noite).
Regras:

- sem acento e sem caixa ("confianca" acha "CONFIANÇA");
- **ignora o corte de exibição**: o que se procura aparece nominalmente,
  esteja ou não no Top N (a busca é o corte enquanto estiver ativa);
- na aba Categorias mantém só as categorias que têm SKU casando e as **abre
  sozinha**; a linha da categoria conserva o valor inteiro dela;
- a nota e o rodapé dizem "busca: N de M; o total soma todas";
- o texto fica no recorte (`qBan`/`qSku` no hash e no `localStorage`), então
  "Copiar recorte" leva a busca junto;
- rerender só da própria aba, com 150 ms de espera entre teclas.

**Onde.** `template_v4.html` (`#bBan`, `#bSku`, `semAcento`, `cfg.busca` em
`matrizNiveis`, `ligarBusca`); guarda em `tests/test_regras.py`. Nenhum número
muda.

**Rollback.** git.


---

## D-67 · Colunas de decisão antes da série, nas três matrizes (03/09/2026)

**Contexto.** Nas capturas dos quatro arquivos de referência (Full, N1
Distribuição, N2 Sul/CO, N3 RS/SC), a última coluna visível da matriz de
Bandeiras sem rolar era o TOTAL da série; ATUAL, ANT., Δ, Δ% e Part. % (o que
se decide) só apareciam rolando para a direita.

**Decisão (opção A, escolhida pelo Douglas entre "decisão primeiro" e "série
recolhível").** Ordem nas três matrizes (hierárquica, Bandeiras, Categorias):

```
nome | ATUAL | ANT. | Δ | Δ% | Part. % || série (até 12 períodos) | TOTAL
```

A série continua à direita como contexto, com o TOTAL dela no fim; uma
divisória marca onde a série começa. A exportação CSV/XLSX segue a mesma
ordem. A nota da matriz foi reescrita na mesma sequência.

**Onde.** `template_v4.html` (`matrizNiveis`: `cabec`, `linhaDo`, rodapé,
`registrarExport`; `notaMatriz`); guarda em `tests/test_regras.py`; docs/08
§2. Nenhum número muda.

**Rollback.** git.


---

## D-68 · Linhas Σ fora da hierarquia em linguagem de leitor (03/09/2026)

**Contexto.** No Full, a matriz e o chip de Head mostravam `NÃO ATRIBUÍDO` e
`INATIVO (SANEAMENTO)`: jargão do pipeline para a diretoria.

**Decisão.** Texto de tela declarado em `config → dashboard.rotulos_exibicao`
(`sem_estrutura: "Sem estrutura comercial"`, `inativo: "Inativos (sem sell-in
há 6 meses)"`). O gerador manda o mapa chave → texto em `rotulos_exibicao`; o
template aplica com `EXIBE(k)` na matriz hierárquica e no chip de Head. **A
chave de dado não muda** (`dimensoes.rotulo_sem_estrutura` / `rotulo_inativo`
seguem no cubo, no relatório, nos CSVs e no recorte salvo), então nada quebra e
o texto pode ser trocado sem reprocessar. A nota da matriz explica os dois
casos sem citar a D-50.

**Onde.** `config.yaml`, `run_dashboard.py`, `template_v4.html`; guarda em
`tests/test_regras.py` (o template não carrega o texto escrito). Nenhum número
muda.

**Rollback.** apagar `rotulos_exibicao` do config (volta a chave).


---

## D-69 · Filtro hierárquico: Gerente, Sup./Exec. e Vend./RCA nas três abas (04/09/2026)

**Contexto.** Pedido do Douglas: "se o head quiser ver algum subordinado
específico nas abas Bandeiras e Categorias, como ele faz?". Não fazia: desde a
D-51 os únicos filtros de dimensão eram Canal, Categoria e Head, e a matriz
hierárquica só navegava a Visão Geral (item 4 da crítica de 03/09).

**Decisão.** Os três níveis abaixo do head voltam ao painel de filtros, como
filtros globais que valem nas três abas. Uma função só (`passaPerfil`) decide o
perfil para os dois cubos, então "ver o executivo X" recorta KPIs, gráfico,
matriz hierárquica, Bandeiras e Categorias ao mesmo tempo. Regras herdadas da
D-54: só opções com dado no recorte; linha some com menos de duas opções (no
arquivo de um N3 as linhas de Gerente e Sup./Exec. somem sozinhas, a de
Vend./RCA fica com os vendedores dele); a cascata é pelo dado (escolher um
gerente deixa na lista só os Sup./Exec. dele). Um único item selecionado
aparece pelo nome na linha de estado; a seleção vai para o recorte salvo e
para o nome do arquivo exportado; "Limpar filtros" limpa os seis filtros.

**Verificado (Full, 04/09):** gerente Sul/CO selecionado → KPI R$ 129,6 mi
(igual ao arquivo N2 dele), matriz só com o ramo dele, Bandeiras com o mesmo
universo de 3.415 do arquivo N2, cascata Sup./Exec. 57 → 4 e Vend./RCA
197 → 25. Arquivo N3 RS/SC: Gerente e Sup./Exec. ocultos, 21 vendedores.

**Chip ou lista suspensa: lista suspensa (decisão do Douglas, 04/09).**
Primeiro saiu com chips; medido no Full eram 13 gerentes (+2 Σ), 55 Sup./Exec.
e 154 Vend./RCA (depois da D-71) em linhas com rolagem, e o caso de uso é um
subordinado por vez. Os três níveis viraram `<select>` de escolha única com
"Todos" no topo (`listaSuspensa`), com as mesmas regras dos chips: só opções
com dado no recorte, a selecionada fica mesmo sem dado marcada "(0)", linha
some com menos de duas opções, cascata pelo dado. O estado continua um Set
(vazio ou um item), então `passaPerfil`, o recorte salvo e o export não
mudaram. Canal, Categoria e Head seguem em chips (poucas opções, escolha
múltipla útil).

**Onde.** `template_v4.html` (`passaPerfil`, `TEM_PERFIL`, `DIMS_FILTRO`,
linhas `frowGer/frowSup/frowVend`, `atualizarOpcoes`, `montarFiltros`,
`atualizarEstado`, recorte, `nomeArquivo`); guarda em `tests/test_regras.py`;
docs/08 §1. Nenhum número muda.

**Rollback.** git.


---

## D-70 · Notas de rodapé dos cards saem da tela (04/09/2026)

**Pedido do Douglas.** "Os textos do rodapé podem sumir, não precisa exibi-los."

**Decisão.** Os quatro blocos `.note` (sob o gráfico de Evolução e sob as três
matrizes) e a função `notaMatriz` saíram do template. O que era dado vivo
continua na própria tabela: a contagem do Σ no rótulo da linha, "Total geral
(N de M exibidas + síntese)" ou "(busca: N de M)" no rodapé, e `*` no
cabeçalho para período parcial. As regras que as notas explicavam (LY pareado
mês a mês, ordenação pelo TOTAL, "–" = ausência, corte de exibição) ficam
documentadas em docs/08 e docs/10.

**Onde.** `template_v4.html`; guarda em `tests/test_regras.py`. Nenhum
número muda.

**Rollback.** git.


---

## D-71 · Vend./RCA que é o próprio Sup./Exec. não é um nível (04/09/2026)

**Pedido do Douglas.** "Quando o Sup./Exec. for igual ao Vend./RCA não tem por
que descer mais um nível", valendo para o filtro e para a matriz.

**Medido antes (cubo de 04/09).** "Igual" só existe pelo **nome**: 0 pares com
rótulo idêntico, 0 com o mesmo código, **43 dos 203 pares com o mesmo nome**
(`1150 - Superv_SPC+Litoral - DEODATO CARMO` → `972 - TT Superv_SPC+Litora -
DEODATO CARMO`). **37 dos 55 Sup./Exec. têm um único vendedor abaixo, e é ele
mesmo** com outro código. Na base inteira, 88 perfis (combinações
head × gerente × sup × canal × projeto × vendedor) são "vendedor = o próprio
sup".

**Decisão.** A igualdade é decidida no gerador, pelo nome (última parte do
rótulo `código - papel - nome`, com o nome inteiro mesmo quando tem " - "
dentro de colchetes), e viaja como **7º elemento do perfil** (posições 0 a 5
não mudam). O template usa a flag em dois lugares:

- **matriz hierárquica**: o caminho para no Sup./Exec.; a linha dele não abre
  (o valor já é o dele). Sup./Exec. que tem ele mesmo **e** outros vendedores
  abre só os outros.
- **filtro Vend./RCA**: essa pessoa não é opção (escolher o Sup./Exec. já é
  escolhê-la). No Full a lista caiu de 197 para 154 chips; no arquivo de um
  Sup./Exec. que é o próprio vendedor, a linha some.

**Verificado.** Arquivo N3 de Deodato Carmo: matriz de uma linha sem expansor,
linhas Gerente/Sup./Exec./Vend./RCA ocultas; Full: 88 perfis marcados no log
do pipeline. Rótulos de ausência nunca casam (teste).

**Onde.** `cubos.py` (`_nome_do_rotulo`, `_mesma_pessoa`, flag no perfil),
`template_v4.html` (`P_VEND_E_SUP`, `vendEhSup`, `renderHier`,
`montarFiltros`, `atualizarOpcoes`); testes. Nenhum número muda: o total do
Sup./Exec. já incluía as vendas dele.

**Rollback.** git.

---

## PROPOSTA EM ABERTO (04/09/2026) · Aba Bandeiras com o nível Cliente e a linha RTM acumulada

**Estado: DECIDIDA em 04/09/2026 à tarde ("vamos abrir a rodada: opção A,
Bandeira > Cliente > Categoria") e executada como D-72, logo abaixo.** A
seção fica como registro da análise que sustentou a decisão.
A maquete estática (CSS do template, números reais de FY2026) foi apresentada
em 04/09 à tarde; é só desenho, não está no repositório.

**Pedido do Douglas.** "Avalie a possibilidade de, na aba Bandeiras, ter a
abertura por cliente na matriz hierárquica." Depois de ver a maquete: "os
clientes RTM não devem aparecer na matriz de bandeira do canal de
Distribuição; talvez seja interessante trazer acumulado: DIST. CLAUMAR ->
CLAUMAR 23,9 mi + RTM (soma dos clientes)". E: "gostei muito da opção, mas
preciso mapear os riscos, lembrando que os dashboards já estão compartilhados".

### O que existe e o que falta

A matriz da aba Bandeiras é a mesma `matrizNiveis` da Visão Geral, que aceita
N níveis e já renderiza quatro. Trocar `["Bandeira","Categoria"]` por
`["Bandeira","Cliente","Categoria"]` é só o `pathFn`. O bloqueio é o dado:
cliente não é eixo de nenhum cubo (D-30, mantido até hoje). Para abrir por
cliente, o cliente tem de entrar no cubo principal.

### Medido em 04/09/2026 (execução 20260904-131459, 3.131.629 linhas de fato)

Cardinalidade: **9.611 das 10.350 bandeiras têm um único cliente** (a
bandeira é o próprio cliente; R$ 919,6 mi, 39,5% da receita). Só 739 têm mais
de um (R$ 1.407,3 mi). Por escopo:

| Escopo | Bandeiras | Com mais de 1 cliente | Receita nessas |
|---|---|---|---|
| N1 Atacado | 9.489 | 542 | 30% |
| N1 Distribuição | 66 | 36 | 69% |
| N2 Sul/CO | 3.415 | 233 | 26% |
| N3 RS/SC | 2.930 | 180 | 24% |

Logo, a regra da D-71 tem de valer aqui: **bandeira com um filho só não ganha
expansor**, senão 93% das linhas abrem para repetir a si mesmas.

Custo no dado (gzip+base64, como viaja no HTML):

| Escopo | Cubo hoje | A: cliente no cubo principal | A com RTM acumulado | B: cubo de cliente à parte, sem categoria | Nomes |
|---|---|---|---|---|---|
| Full | 495.628 linhas, 7,19 MB | 831.155, 11,93 MB | 724.744 (cerca de 10,4 MB) | 157.761, 2,66 MB | 0,25 MB (16.140) |
| N1 Atacado | 437.993, 6,23 MB | 503.215, 7,47 MB | idem (sem RTM) | 101.914, 1,70 MB | 0,19 MB (11.147) |
| N1 Distribuição | 12.770, 0,21 MB | 119.552, 1,53 MB | 18.654 | 20.140, 0,32 MB | 0,03 MB (1.684) |
| N2 Sul/CO | 156.269, 2,11 MB | 184.312, 2,58 MB | idem | 36.550, 0,59 MB | 0,07 MB (4.094) |
| N3 RS/SC | 128.303, 1,70 MB | 139.763, 1,95 MB | idem | 28.901, 0,46 MB | 0,06 MB (3.339) |

RTM (só existe no head de Distribuição: 1.596 clientes com fato; os 166 sem
distribuidor estão fora da hierarquia): 25 das 66 bandeiras têm RTM; a soma
RTM é R$ 39,7 mi dos R$ 278,7 mi do head no FY2026; só 14 bandeiras têm mais
de um CNPJ próprio. Os pontos migrados ainda faturam direto cerca de R$ 3 mi
por mês até ago/26.

| Bandeira | CNPJs próprios | Clientes RTM | Próprio FY26 | RTM FY26 |
|---|---|---|---|---|
| DIST. CLAUMAR | 1 | 109 | 20,9 mi | 3,1 mi |
| DIST. LOBO | 1 | 0 | 15,7 mi | 0 |
| DIST. CENTRAL | 1 | 1 | 14,9 mi | 0,1 mi |
| DIST. DISO | 1 | 355 | 0,8 mi | 8,5 mi |
| DIST. CHUA | 2 | 2 | 9,1 mi | 0 |
| DIST. PELLAH | 1 | 280 | 0,5 mi | 8,5 mi |

Carga do Full publicado, medida no navegador em 04/09, e projeção proporcional
às linhas da opção A com RTM acumulado:

| Full | Hoje | Opção A (projeção) |
|---|---|---|
| Linhas do cubo principal | 495.628 | 724.744 (+46%) |
| Arquivo | 14,96 MB | cerca de 18,4 MB |
| Abertura | 1,15 s | cerca de 1,5 s |
| Memória do navegador (heap) | 170 MB | cerca de 230 MB |
| Renderizar a aba Bandeiras | 0,68 s | cerca de 1,0 s |
| Folga até o teto de 25 MB (D-48), a 4% ao mês | 13 meses | 8 meses |

Arquivos compartilhados: Atacado 11,1 para cerca de 12,4 MB; Distribuição
1,25 para 1,5; Sul/CO 3,8 para 4,3; RS/SC 3,1 para 3,4. O teto de 25 MB foi
fixado na D-48 por duplo clique em máquina corporativa e anexo de e-mail; só
o Full chega perto, e o Full não é compartilhado.

### Como ficaria (opção A, a preferida na análise)

- **Nível 0, bandeira**: igual a hoje (Top N + Σ no Full e N1, todas no N2 e
  N3, busca, ganhos/quedas). Ganha o expansor ▸ só quando tem mais de um filho.
- **Nível 1, cliente**: rótulo `código - nome` (o nome vem truncado em 35
  caracteres do Sell In; há nomes iguais com códigos diferentes, por isso o
  código). Na Distribuição, sob o distribuidor ficam os CNPJs próprios dele e
  **uma** linha Σ "RTM (soma de N clientes)" com o histórico direto dos pontos
  migrados; nenhum cliente RTM aparece nominalmente. A linha RTM abre por
  categoria como as outras e fica por último entre os filhos.
- **Nível 2, categoria**: o que cada cliente compra.
- Pai = soma dos filhos por construção, Total geral = KPI, exportação das
  linhas visíveis, como hoje. **Nenhum número do nível bandeira muda.**

Quando os RTM pararem de comprar direto: a linha RTM vai a "–" nos meses
novos e aparece com queda contra o ano anterior; o CNPJ do distribuidor sobe;
a bandeira soma os dois e é o número comparável (é o propósito da D-59). Os
ganhos/quedas da aba são por bandeira, então não há queda falsa. O cliente
RTM **nunca é inativado pelo saneamento** (a regra RTM tem precedência sobre a
base Faltando, `saneamento.py`), então o histórico não vai para "Inativos".
Quando período e LY ficarem sem faturamento direto, a linha some sozinha, sem
limpeza manual (a matriz só cria nó a partir de linhas dos meses
selecionados). Condição: a base RTM_DePara_Transicao tem de continuar com
esses clientes; tirar um de lá devolve o histórico dele à bandeira original e,
como não está na Consolidada, a "Sem estrutura comercial".

Rotas alternativas medidas: **B**, cubo de cliente à parte sem categoria (+2,9
MB no Full, mas só Bandeira → Cliente e a aba precisaria de um seletor "abrir
por Categoria ou por Cliente", dois cubos para reconciliar); **C**, opção A só
nos arquivos N2/N3 (o P10 original), reagregando sem cliente para Full e N1,
que deixa de fora o head da Distribuição, quem mais ganharia.

### Riscos mapeados

Para quem já tem o link:

1. **Publicação sem homologação.** Qualquer `run_dashboard.py` com o código
   novo substitui os 73 arquivos na hora. Mitigação (a da D-63): desligar
   `dashboard.publicacao.ativo` durante a rodada, gerar em `dashboard/build`,
   conferir, religar só com o ok do Douglas.
2. **Rollback**: `git revert` + gerador republica a versão anterior em cerca
   de 12 s; o SharePoint guarda o histórico de versões como segundo caminho.
   Quem estiver com o arquivo aberto segue na versão antiga até reabrir.
3. **Mudança de hábito.** Na ordem Bandeira → Cliente → Categoria a categoria
   desce um clique. A ordem Bandeira → Categoria → Cliente mantém o de hoje
   intacto e só acrescenta um nível abaixo, mas separa a cesta do cliente por
   categoria. O grão da opção A serve às duas; é a decisão de maior impacto no
   usuário.
4. **Nada guardado no navegador quebra**: a chave `dashDoriCanais.recorte.v5`
   guarda só filtros; a expansão (`EXP`) vive em memória. Não precisa trocar a
   chave.
5. **Nomes de cliente em arquivo compartilhado**: dado novo. O N1 Atacado
   levaria 11.147 razões sociais; o recorte físico da D-52 garante que cada
   arquivo leva só os clientes do próprio escopo, e são clientes que essas
   pessoas já veem no ERP. Decisão do Douglas mesmo assim.
6. **Arquivo maior no SharePoint**: +1,3 MB no Atacado, menos de 0,5 MB nos
   demais.

Dado e regra de negócio:

7. **RTM acumulado depende** de `saneamento.rtm_herda_bandeira: true` (senão o
   RTM não está sob o distribuidor) e da base RTM continuar com os clientes.
   A regra tem de ser "acumula só quando herdou a bandeira".
8. Os **166 RTM sem distribuidor** ficam nominais sob a própria bandeira, e só
   no Full (não entram em arquivo de nível nenhum).
9. **Identidade do cliente**: nome truncado em 35 caracteres; mesmo nome com
   dois códigos aparece em duas linhas. Rótulo = código + nome.
10. **Um filho só não abre** (regra da D-71, genérica na matriz) e a **linha Σ
    RTM fica por último** entre os filhos (hoje só o nível 0 tem essa ordem).
11. **Reconciliação**: o pipeline continua abortando se o cubo não fechar com
    a fato; o desvio de arredondamento cresce com os grupos (de 26 para uns
    40 centavos), dentro da tolerância de 1e-6. Caixas nulas viram 0 por
    grupo (A13), mais grupos, mesmo total.

Técnico:

12. **Layout do cubo**: um índice a mais por linha. Colocado DEPOIS do perfil,
    as posições 1 (bandeira), 2 (categoria) e 3 (perfil) que o template lê
    não mudam; só as métricas deslocam uma casa (`BASE_MET` 4 → 5, base da
    reconciliação 4 → 5). Toca `cubos.py` (grão + flag RTM lida da
    DIM_CLIENTE, que já a tem), `filtrar_por_nivel` (reindexar cliente e
    nomes por arquivo), o template em três pontos (`pathFn`, `rotNo`, regra
    de filho único/Σ por último), cerca de 15 asserts posicionais em
    `tests/test_regras.py` e os cenários sintéticos. `VERSAO_CACHE` não muda
    (o cache cobre a leitura dos Excel).
13. **Tempo**: segundos a mais no groupby do pipeline; geração dos 73
    arquivos de 12 para uns 15 s.
14. **Docs** no mesmo turno: 05, 06, 08, 09, 12, 13 e README.

### Rodada sugerida (sem executar nada agora)

Desligar a publicação; implementar; 63/63 + cenários; gerar os 73 em build;
script que compare os totais por bandeira de cada arquivo novo com o publicado
hoje, ao centavo; abrir Full, Atacado, Sul/CO e RS/SC no navegador e medir
carga; ok do Douglas; religar e publicar; aviso de uma linha aos usuários
("a bandeira agora abre por cliente").

### Decisões pendentes (viram a D-72)

1. Rota: A (recomendada), B ou C.
2. Ordem dos níveis: Bandeira → Cliente → Categoria ou Bandeira → Categoria →
   Cliente.
3. Nome de cliente pode ir nos arquivos N1 (Atacado com 11.147 nomes)?
4. Contagem no rótulo "RTM (soma de N clientes)": fixa (histórica, como o "N
   bandeiras" do Σ) ou do período selecionado.
5. A busca da aba também acha cliente?
6. Folga menor até o teto de 25 MB no Full (8 meses a 4% ao mês): aceitar, ou
   rever o teto, já que a distribuição é por SharePoint e não por e-mail.

**Rollback.** Não se aplica (nada implementado).

---

## D-72 · Aba Bandeiras abre por Cliente; clientes RTM acumulados sob o distribuidor (04/09/2026)

**Decisão do Douglas** (04/09/2026 à tarde, depois da análise e da maquete
registradas na seção anterior): "vamos abrir a rodada: opção A, Bandeira >
Cliente > Categoria". Das seis perguntas pendentes, ele fechou a rota (A) e
a ordem dos níveis; as outras quatro ficaram no padrão declarado aqui:
nomes de cliente vão nos arquivos N1 (a opção A exige); a contagem do rótulo
RTM é **fixa** (histórica, como o "N bandeiras" da linha Σ); a busca continua
só por bandeira; o teto de 25 MB do Full fica como está (não é arquivo
compartilhado).

**O que mudou.**

- **Cubo principal** (`cubos.py`): o CLIENTE entrou como 5º índice, DEPOIS do
  perfil (`[mês, bandeira, categoria, perfil, cliente, R, P, C]`), então as
  posições 1/2/3 que o template lê não mudaram; as métricas deslocaram uma
  casa (`BASE_MET` 4 → 5, `BASE_MET_SKU` 3, exportadas para o gerador e os
  testes: fim dos números soltos). `dims.cli` = `[código, nome, n_rtm]`.
- **RTM acumulado**: cliente RTM cuja bandeira foi de fato trocada pela do
  distribuidor (`DIM_CLIENTE.BANDEIRA_HERDADA`, coluna nova gravada pelo
  `saneamento.py` na D-59) vira **uma chave sintética por bandeira**
  (`RTM@<bandeira>`, nunca colide com código); `n_rtm` = clientes RTM
  distintos com sell-in atrás dela. "Acumula só quando herdou": com
  `saneamento.rtm_herda_bandeira: false` ou distribuidor sem bandeira, o
  cliente segue nominal. `dashboard.cliente_rtm_acumulado: false` mostra cada
  RTM pelo nome (rollback pelo config). Rótulo de leitor em
  `dashboard.rotulos_exibicao.rtm_acumulado` ("RTM (soma de {n} clientes)").
- **Gerador** (`filtrar_por_nivel`): `dims.cli` encolhe para os clientes do
  escopo, reindexados; assert por arquivo de que toda linha aponta para um
  cliente da lista. A contagem RTM não muda por arquivo (todos os RTM de um
  distribuidor carregam a hierarquia dele).
- **Template v4**: `BASE_MET = 5`; `METRICAS.col` virou posição dentro do
  triplo `[R, P, C]` (o último `col-4` solto saiu); `BAN_MULTI` decidido uma
  vez na carga (bandeira com mais de um cliente no arquivo); a matriz da aba
  Bandeiras é `["Bandeira","Cliente","Categoria"]` com **chave tipada** abaixo
  da bandeira (`c<i>` cliente, `k<i>` categoria) porque a profundidade não
  diz mais qual dimensão é a linha: bandeira de um cliente só **pula o
  nível** (caminho `[bandeira, categoria]`, como antes; lógica da D-71),
  bandeira com vários abre por cliente e o cliente abre por categoria.
  `matrizNiveis` ganhou `nivelDe` (nome do nível pela chave, para título e
  exportação) e `acumFn` (linha acumulada: "Σ " no rótulo, classe `fora`, por
  último entre os irmãos, expansível).
- **Ferramenta nova** `ferramentas/comparar_paineis.py`: publicado × build,
  sem navegador (total geral, por mês, por bandeira dentro do teto teórico
  de arredondamento de 1 unidade por linha de cubo; SKU e dimensões exatos;
  pareia pelo caminho e avisa de cópia avulsa).

**Medido (execução 20260904-183146, 3.131.629 linhas, R$ 2.326.876.207,52).**

| | Antes (D-71) | D-72 |
|---|---|---|
| Cubo principal | 495.628 linhas | **730.257** (831.155 se cada RTM fosse nominal) |
| Clientes no eixo | — | 14.544 nominais + 25 linhas RTM somando 1.596 clientes |
| Bandeiras com mais de um cliente (Full) | — | 739 de 10.350 (Distribuição: 36 de 66) |
| Full | 14,96 MB | **17,60 MB** (cubos 45,2 MB → 17,3 compactados) |
| N1 Atacado · Distribuição | 11,14 · 1,25 MB | 12,39 · 1,34 MB |
| N2 Sul/CO · N3 RS/SC | 3,78 · 3,11 MB | 4,38 · 3,49 MB |
| Full no navegador: abertura · aba Bandeiras · Visão Geral | 1,15 s · 0,68 s · 0,17 s | 1,8 s · 1,07 s · 0,27 s |
| Pipeline · geração dos 73 | 35 s · 12 s | 35 s · 21 s |

**Prova de que nenhum número de bandeira mudou**: `comparar_paineis.py`
contra os 73 arquivos publicados às 13:16 (mesma base): 73 de 73 dentro do
teto; cubo de SKU e listas de dimensão idênticos; pior desvio de bandeira 18
centavos (KA Regional e Full), diferença do total geral do Full −18 centavos
em R$ 2,33 bi (mais grupos, mais arredondamentos, dentro da tolerância de
1e-6 do pipeline). A ferramenta achou uma **cópia avulsa** do Full em
`Painéis Comerciais\Gerencial\Dashboard - Full\` (00:23 de 04/09, fora da
publicação automática, que só grava na raiz): ignorada na comparação,
reportada ao Douglas.

**Verificado no navegador (zero erro no console).** Full: cabeçalho
"Bandeira › Cliente › Categoria"; ATACADAO abre em 415 CNPJs ordenados pelo
valor, `1023022 - ATACADAO S.A.` abre em categorias; DIST. LOBO (um cliente)
tem o título "abrir Categoria" e abre direto; DIST. CLAUMAR abre em
`1003318 - CLAUMAR ALIMENTOS LTDA` R$ 20,9 mi + `Σ RTM (soma de 109
clientes)` R$ 3,1 mi por último, que abre em GOMAS/BALA/AMENDOIM; Total
geral = KPI (R$ 1,2 bi). N1 Distribuição: 66 bandeiras, 36 com expansor de
cliente, 113 clientes no arquivo (88 nominais + 25 linhas RTM), DIST. DISO =
CNPJ próprio R$ 764,1 mil + Σ RTM (355) R$ 8,5 mi, DIST. CHUA = 2 CNPJs + Σ
RTM (2) R$ 19,3 mil; Total geral = KPI R$ 278,7 mi.

**Testes.** 68/68 unitários (63 + 5 da D-72: posições e soma por bandeira,
RTM acumulado com rollback pelo config, recorte por nível reindexando
clientes, flag do saneamento, guarda do template) e 6/6 cenários.

**O que o usuário vê mudar.** Só o expansor ▸ nas bandeiras com mais de um
cliente e o nível a mais; nada do nível bandeira, dos ganhos/quedas, da
busca, dos filtros ou das outras abas muda. A categoria de uma bandeira com
vários clientes fica um clique abaixo (dentro do cliente).

**Publicação.** Desligada em commit próprio antes de qualquer alteração
(`b0f5cf8`) porque os 73 arquivos já estão compartilhados. **Religada em
04/09 à noite com o ok do Douglas** ("pode publicar"): `publicacao.ativo:
true`, geração em 24,5 s, 72 arquivos nas pastas por usuário + o Full na
raiz, MD5 conferido na cópia e o publicado byte a byte igual ao build.
Aviso de uma linha aos usuários fica com o Douglas: "a bandeira agora abre
por cliente".

**Rollback.** `git revert` dos commits da D-72 + `run_dashboard.py` (republica
o anterior em ~20 s); parcial, sem código: `dashboard.cliente_rtm_acumulado:
false` (RTM nominal) — o nível Cliente em si não tem chave de desligar, é o
grão do cubo.

**Onde.** `src/transform/saneamento.py` (`BANDEIRA_HERDADA`), `src/load/cubos.py`
(eixo, chave RTM, `BASE_MET`), `run_dashboard.py` (`filtrar_por_nivel`,
`rotulos_exibicao`), `dashboard/template_v4.html` (`CLIDE`, `rotCli`,
`BAN_MULTI`, `matrizNiveis`, `renderBandeiras`), `config/config.yaml`
(`cliente_rtm_acumulado`, `rotulos_exibicao.rtm_acumulado`, publicação),
`ferramentas/comparar_paineis.py`, testes, docs 05/06/08/09/11/13, README.

---

## D-73 · O Full é publicado na pasta `Dashboard - Full\`, não na raiz (04/09/2026 à noite)

**Pedido do Douglas.** "Quero que agora o Full grave na pasta
`Painéis Comerciais\Gerencial\Dashboard - Full`, pois precisei compartilhar
com pessoas que não podem ver os outros."

**Contexto.** Pela Q13 (D-52) o Full ficava na raiz do destino, fora das
pastas compartilhadas, e só quem tinha acesso à raiz o via. Compartilhar a
raiz daria visibilidade a todas as pastas de colaborador; por isso o Douglas
criou a pasta `Dashboard - Full\` à mão (00:23 de 04/09, a "cópia avulsa"
que a ferramenta de comparação achou, P11) e à noite moveu o Full da D-72
para lá. A geração continuava gravando na raiz, então a pasta envelheceria a
cada execução.

**Decisão.** `dashboard.publicacao.pasta_full: "Dashboard - Full"`: a geração
grava o Full nessa subpasta do destino (`pasta_do_full` em
`run_dashboard.py`; vazio = raiz, regra anterior). A raiz não recebe mais o
Full. `limpar_paineis_antigos.py` passa a esperar o Full no mesmo lugar, de
modo que um Full deixado na raiz por engano vira candidato a quarentena. O
nome do arquivo não muda: o link da pasta continua válido. Resolve a P11.

**Verificado.** Geração com a chave nova: 72 arquivos nas pastas por
usuário + o Full em `Dashboard - Full\` (MD5 conferido), nenhum
`Dashboard_Gerencial.html` na raiz; teste unitário da regra (subpasta,
vazio, ausente; o config tem de declarar a pasta).

**Onde.** `config/config.yaml`, `run_dashboard.py` (`pasta_do_full`),
`ferramentas/limpar_paineis_antigos.py`, testes, docs 10/13/15, README.

**Rollback.** `pasta_full: ""` volta o Full para a raiz, sem código.

---

## D-74 · Metas FY27 por cliente × categoria × mês no painel (08/09/2026)

**Contexto.** O Comercial entregou `bases/Metas/Metas_FY'27.xlsx` (criado em
08/09/2026 09:38): formato longo, uma linha por `CÓDIGO CLIENTE` ×
`CATEGORIA` × `Período` × `Tipo Meta` (`VALOR (R$)` / `VOLUME (KG)`), com
set/26 e out/26 (146.794 pares cliente×categoria×mês, 11.133 clientes, 10
categorias). É o "novo arquivo de metas cruzado pela chave do cliente" que a
D-49 previu ao remover o tema Metas antigo (rota A por bandeira). O total de
set/26 (R$ 122.279.463,48) bate ao centavo com a base antiga: é a mesma meta,
rateada por cliente. A análise prévia (pedida "só análise, sem alterar nada")
está resumida no README e mediu: 11.133/11.133 clientes na DIM_CLIENTE,
10/10 categorias no modelo, 1.034 pares negativos (318 clientes, R$ −96.066;
493 dos 517 de set/26 coincidem com realizado negativo no FY26: o rateio
herdou o sinal das devoluções), 14.599 pares abaixo de 1 kg, custo de 0,96 MB
por mês de meta no Full.

**Decisões do Douglas (08/09/2026, respostas Q1–Q10):**

| # | Decisão |
|---|---|
| Q1 | Metas negativas **entram como estão**; sai um arquivo com os casos isolados e a soma por bandeira (`data/quality/metas_negativas.csv`, `metas_negativas_por_bandeira.csv`) |
| Q2 | O leitor **varre `bases/Metas/*.xlsx`**; o mesmo mês em dois arquivos aborta |
| Q3 | A meta de um mês já carregado **pode mudar**: releitura completa e **registro** das mudanças (`data/quality/metas_revisoes.csv`, append, com aviso) |
| Q4 | Cliente com meta que nunca faturou entra na DIM_CLIENTE pela Hierarquia_Consolidada; sem linha lá, "Sem estrutura comercial" com aviso |
| Q5 | Categoria que não existe no modelo **aborta** |
| Q6 | Primeira onda: **KPIs + colunas nas matrizes**; barra de meta na Evolução fica para a segunda |
| Q7 | Teto do arquivo sobe de 25 para **35 MB**, com abertura e heap medidos a cada rodada |
| Q8 | Atingimento em mês parcial **é mostrado**, marcado "(parcial)" |
| Q9 | `VOLUME (KG)` da meta = mesmo conceito do `Peso Líquido` do sell-in (confirmado) |
| Q10 | Sem meta de caixas e sem meta por SKU: aceito |

**Como ficou.**

1. **Leitor** `src/extract/metas.py` (config `fontes.metas`): pasta varrida,
   competência do conteúdo (`Período` como data, serial do Excel ou texto
   AAAA-MM), `digitos()` no cliente, `texto()` na categoria, mapa
   `tipos_meta` do config (tipo desconhecido aborta), chave duplicada / nulo /
   período irreconhecível abortam, pivô para `META_RECEITA` + `META_PESO_KG`
   e reconciliação interna (pivô × soma bruta por mês). Arquivo aberto no
   Excel vira mensagem "feche o arquivo". Cache por hash em staging.
2. **Pipeline**: `FATO_META` (ANO_MES × COD_CLIENTE × CATEGORIA, em R$ e kg)
   gravada na curated; `DIM_CALENDARIO` cobre até o último mês com meta
   (out/26 entrou sem sell-in: 26 meses, FY2027); `dim_cliente(...,
   clientes_extra)` acolhe cliente só com meta (flag `SEM_SELLIN`, zero casos
   hoje); `metas.conferir_categorias` aborta categoria estranha;
   `metas.registrar_revisoes` compara com a FATO_META da execução anterior
   antes de sobrescrever; seção **11** do relatório de qualidade.
3. **Cubo** `cubo_meta` (`cubos.construir(..., fato_meta)`): os **mesmos cinco
   índices do principal** [mês, bandeira, categoria, perfil, cliente] +
   [META_R$ em centavos, META_KG em gramas], escalas `ESC_RECEITA`/`ESC_PESO`.
   Cruzamento = join pela chave do cliente na DIM_CLIENTE: a meta herda
   bandeira, hierarquia, canal e a regra RTM (cliente que herdou a bandeira
   soma na linha Σ do distribuidor) sem código próprio de atribuição. Os
   eixos são a união realizado ∪ meta. `reconciliar_meta` aborta se a soma
   por mês não bater com a FATO_META. Cubo separado, não colunas a mais no
   principal: 69.260 dos 73.397 pares de set/26 não têm sell-in no mês.
4. **Gerador**: `filtrar_por_nivel` recorta o `cubo_meta` pelo mesmo perfil e
   reindexa categoria/bandeira/cliente pela união; três asserts por arquivo;
   particionamento da meta por nível no log; `dashboard.teto_mb: 35` aborta
   acima do teto.
5. **Template v4** (primeira onda): `somarMeta`/`metMeta` sobre `IDX_META`
   com os mesmos filtros; cards Valor e Volume ganham "Meta · Ating." (Caixas
   não); as três matrizes ganham **META** e **ATING. %** logo depois de ATUAL
   (ordem D-67 mantida; exportação acompanha), só quando o período tem mês
   com meta; atingimento = realizado **dos meses com meta** ÷ meta desses
   meses (cabeçalho diz "(k/n m.)" quando a meta cobre parte do período e
   "(parcial)" quando há mês não fechado); SKU sem meta (n/d); mês só com
   meta aparece nos chips com a marca "0" e o título "tem meta"; linha de
   estado e cabeçalho declaram os meses com meta; abertura e heap saem no
   console (`painel: abertura … ms · heap … MB`).

**Medido em 08/09/2026.** Pipeline 37 s (leitura da meta 3,6 s);
CUBO_META 146.106 linhas; Full 17,62 → **19,46 MB** (+0,92 MB por mês de
meta), abertura 3,7 s, heap 200 MB; N3 RS/SC 1,1 s, heap 43 MB; 73 arquivos
em 19 s; meta particiona por nível ao centavo (R$ 241.828.369,97 nos
níveis + R$ 402.376,18 fora da hierarquia = R$ 242.230.746,15; a diferença
de R$ 1,33 para a soma da planilha é o arredondamento a centavos por linha).
Na tela (FY2027, set+out/26): KPI "Meta R$ 242,2 mi · Ating. 4,8% (parcial)",
head Atacado R$ 96,7 mi, categoria AMENDOIM R$ 75,5 mi, bandeira LASA
R$ 15,7 mi, Total geral = KPI nas três abas; executivo RS/SC R$ 12,8 mi.
Negativas: 568 pares bandeira×categoria×mês com algum cliente negativo; a
soma da bandeira na categoria fica negativa em 366 e a da bandeira inteira
em 204 (102 bandeiras por mês, a pior UMBELINO DA SILVA REIS ME em
R$ −1.777). 78/78 unitários (9 novos), 6/6 cenários.

**Segunda onda, no mesmo dia (pedido dele: "no gráfico de Evolução
precisamos exibir a meta e o atingimento").** Barra **Meta** (âmbar, à
direita do Atual: passado, presente, alvo) só nos grupos que têm mês com
meta; grupo sem meta fica sem barra (null, nunca zero). Por grupo, a meta é
a soma dos meses do grupo que têm meta e o atingimento é o realizado desses
meses ÷ meta (mesma regra dos cards e matrizes). Rótulo da barra: valor em
cima e atingimento em negrito embaixo; tooltip "Meta: … · Ating.: …%", com
"(meta de k de n meses)" quando a meta cobre parte do grupo e "(parcial)"
quando há mês não fechado. A série (e a legenda) só existe quando o período
tem meta e a métrica não é Caixas. Verificado: FY2027 por mês, set/26 barra
Meta R$ 122,3 mi · 4,8% e out/26 R$ 120 mi · n/d (sem sell-in); por ano,
uma barra FY2027 R$ 242,2 mi · 4,8%; FY2026 sem barra nem legenda de meta.

**Fica para depois (decisão dele):** busca por cliente; meta de caixas e
por SKU (não existem na base).

**Onde.** `config/config.yaml` (`fontes.metas`, `dashboard.teto_mb`),
`src/extract/metas.py` (novo), `src/transform/dimensoes.py`,
`src/load/cubos.py`, `src/qualidade.py` (§11), `run_pipeline.py`,
`run_dashboard.py`, `dashboard/template_v4.html`, `tests/test_regras.py`,
docs 05/06/08/10/11, README.

**Rollback.** Tirar os arquivos de `bases/Metas/`: o painel sai sem meta
(FATO_META vazia, `cubo_meta` vazio, nenhuma coluna ou card de meta), sem
tocar em código.

---

## D-75 · Nomes das colunas de decisão das matrizes: ano selecionado, LY e YTD (08/09/2026)

**Pedido do Douglas.** "ATUAL = FY27 (é dinâmico ou exibe sempre FY27?),
ANT. = LY, a última coluna da matriz (Total) = YTD."

**Fato medido antes de mudar.** A coluna TOTAL somava as **12 colunas
exibidas** da série (nov/25 a out/26 em 08/09), não o acumulado do ano: com
o FY2027 selecionado ela trazia 10 meses do FY2026 dentro. Renomear sem
mudar a conta seria número enganoso.

**Decisão.**

1. **ATUAL → ano selecionado, dinâmico**: "FY2027" na base fiscal, "2026" na
   base calendário (o mesmo ano do chip "Ano"). Quando a seleção de meses não
   é o ano inteiro oferecido, o cabeçalho diz "FY2027 (2 m.)" e o tooltip
   traz o intervalo ("set/26 a out/26 (2 meses)"). A conta não mudou: é o
   período selecionado.
2. **ANT. → LY**, como nos cards.
3. **TOTAL → "YTD FY2027"** (ou "YTD 2026"): o **acumulado do ano
   selecionado até o último mês escolhido**, pela mesma junção
   `ytdFiscal`/`ytdCalendario` que o "Comparar" já usa. Tooltip com o
   intervalo. A série de até 12 períodos continua como contexto à esquerda.
   A ordenação padrão das matrizes e a exportação passam a seguir o YTD.
   Com o ano inteiro selecionado, ATUAL = YTD por construção; com uma
   seleção parcial (só jun/26, por exemplo), ATUAL é jun/26 e YTD é set/25 a
   jun/26.

**Verificado.** Full, FY2027 (set+out/26): cabeçalho "FY2027 | META |
ATING. % (PARCIAL) | LY | Δ | Δ% | PART. % | … | YTD FY2027", Total geral
ATUAL = YTD = R$ 11,7 mi (tooltips "set/26 a out/26 (2 meses)" e "acumulado
de set/26 a out/26"); FY2026 com jun/26 só: ATUAL "FY2026 (1 m.)" R$ 101,8
mi (Atacado R$ 40 mi) e YTD FY2026 (set/25 a jun/26, 10 meses) R$ 964,5 mi
(Atacado R$ 372,4 mi); base calendário 2026 inteiro: "2026" e "YTD 2026",
R$ 787,3 mi nas duas. Exportação com os mesmos nomes ("FY2027", "LY",
"YTD FY2027"). Zero erro no console. Guarda da D-67 atualizada; 78/78.

**Onde.** `dashboard/template_v4.html` (`rotuloAnoSel`, `mesesYtd`,
`matrizNiveis`), `tests/test_regras.py`, docs/08, README.

---

## D-76 · Cores do gráfico de Evolução (opção A) e fim da linha de Δ% com eixo próprio (08/09/2026)

**Pedido do Douglas.** "Não achei as cores do gráfico muito friendly; quais
opções temos?" e, diante das opções, "Opção A; acho que o Δ% pode não ter a
linha mesmo, como recomendado".

**Medido antes.** O validador de paletas do kit de dataviz (six checks:
faixa de luminosidade, saturação, separação para daltônicos, separação
normal, contraste) reprovou a combinação de então: Meta âmbar `#f4cf6a` e
linha laranja `#f5a623` com distância 9,8 (mínimo 15, "difícil de
distinguir mesmo com visão normal") e LY `#c2cfdc` com contraste 1,5:1
sobre o fundo. Três candidatas foram apresentadas lado a lado num mock com o
mesmo desenho do gráfico.

**Decisão.**

1. **Opção A**: LY `#5e94c9` (azul médio, tom do Atual: mesma entidade, ano
   anterior), Atual `#00539f` (azul Dori), Meta `#c97b12` (laranja queimado,
   sem contorno). Validador: separação para daltônicos 20,8 no pior par,
   contraste acima de 3:1 nas três; o LY fica no limite de saturação por
   ser tom do Atual de propósito.
2. **A linha "Δ% vs LY" e o eixo direito em % saíram.** Motivo do kit
   (aceito por ele): dois eixos no mesmo gráfico fazem a linha parecer
   maior ou menor que as barras sem ser. O Δ% do grupo passa a ser a
   **segunda linha do rótulo da barra Atual** (verde/vermelho, negrito), só
   onde o par no LY é completo, e entra no tooltip da barra ("Atual: R$ … ·
   Δ% vs LY: +…%"). A legenda fica com três itens. Rótulo do LY em azul
   escuro `#3f6e9b`, do Atual `#003a70`, da Meta `#8a5a00`, os três com o
   valor em cima e a taxa embaixo no mesmo desenhador.

**Verificado.** Full, FY2027 (Valor): três barras por grupo, sem eixo
direito; set/26: LY R$ 103,5 mi, Atual R$ 11,7 mi com "−88,7%" embaixo,
Meta R$ 122,3 mi com "9,6%"; FY2026 sem barra Meta e sem legenda de meta;
tooltip da barra Atual traz o Δ%; zero erro no console. 78/78.

**Onde.** `dashboard/template_v4.html` (`renderEvolucao`, `rotuloBarras`),
`tests/test_regras.py`, docs/08, README.

---

## D-77 · Os dois percentuais do gráfico dizem o que são (08/09/2026)

**Pedido do Douglas.** "Ficou confuso, precisamos ter a indicação do que é
cada percentual no gráfico: Δ% LY e % ating. Como podemos fazer? Marcador +
legenda? Descrição no rótulo? Não mude nada ainda." Quatro formas foram
mostradas lado a lado (texto no rótulo; marcador + legenda; percentuais na
segunda linha do eixo; faixa acima do grupo) com prós e contras medidos na
largura das barras; ele escolheu **"opção 1 com abreviação inteligente"**.

**Decisão.** A segunda linha do rótulo **nomeia** o percentual: "Δ LY
−88,7%" na barra Atual e "ating. 9,6%" na barra Meta. O desenhador mede
(`measureText`) se o texto mais largo do gráfico cabe no espaço de uma
barra (largura da área ÷ grupos ÷ séries visíveis, menos 4 px); quando não
cabe (tipicamente 12 meses com 3 barras), todos os rótulos caem para a forma
curta com marcador ("▼ −88,7%", "◎ 9,6%") e o título do gráfico ganha a
explicação "▲▼ Δ% vs ano anterior · ◎ % da meta". A decisão é por largura
real, nunca por contagem de meses: trimestre, semestre e ano têm barras
largas e ficam por extenso. O tooltip diz por extenso nos dois casos.

**Verificado.** Full, Valor, tela de 1600 px (área do gráfico 1.452 px):
FY2027 por mês (2 grupos, 3 séries), FY2026 por mês (12 grupos, 2 séries)
e FY2026 por trimestre ficam **por extenso**, sem sufixo no título. Tela
de 800 px (área 240 px): os três casos caem para o marcador e o título
ganha "▲▼ Δ% vs ano anterior · ◎ % da meta". Com 12 meses e 3 séries a
1600 px o espaço por barra é 40 px e a forma curta entra. Zero erro no
console. 78/78.

**Onde.** `dashboard/template_v4.html` (`rotuloBarras`),
`tests/test_regras.py`, docs/08, README.

**Publicação (08/09/2026, "Aprovado, pode publicar").** `publicacao.ativo:
true`, geração com a execução `20260908-105634`: 72 arquivos por nível nas
pastas de colaborador + o Full em `Dashboard - Full\`; 73 de 73 publicados
com MD5 igual ao build. A partir daqui todo `run_dashboard.py` republica
D-74 a D-77.

---

## D-78 · Busca por cliente na aba Bandeiras (08/09/2026 à tarde)

**Pedido do Douglas.** "Vamos abrir a próxima rodada: busca por cliente na
aba Bandeiras." Publicação desligada antes (`62199ef`).

**Contexto.** Desde a D-72 a matriz da aba é Bandeira › Cliente ›
Categoria, mas o nível Cliente só existe nas bandeiras com mais de um
cliente (`BAN_MULTI`; 9.611 das 10.350 bandeiras têm um só e abrem direto em
categoria). A busca da D-66 olhava só o rótulo da bandeira: quem procurava um
CNPJ ou um nome de cliente não achava nada.

**Decisão.** A **mesma caixa** da aba passa a achar a bandeira pelo rótulo
**ou por qualquer cliente dela** (código ou nome, sem acento e sem caixa).
Os clientes de cada bandeira (`BAN_CLIS`, índices em `dims.cli`) são
decididos uma vez na carga, sobre o cubo principal e o de meta, como o
`BAN_MULTI`. Regras na matriz (`busca.casaExtra` e `busca.filhoCasa` em
`matrizNiveis`):

1. bandeira que casa pelo **próprio rótulo** aparece inteira, como antes;
2. bandeira que casa **só por um cliente** aparece, abre sozinha e mostra
   apenas os clientes que casam (as categorias abaixo do cliente ficam);
3. bandeira de um cliente só aparece quando o cliente casa, e abre direto em
   categoria, como sempre;
4. a linha Σ RTM entra na busca pelo seu rótulo de leitor ("RTM (soma de N
   clientes)"), como qualquer outro filho.

Não há caixa separada nem opção "buscar por": o leitor digita o que tem
(nome de rede, CNPJ, razão social). O texto continua persistindo no
recorte (`qBan`) e ignorando o corte de exibição (D-66).

**Verificado.** Full, FY2027 (10.350 bandeiras, 739 com mais de um
cliente): "1003318" (CNPJ do DIST. CLAUMAR) → 1 bandeira, aberta, só esse
cliente, Σ RTM oculta, rodapé "busca: 1 de 10350"; "rtm (soma" → 25
bandeiras, cada uma aberta na sua linha Σ RTM; código "1014458" e nome
"DISTRILOBO REPRESENTACOES" (cliente único da DIST. LOBO) → a bandeira,
aberta direto nas categorias; "zzzzqqq" → "Nada encontrado"; limpar a
busca volta às 50 do Top. Zero erro no console. 78/78.

**Onde.** `dashboard/template_v4.html` (`marcarBandeirasMulti`,
`matrizNiveis`, `renderBandeiras`, placeholder), `tests/test_regras.py`,
docs/08, README.

**Publicação (08/09/2026, "Aprovado, pode publicar").** Publicação
religada; 72 arquivos por nível + Full em `Dashboard - Full\`; 73 de 73 com
MD5 igual ao build.

---

## PROPOSTA EM ABERTO · Canal como dimensão (08/09/2026 à tarde, SEM decisão: "não vamos entrar nessa rodada ainda")

Só análise, nada executado. Hoje o canal (7 valores de `Canais.xlsx`) é
apenas **filtro**; nenhuma tabela quebra por canal. O canal já viaja na
posição 3 do perfil dos três cubos (principal, SKU e meta), então qualquer
matriz pode ganhar o nível Canal **sem pipeline, sem MB e com a meta por
canal de graça**; o recorte por nível e a regra RTM (cliente RTM carrega o
canal DISTRIBUIDOR, D-50) já valem. Opções apresentadas: (A) nível na matriz
hierárquica; (B) card novo na Visão Geral, Canal › Categoria, com seletor
para Bandeira no 2º nível (recomendada); (C) Canal › Bandeira › Cliente ›
Categoria na aba Bandeiras; (D) aba "Canais". Perguntas que ficam para quando
ele abrir: onde; 2º nível; vale nos 73 arquivos ou só Full/N1; "SEM CANAL"
(1 cliente) como linha síntese.
