# 13 · Fluxo de geração do painel — ponta a ponta

> Para entender o caminho do dado bruto até o painel publicado **sem ler
> código**. Diagrama navegável em [`fluxo_geracao_painel.html`](fluxo_geracao_painel.html)
> (abre por duplo clique). Reescrito em 03/09/2026 para o estado atual: painel
> v4 (D-51), reatribuição RTM e saneamento (D-50, D-59), um arquivo por
> colaborador com publicação automática (D-52, D-58). Números da execução
> `20260903-155531`.

## O fluxo em uma linha

```
 6 bases Excel ──► run_pipeline.py (6 passos) ──► modelo estrela (Parquet)
                                                       │
                     dashboard/template_v4.html ◄──────┤ cubos.json + resumo.json
                     + Chart.js embutido               │
                                ▼                      ▼
                     run_dashboard.py ──► dashboard/build/Dashboard_Gerencial.html
                                          (11,4 MB · um arquivo · abre por duplo clique)
                                     └──► Dashboard_Gerencial_N1_/N2_/N3_<colaborador>.html
                                          (72 arquivos · só os dados do próprio escopo)
                                     └──► publica substituindo em Painéis Comerciais\Gerencial\
                                          (Full em Dashboard - Full\ · um por pasta de colaborador · MD5 conferido)
```

---

## 1. Bases de origem — o que entra

| # | Arquivo | Aba | O que traz | Cadência |
|---|---|---|---|---|
| 1 | `bases/Sell In/sellin_*.xlsx` (29 arquivos) e/ou `data/raw/sell_in/*.xlsx` | `Export` | **o faturamento**: 3.127.196 linhas úteis (3.516 linhas 100% zeradas descartadas, D-36), mês × cliente × SKU, com Receita Líquida, Peso Líquido (kg) e Qtde Faturado (caixas). Cada arquivo tem um rodapé com a linha `Total` e o texto dos filtros da extração | **diária** (ver doc 14) |
| 2 | `../bases compartilhadas/Produtos.xlsx` (D-85; até 02/10/2026 em `bases/Bases para tabelas dimensões/`) | `Produtos` | cadastro de SKU: código, descrição, **categoria**, **marca** | estática |
| 3 | `bases/Bases para tabelas dimensões/Hierarquia_Consolidada.xlsx` | `Planilha1` | estrutura comercial por cliente, **N1 a N4** (head, gerente, sup./exec., vend./RCA) como rótulo `código - papel - nome`, mais projeto e código de bandeira. **Única fonte** da hierarquia (D-56): 13.516 clientes | estática, dono no Comercial |
| 4 | `bases/Canais/Canais.xlsx` | `Export` | **canal e subcanal** por cliente (43.072 clientes; cobre 100% do sell-in) | estática |
| 5 | `../bases compartilhadas/RTM_DePara_Transicao.xlsx` (D-85; até 02/10/2026 em `bases/RTM-Transicao/`) | `De-Para RTM` | 1.762 clientes que passaram a ser atendidos por **27 distribuidores** (166 sem código de distribuidor = exceção) | estática (D-50) |
| 6 | `bases/Bases para tabelas dimensões/Hierarquia_Clientes_Faltando.xlsx` | `Planilha1` | 850 clientes sem vínculo, com a coluna `Hierarquia` SIM (70) / NÃO (780) que decide o saneamento | estática (D-50) |
| — | `config/config.yaml` + `config/geografia.yaml` | — | parâmetros: pastas, colunas obrigatórias, ano fiscal (set→ago), tolerâncias, correções declaradas (`[Vago]` → `[VAGO]`), regras do saneamento (`rtm_herda_bandeira`, janela), cortes de exibição, nomes de saída e destino de publicação | muda por decisão |

**O que NÃO entra:** Sell Out (MTRIX/FEMSA/KAN), Previsão, Estoque, Alavancas
e o arquivo de Metas antigo saíram do escopo (D-53/D-49) e foram excluídos na limpeza de 03/10/2026. Nenhum é lido. As METAS voltaram na D-74 (`Metas_FY'27.xlsx`) e, desde a D-87 (02/10/2026), ficam em `../bases compartilhadas/` — lidas também pelo ROTA.

---

## 2. ETL — o que cada base sofre

### Sell In (`src/extract/sellin.py`)
1. **Localiza** os arquivos nas duas pastas declaradas no config; rejeita
   qualquer um sem as 12 colunas obrigatórias (aborta, nunca ingere pela metade).
2. **Remove o rodapé**: a linha `Total` vira **gabarito de reconciliação** e o
   texto `Filtros aplicados` é guardado para comparar o recorte entre meses
   (hoje há 3 recortes na série: 19 meses, ago/26 e set/26; o aviso está
   aberto com o BI).
