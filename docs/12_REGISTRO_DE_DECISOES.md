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
