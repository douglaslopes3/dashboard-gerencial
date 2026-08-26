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