3. **Normaliza**: `Ano mês` → `AAAA-MM`; `Cód. cliente`/`Cód. material` → só
   dígitos, **sem zeros à esquerda**; textos com trim/maiúscula; números com
   sinal preservado (devolução é negativa e **fica**); caixas nulas **ficam
   nulas**; linha 100% zerada é descartada e contada (D-36).
4. **Cache**: cada Excel lido vira um Parquet em `data/staging/`; reexecutar
   sem mudança de arquivo pula a leitura (chave = nome+tamanho+mtime+versão).

### Produtos (`src/extract/cadastros.py`)
Código sem zeros, textos normalizados. **Marca vem do cadastro, nunca é
inferida da descrição.**

### Estrutura comercial (`src/extract/cadastros.py`)
Código zero-preenchido (`0001010846`) → sem zeros (`1010846`); sem isso o join
casa com **zero** clientes. Cabeçalhos com quebra de linha são normalizados.
Cada nível N1–N4 vira um rótulo `código - papel - nome`. Correções
**declaradas** no config são aplicadas aqui e saem no log. Cliente com linhas
conflitantes: vence a 1ª, com aviso (desde a D-56 a base vem limpa; o detector
continua).

### Canais (`src/extract/cadastros.py`)
Mesmo tratamento de código; remove o rodapé de filtros; cliente com dois canais
viraria aviso (hoje: zero).

### RTM e Faltando (`src/extract/cadastros.py` → `src/transform/saneamento.py`)
Só códigos e textos normalizados na extração. A regra vive na transformação e
age **só na DIM_CLIENTE**: o cliente RTM herda do distribuidor hierarquia,
projeto, canal e, desde a D-59, a **bandeira** (a de origem fica em
`BANDEIRA_ORIGINAL`); cliente `Hierarquia = NÃO` sem sell-in na janela de 6
meses fechados vira `INATIVO (SANEAMENTO)`; `NÃO` com sell-in fica listado
para decisão (Q5, 158 clientes). Tudo parametrizado em `config → saneamento`.

### Derivadas (`src/transform/`)
- `DIM_CALENDARIO`: gerada da amplitude dos meses do sell-in; os **dois
  calendários** (civil e fiscal set→ago) como colunas da mesma tabela, mais o
  pareamento explícito `ANO_MES_LY` (junção, nunca deslocamento).
- `DIM_CLIENTE`: nome/bandeira/UF **mais recentes** do sell-in + N1–N4/projeto
  da hierarquia + canal/subcanal do Canais.xlsx + as colunas do RTM e do
  saneamento. Quem não está em base nenhuma entra **marcado** (`NÃO
  ATRIBUÍDO` / `SEM CANAL`), nunca descartado.
- `DIM_PRODUTO`: cadastro + os 4 SKUs órfãos adotados do próprio sell-in
  (`FORA_DO_CADASTRO = true`).

---

## 3. Relacionamentos — como as bases se conectam

```
                       DIM_CALENDARIO (25 linhas · PK ANO_MES)
                              │ 1:N
  DIM_PRODUTO ────────── FATO_SELLIN ────────── DIM_CLIENTE
  (400 · PK COD_PRODUTO)  3.127.196 linhas      (16.136 · PK COD_CLIENTE)
        1:N                                          1:N
```

| Ligação | Chave | Cardinalidade | Integridade |
|---|---|---|---|
| Fato → Calendário | `ANO_MES` (`AAAA-MM`) | N:1, 25 meses | 100%, aborta se quebrar |
| Fato → Cliente | `COD_CLIENTE` (dígitos sem zeros) | N:1, 16.136 clientes | 100% (a dimensão adota órfãos) |
| Fato → Produto | `COD_PRODUTO` (idem) | N:1, 400 SKUs | 100% (idem) |
| Cliente → canal/N1–N4/projeto/bandeira/UF | atributos na própria `DIM_CLIENTE` | 1:1 por cliente | coberturas com piso: estrutura 97,65%, canal 100,00% (abaixo de 95% o pipeline aborta) |
| Produto → categoria/marca | atributos na própria `DIM_PRODUTO` | 1:1 por SKU | zero divergência medida entre sell-in e cadastro |

**Grão da fato (declarado e medido):** *uma linha = o faturamento líquido de um
SKU para um cliente em um mês*; zero duplicados em 25 meses. Não há snowflake:
toda dimensão liga direto na fato.

---

## 4. Pipeline — ordem, e o que cada etapa produz

`python run_pipeline.py`: 6 passos, ~2 min a frio / ~20 s com cache, `exit 0`
ou aborta com a causa (nenhum Parquet é atualizado num aborto):

| # | Passo | O que faz | Produz |
|---|---|---|---|
| 1 | **EXTRAIR** | localiza, valida schema, tira rodapé, lê as 6 bases | `data/staging/*.parquet` (cache) |
| 2 | **FATO** | monta a fato, confere o **grão** (zero duplicados) e **reconcilia contra a linha `Total`** de cada arquivo, nas 3 métricas | — |
| 3 | **DIMENSÕES** | calendário, cliente (com canal, estrutura N1–N4, RTM e saneamento), produto | — |
| 4 | **INTEGRIDADE** | FKs 100% + pisos de cobertura (estrutura ≥95%, canal ≥95%). Foi aqui que a edição da hierarquia sem os distribuidores abortou a 75,40% em 03/09 (D-61) | — |
| 5 | **AGREGAR** | os 2 cubos, **sem o eixo UF** desde a D-51 (principal 730.257 linhas: mês × bandeira × categoria × perfil × **cliente** desde a D-72, **todas** as bandeiras desde a D-65, clientes RTM que herdaram a bandeira acumulados numa chave por bandeira; SKU 681.892: mês × SKU × perfil, sem bandeira desde a D-64; perfil = head, gerente, sup./exec., canal, projeto, vendedor, 517 tuplas) e a **reconciliação cubo × fato**, tudo **antes** de qualquer gravação | — |
| 6 | **GRAVAR + RELATAR** | o modelo estrela em Parquet; `cubos.json`/`resumo.json` gravados de forma **atômica** e carimbados com a execução (conferida pelo `run_dashboard.py`); relatório de qualidade | `data/curated/DIM_*.parquet`, `FATO_SELLIN/ANO=*/`, `cubos.json`, `resumo.json`, `data/quality/*` |

**Regra de ouro do passo 6:** linha transacional **nunca** chega ao HTML, só
agregado; e camada agregada que não reconcilia com a fato **não é publicada**.

## 5. Publicação — como o painel final nasce

`python run_dashboard.py` (~10 s para os 73 arquivos):

1. Lê `data/curated/cubos.json` e `resumo.json` (e confere que os dois vêm da
   **mesma execução**; par trocado aborta).
2. Abre o template apontado no config (`dashboard/template_v4.html`): **a
   interface inteira vive aqui**, editada à mão; nenhuma linha de HTML/CSS/JS
   nasce em Python.
3. Faz **duas substituições de texto**: embute o `dashboard/lib/chart.umd.min.js`
   no marcador de biblioteca e injeta os cubos, **compactados** (gzip+base64,
   45,2 MB → 17,3 MB desde a D-72; o navegador descompacta na abertura, sem
   rede), entre os marcadores de dados (cada marcador precisa existir
   exatamente 1 vez).
4. Grava **`dashboard/build/Dashboard_Gerencial.html`** (17,6 MB, um arquivo
   só, **zero requisições de rede**; abre por duplo clique, inclusive em
   `file://` no OneDrive).
5. **Arquivos por nível** (config `dashboard.por_nivel`, D-52): para cada
   head (N1), gerente (N2) e sup./exec. (N3) da base, `filtrar_por_nivel`
   recorta os dois cubos no **nível de dados** e remapeia os índices; desde a
   D-54 as listas de canal, categoria e SKU também encolhem, desde a D-65 a
   de bandeiras (o arquivo leva todas as do escopo; o corte é de exibição, no
   template) e desde a D-72 a de **clientes** (nem o nome de um cliente de
   fora do escopo viaja). O que é de outro escopo
   **não existe** dentro do arquivo. A geração confere por assert que nenhuma
   linha vazou e loga o particionamento (soma do nível + fora da hierarquia =
   base completa, ao centavo). Os baldes `NÃO ATRIBUÍDO` e `INATIVO
   (SANEAMENTO)` não geram arquivo. Nomes: `Dashboard_Gerencial_N1_<head>.html`,
   `_N2_<gerente>`, `_N3_<sup-exec>` (D-58).
6. **Publicação** (config `dashboard.publicacao`, D-52/Q13): cada arquivo por
   nível é copiado **substituindo** para a pasta do próprio colaborador em
   `Documentos\Painéis Comerciais\Gerencial\` (nome da pasta = rótulo do
   colaborador, caracteres inválidos trocados por `-`), e o Full vai para a
   pasta `Dashboard - Full\` (config `publicacao.pasta_full`, D-73; até
   04/09 era a raiz); MD5 conferido em cada cópia. O Douglas compartilha cada pasta com o
   respectivo colaborador uma vez; as gerações seguintes mantêm nome e link.
   A geração **não apaga** o que ela não criou: painel antigo que sobrar numa
   pasta é recolhido por `ferramentas/limpar_paineis_antigos.py` (D-60).

Não há rodapé textual desde a D-47: título e cabeçalho declaram o recorte, e
as ressalvas (caixas bruta, corte de bandeiras, linhas Σ) ficam nas próprias
telas que elas afetam.

> Modelo de distribuição no SharePoint e o que ficou decidido:
> [`15_PLANO_SHAREPOINT.md`](15_PLANO_SHAREPOINT.md).
