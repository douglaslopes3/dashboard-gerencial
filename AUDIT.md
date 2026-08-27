# AUDIT.md — Auditoria completa do pipeline

> Auditoria de 26/08/2026, **somente leitura** — nenhum arquivo do projeto foi
> alterado além da criação deste `AUDIT.md`. Cinco auditores independentes, em
> paralelo, varreram as camadas (ingestão, transformação, armazenamento, modelo
> dimensional, dashboard); cada achado foi conferido em `arquivo:linha` e, onde
> coube, **medido** contra os dados reais (parquets da carga
> `20260826-211432-ea347c`, os 28 xlsx de origem e o HTML publicado).
>
> **Declaração de contexto:** o pipeline auditado foi construído neste mesmo
> ambiente. O viés de autor foi mitigado com auditores de contexto limpo,
> instruídos a só reportar o que confirmassem na linha, e com medição empírica
> — inclusive re-lendo os rodapés dos 28 Excel para refazer a reconciliação do
> zero.

**Placar:** 22 achados de risco de dado errado ou robustez, 10 de performance,
16 de limpeza · **0 dado errado armazenado hoje** (a fato reconcilia com a
fonte em R$ −0,0001 sobre R$ 2,26 bi) · os riscos materiais são **condicionais**
(o que acontece quando a fonte, o OneDrive ou um clique incomum se comportarem
de um jeito ainda não visto) e **um semântico** (SCD, achado A8).

---

## 0. O fluxo ponta a ponta (mapa derivado do código, não das docs)

```
ENTRADA (Excel)                          ETL — run_pipeline.py (6 passos)
─────────────────                        ────────────────────────────────
bases/Sell In/*.xlsx  (28 arq, aba      1/6 EXTRAIR  src/extract/sellin.py:141 ler()
  Export, rodapé Total+filtros) ─────►      · valida colunas obrigatórias (config)
data/raw/sell_in/*.xlsx  (2ª pasta)         · remove rodapé; guarda gabarito+filtro
Produtos.xlsx (aba Produtos) ────────►      · normaliza: digitos() sem zeros,
DePara_Estrutura_Comercial.xlsx             ano_mes(), texto(), sinais preservados
  (aba Planilha1, cód zero-preench.) ►      · cache 1 Excel→1 Parquet (staging)
Canais.xlsx (aba Export, rodapé) ────►      · correções declaradas do config
config/config.yaml + geografia.yaml         (cadastros.py:52/105/153)

                                         2/6 FATO  src/transform/fato.py:34
                                            grão declarado fato.py:31 =
                                            ANO_MES × COD_CLIENTE × COD_PRODUTO
                                            conferir_grao():49 (0 dup ou aborta)
                                            reconciliar_origem():84 — soma ×
                                            linha Total de CADA arquivo, 3 métricas

                                         3/6 DIMENSÕES
                                            calendario.py:50 (civil+fiscal na
                                              mesma tabela; ANO_MES_LY por junção)
                                            dimensoes.py:21 dim_cliente (sell-in
                                              mais recente + estrutura + canais)
                                            dimensoes.py:85 dim_produto

                                         4/6 INTEGRIDADE  fato.py:69/121
                                            FKs 100% · cobertura estrutura ≥95%
                                            · cobertura canal ≥95% (senão aborta)

SAÍDA (Parquet)                          5/6 GRAVAR  src/load/parquet.py:14/48
────────────────                            DIM_CALENDARIO (24×21) · DIM_CLIENTE
data/curated/DIM_*.parquet                  (16.131×12) · DIM_PRODUTO (494×6) ·
data/curated/FATO_SELLIN/ANO=*/             FATO_SELLIN (3.085.119×10, partição
  (3 partições, snappy, 23,2 MB)            por ANO, reprocessamento completo)

                                         6/6 AGREGAR  src/load/cubos.py:47
data/curated/cubos.json (14,0 MB)           CUBO_PRINCIPAL 90.644 linhas: mês ×
data/curated/resumo.json                      bandeira(300+balde) × categoria ×
data/quality/relatorio_qualidade.md           PERFIL(head,ger,canal,proj) × UF
  + 5 CSVs de exceção                       CUBO_SKU 368.699: mês × SKU ×
                                              (head,canal) × UF
                                            inteiros escalados (¢, g, ¢cx)
                                            reconciliar():145 cubo × fato ou aborta

DASHBOARD                                run_dashboard.py
─────────                                   injeta cubos.json + Chart.js no
dashboard/template.html (interface          template por substituição de texto
  editada à mão; motor JS re-agrega         (marcadores conferidos: exatamente 1)
  os cubos no cliente a cada render) ──► dashboard/build/
                                            Dashboard_Gerencial_Canais.html
                                            14,99 MB (JSON 14,72 + Chart.js 0,20
                                            + template 0,07) · 1 arquivo · zero
                                            rede · 5 páginas · export · drills
```

**Grão da única fato** (declarado em `src/transform/fato.py:31` e
`docs/06_MODELO_ESTRELA.md`; **medido: respeitado, 0 duplicados**): *uma linha
= faturamento líquido de um SKU para um cliente em um mês de competência.*

**Como o dashboard lê:** não lê Parquet — consome os dois cubos pré-agregados
embutidos no HTML (arrays posicionais de inteiros escalados) e **re-agrega os
cubos em JavaScript a cada interação**. Linha transacional nunca chega ao
navegador.

---

# GRUPO A — RISCO DE DADO ERRADO
*Ordenado por impacto ÷ esforço. Nenhum destes está corrompendo dado HOJE
(medição no §"o que está bem") — são as portas pelas quais o dado errado
entraria ou já aparece errado na tela em cenários específicos.*

### A1 · Ranking sem guarda de LY: FY sem ano anterior vira "ganho" gigante
`dashboard/template.html:856-868, 878-881` · esforço **P**
- **Problema:** `ranking()`/`tabelaRanking()` não têm a guarda `temLy` que as
  outras tabelas têm. Clicando **FY2025** (os 12 primeiros meses têm LY nulo —
  medido no calendário), todo item vira `l=0, d=a`.
- **Impacto:** "Maiores ganhos" lista o top-10 inteiro como ganho verde de
  valor cheio; o rodapé mostra LY "R$ 0,00" e **Δ "+R$ 2,26 bi" em verde** — o
  painel afirma crescimento onde não existe base. É um clique comum.
- **Correção:** com `p.ly.length===0`, rodapé LY/Δ = `n/d` e rankings exibem
  "sem base", como as demais tabelas já fazem.

### A2 · `varPct(null, ly)` devolve −100% em vez de n/d
`dashboard/template.html:388-391` (usada em :670, :959-967, :981) · esforço **P**
- **Problema:** o guard cobre só o denominador; `atual === null` passa e
  `(null − ly)/|ly| = −1`. O espelho Python (`src/utils/texto.py:74`) devolve
  `None` no mesmo caso — as "mesmas fórmulas" divergem num edge case.
- **Impacto:** na aba R$/kg, linha com peso atual 0 e LY válido mostra
  **"▼ −100,0%"** em vez de n/d — e **exporta `-100`** no CSV/XLSX.
- **Correção:** adicionar `atual===null || !isFinite(atual)` ao guard.

### A3 · Cópia de conflito do OneDrive dobra um mês com todas as checagens verdes
`src/extract/sellin.py:60` (+ `fato.py:96-112`, `sellin.py:212-218`) · esforço **M**
- **Problema:** `arquivos()` ingere tudo que casar `*.xlsx` nas duas pastas.
  Uma cópia do mesmo arquivo com outro nome (`...-DESKTOP-XYZ.xlsx`,
  `... - Copia.xlsx` — padrão real do OneDrive) entra como arquivo novo. Cada
  cópia carrega o **próprio gabarito**, então a reconciliação por arquivo FECHA
  e o detector de mês partido classifica como "filtros complementares".
- **Impacto:** a receita do mês **dobra no painel sem nenhum aviso** — é o
  único cenário encontrado que fura as três camadas de reconciliação.
- **Correção:** mês partido cujas assinaturas de filtro são **idênticas**
  (complementares têm assinaturas diferentes por construção) → abortar; ou
  deduplicar por hash de conteúdo.

### A4 · Exportação entrega tabela de outro recorte quando a quebra não existe
`dashboard/template.html:777-781` · esforço **P**
- **Problema:** o desvio de `quebra()` ("esta quebra não existe na camada de
  SKU") escreve a mensagem direto no `innerHTML`, sem `delete RAW[idTab]` — só
  `vazio()` limpa o registro de exportação.
- **Impacto:** Detalhamento por Gerente + filtro de SKU: a tela diz que a
  quebra não existe, mas ⬇ CSV/XLSX **exporta a tabela anterior, de outro
  recorte**, sem aviso.
- **Correção:** usar `vazio(idTab, msg)` no desvio (o `renderPreco:946` já faz
  certo; só `quebra()` divergiu).

### A5 · Gabarito com célula vazia faz a reconciliação "passar de mão vazia"
`src/extract/sellin.py:101-105` (+ `fato.py:110`) · esforço **P**
- **Problema:** a linha `Total` é lida com `float()` cru e só Caixas tem
  proteção de `notna`. Receita/Peso vazios viram `NaN` no gabarito, e
  `abs(nan) > tol` é `False` — a métrica passa "reconciliada" sem conferência.
  Vindo como texto pt-BR, `float("1.234,56")` estoura traceback cru.
- **Impacto:** a checagem mais importante do pipeline rodando de mão vazia — o
  exato modo de falha documentado no cabeçalho de `cache.py` como o mais
  perigoso ("checagem que não roda é pior do que checagem que não existe").
- **Correção:** `numero()` + `pd.notna` nas três métricas do gabarito; NaN vira
  "gabarito ausente" com aviso.

### A6 · Aborto no meio da gravação deixa `data/curated` inconsistente — e a mensagem mente
`run_pipeline.py:85-99` + `src/load/parquet.py:35-45` + `src/utils/log.py:73` · esforço **M**
- **Problema:** (a) o passo 5 grava dims+fato ANTES de o passo 6 validar os
  cubos — um aborto no 6 deixa parquet novo com `cubos.json`/`resumo.json`
  velhos; (b) `_limpar_parquets` pode abortar no meio (PermissionError do
  OneDrive na 4ª tentativa) com a fato **parcialmente apagada** e as dims já
  sobrescritas; a mensagem fixa de `abortar` ("nenhum Parquet foi atualizado")
  é **falsa** nesses cenários.
- **Impacto:** `run_dashboard.py` publica painel da execução anterior com cara
  de válido; leitor da fato lê dado que os cubos não refletem.
- **Correção:** gravar `cubos.json`/`resumo.json` via `.tmp` + `os.replace`;
  só gravar parquet após TODAS as validações; carimbar `EXECUCAO_ID` no
  cubos.json e conferir no `run_dashboard`; mensagem de aborto parametrizável.

### A7 · Trimestre/semestre "fiscais" existem no payload mas o painel agrupa pelo calendário
`dashboard/template.html:674-678` (vs `:314`; geradas em `src/load/cubos.py:126-133`) · esforço **M**
- **Problema:** `grupoPeriodo()` usa sempre `C_TRI`/`C_SEM` (calendário), mesmo
  em YTD Fiscal; `C_TFIS`/`C_SFIS` viajam no payload e **nunca são lidos**.
- **Impacto:** no FY fiscal, "Trimestre" produz grupos rasgados (set/25 sozinho
  em "2025-T3") e o "T" exibido não é o trimestre fiscal que o resto da aba usa.
- **Correção:** em `F.base==="fis"`, agrupar por `FY-T{C_TFIS}`; ou tirar as
  colunas do payload se a decisão for manter calendário.

### A8 · SCD: toda a história é classificada pela estrutura comercial DE HOJE — e a decisão não está registrada
`src/transform/dimensoes.py:45` + `src/extract/cadastros.py:129-150` · esforço **M**
- **Problema (medido):** o de-para (gravado 24/08/2026, colunas "Novo Head/
  Gerente/Supervisor" — a estrutura pós-reorganização) é aplicado sem data de
  vigência aos 24 meses. **R$ 1.133.602.149,05 (50,1% da receita)** são de um
  ano fiscal ANTERIOR a essa estrutura; a atribuição da época é irrecuperável
  nos dados entregues. O *mecanismo* está documentado (docs/06 §2.3), a
  *consequência* (todo ranking histórico de head/gerente reescrito pela
  estrutura atual) **não consta de nenhuma decisão D-xx**.
- **Impacto:** comparações "head vs LY" comparam carteiras diferentes como se
  fossem a mesma; é correto SE a leitura desejada for "a carteira atual, olhada
  para trás" — mas isso nunca foi decidido formalmente.
- **Correção:** registrar a decisão (D-32: análise pela estrutura vigente) e,
  se a leitura histórica importar, pedir ao Comercial de-para com vigência.
- **Correlato (P):** nome/bandeira/UF do cliente também são SCD-1. Hoje o churn
  é **zero medido** (os 28 arquivos foram re-extraídos no mesmo dia — a fonte
  já reescreveu o histórico); com a cadência diária ele passará a existir e
  **nada o mede**. Adicionar contador de clientes com >1 bandeira/UF/nome na
  série ao `qualidade.py` (hoje daria 0; o dia em que não der, aparece).

### A9 · `ano_mes()` aceita mês inválido e fatia formato novo em silêncio
`src/utils/texto.py:66-71` · esforço **P**
- **Problema (medido):** `202512` → `"2025-02"` (mês errado!), `"2025/13"` →
  aceito, `"07/2025"` → NA (linha some no dropna). A reconciliação soma por
  ARQUIVO, não por mês — mês errado passa verde.
- **Impacto:** se a extração mudar para `AAAAMM`, dezembro vira fevereiro no
  painel, sem abortar.
- **Correção:** regex full-match + validar 1≤mês≤12; formato não reconhecido
  aborta com exemplo.

### A10 · `numero()` tem bug latente de 100× para texto com decimal em ponto
`src/utils/texto.py:57-58` · esforço **P**
- **Problema (medido):** `"1234.56"` → `123456.0` e `"1,234.56"` → `1.23456` —
  o `.replace(".", "")` roda antes de checar se há vírgula. Hoje as colunas
  chegam como float64 e caem no ramo numérico — o bug está **latente**.
- **Impacto:** extração futura em locale en-US multiplicaria valores por 100 em
  silêncio (o gabarito, lido com `float()` cru — A5 — não pegaria se
  misparseado igual).
- **Correção:** só remover `.` quando houver `,`; senão decidir pelo último
  separador.

### A11 · Cache pode servir dado velho após restore do OneDrive
`src/extract/cache.py:39` · esforço **P**
- **Problema:** chave = `nome|tamanho|int(mtime)` — sem caminho e com mtime
  truncado. Restore de versão pelo histórico do OneDrive (ou `robocopy
  /COPY:DAT`) que preserve tamanho+carimbo serve o Parquet **antigo** como se
  fosse o dado novo, com log "(cache)".
- **Correção:** incluir o caminho relativo na chave + hash rápido de
  primeiros/últimos KB.

### A12 · Coluna opcional que sumir da extração morre em silêncio absoluto
`src/extract/sellin.py:117-119` (log só na presença, :165-166) · esforço **P**
- **Impacto:** o BI renomeia `Subcanal` → o eixo some do painel de um mês para
  o outro, sem uma linha de log.
- **Correção:** logar por arquivo as opcionais declaradas e ausentes; avisar
  quando uma coluna que existia deixar de existir.

### A13 · `fillna(0)` no cubo apaga a distinção nulo × zero de CAIXAS que a fato preserva
`src/load/cubos.py:43` (contra a promessa de `fato.py:12-16` e docs/06) · esforço **M**
- **Medido:** 9.519 de 368.699 células do CUBO_SKU (2,6%) são grupos 100% nulos
  publicados como `C=0` — devoluções com R$ −20,6 mi de receita associada.
- **Impacto:** a tela mostra "0 caixas" onde a verdade é "não informado"; o
  total ainda reconcilia (por isso passou 24 testes).
- **Correção:** sentinela para grupo todo-nulo, ou documentar a perda assumida
  em docs/06.

### A14 · O filtro de extração do Canais.xlsx é capturado e nunca conferido
`src/extract/cadastros.py:80-85` (consumo só de `conflitos`, :118-123) · esforço **M**
- **Problema:** o rodapé do arquivo declara um recorte
  ("Nome Gerente é Izabela - 2650...") incoerente com a cobertura total medida
  — e nada compara essa assinatura entre execuções, ao contrário do sell-in.
- **Impacto:** o BI reextrai o de-para com outro recorte → o universo de canais
  muda em silêncio (o piso de 95% só pega queda grande).
- **Correção:** guardar a assinatura no relatório de qualidade e avisar quando
  mudar.

### A15 · Merges do cubo sem validação de cardinalidade
`src/load/cubos.py:49-54` (+ `dimensoes.py:46,67` protegidos só por `assert`) · esforço **P**
- **Impacto:** duplicata futura em DIM_CLIENTE multiplicaria o cubo; a
  reconciliação pegaria, mas com diagnóstico errado ("cubo não reconcilia").
  E `assert` some com `python -O`.
- **Correção:** `validate="m:1"` nos quatro merges.

---

# GRUPO B — MELHORIA DE PERFORMANCE
*Nenhum item abaixo muda um número. Ordenado por ganho ÷ esforço, com o ganho
medido.*

### B1 · O motor do painel varre os cubos ~103 vezes por clique
`dashboard/template.html:601-617` (motor todo) · esforço **M**
- **Medido:** um `render()` = 103 passadas completas no CUBO (90.644 linhas) +
  2 no CUBO_SKU ≈ **10,1 milhões de visitas de linha por clique** (38,7 mi com
  filtro de SKU ativo, quando as 103 migram para o cubo de 368.699). Síncrono,
  para as 5 abas inclusive as ocultas; Evolução e Período calculam os mesmos 24
  totais duas vezes; uma passada de mês único visita 90.644 linhas para usar
  3.777 (96% desperdício).
- **Impacto:** ~1–2 s de UI congelada por clique em máquina fraca; **4–8 s no
  modo SKU**.
- **Correção composta:** (a) índice por mês construído 1× no `iniciar()`
  (24× menos linhas nas passadas de mês único); (b) memo de `somar()` por
  chave de filtros (−40% das passadas); (c) renderizar só a aba ativa.
  Juntas: ~10 M → ~1 M visitas/clique, sem mudar nenhum número.

### B2 · `data/` e `dashboard/build/` dentro do OneDrive: ~52 MB de churn por execução
pasta `data/` + `dashboard/build/` (cicatriz no código: `parquet.py:24-43`) · esforço **M**
- **Medido:** cada rodada reescreve fato 23,2 MB + cubos.json 14,0 MB + HTML
  15,0 MB. O retry de `PermissionError WinError 5` já existe porque o
  sincronizador **já** segurou arquivo uma vez. Com cadência diária, é atrito
  diário.
- **Correção:** excluir `data/` e `dashboard/build/` da sincronização (OneDrive
  permite por pasta) ou movê-los para pasta local; publicar só o HTML final.

### B3 · `EXECUCAO_ID`/`ARQUIVO_ORIGEM` como str por linha: 178 MB de RAM à toa
`src/transform/fato.py:44-45` · esforço **P**
- **Medido:** `astype("category")` nas duas colunas: fato de 418 → **247 MB**
  (−41%). No disco nada muda (parquet já dicionariza).

### B4 · Pico de memória ~2,4 GB por referências mortas
`run_pipeline.py:51-94` · esforço **P**
- **Medido:** `bruto` (692 MB) e `f_part` (~460 MB) seguem referenciados após o
  último uso. `del` nos dois corta ~1,1 GB do pico. **Veredito do auditor:
  processar em partes NÃO vale** — 2,5 GB cabe em máquina corporativa e
  chunking quebraria as validações globais (grão, reconciliação).

### B5 · Sort de 3,08 M linhas repetido 3× nas dimensões
`src/transform/dimensoes.py:32,39,92` · esforço **P**
- **Medido:** ~0,65 s/sort + ~1 s/groupby; o passo custa 3,7 s dos 16,5 s.
  Ordenar uma vez e agregar num único `.agg` poupa ~1,5–2 s (~10% do pipeline).

### B6 · Cubos montados linha a linha em list comprehension
`src/load/cubos.py:94-99,116-119` · esforço **P**
- **Medido:** 2,4 s dos 16,5 s (15%). Vetorizar cortaria para <0,5 s — mas o
  formato de saída (listas para JSON) força materializar ~102 MB de listas de
  qualquer jeito. Vale registrar; não vale reescrever com urgência.

### B7 · zstd + row groups consolidados: −14,5% e −8,4% no disco
`src/load/parquet.py:57` e `:16` · esforço **P**
- **Medido em regravação de teste:** fato 23,23 → 19,86 MB (zstd) e ANO=2025
  12,57 → 11,51 MB (row groups: hoje são 110 para 3,08 M linhas). Leitura
  continua <0,25 s. Ganho absoluto pequeno; casa com o B2.

### B8 · Cache thrash com o mesmo nome nas duas pastas de entrada
`src/extract/cache.py:64-68` (chave em :39) · esforço **P**
- **Problema:** dois arquivos de mesmo stem (cenário permitido pelo design de
  duas pastas) apagam o cache um do outro a cada execução — releitura eterna
  dos ~6 MB, só visível pelo log "(lido)". Fonte removida deixa par órfão no
  staging (hoje: 31/31 corretos, zero órfãos — o risco é futuro).
- **Correção:** namespacear a chave pela pasta de origem; varrer o staging
  contra a lista de fontes ao fim do `ler()`.

### B9 · `cubo_sku` é 78% do payload — decisão de produto disponível
`data/curated/cubos.json` / `src/load/cubos.py:103-121` · esforço **G**
- **Medido:** 11,46 MB de 14,72. Sem o eixo UF: 65.926 linhas / 1,98 MB
  (**−9,5 MB no arquivo**) — perde SKU×UF (filtro de UF na aba SKU, matriz UF
  em modo SKU). Colunar economiza só 6% (não vale); corte por receita mínima
  fere a política de reconciliação. **Não é correção: é trade-off para o dono
  do produto** (registrado; sem recomendação de código).

### B10 · Particionamento por ANO é neutro
`data/curated/FATO_SELLIN/ANO=*` · esforço **P**
- **Medido:** nenhum leitor filtra por partição (a fato inteira é lida em
  0,21 s); benefício zero, custo ~zero. Registrado como decisão a simplificar
  quando alguém mexer no B7 — não como problema.

---

# GRUPO C — LIMPEZA DE CÓDIGO
*Ordenado por (risco de virar dado errado no futuro) ÷ esforço.*

### C1 · `</script>` escapado nas libs mas não no JSON dos dados
`run_dashboard.py:147-150` (vs `:59`) · esforço **P** — hoje **0 ocorrências**
medidas nos 494 SKUs e 301 bandeiras, mas descrição de SKU vem de Excel de
terceiros; uma futura com `</script>` quebraria o painel inteiro no parse.
Correção: `dados.replace("</script>", "<\\/script>")` após o `json.dumps`.

### C2 · Rótulos de negócio duplicados entre módulos
`src/transform/dimensoes.py:78,80,81,101` × `src/qualidade.py:153,209` · **P** —
`"SEM CANAL"`/`"SEM BANDEIRA"`/`"SEM UF"`/`"NAO INFORMADO"` hardcoded em dois
lugares (o irmão `"NÃO ATRIBUÍDO"` está certo, no config). Trocar num módulo só
faz o relatório contar errado em silêncio. Levar os três para o config.

### C3 · `read_excel` dos cadastros sem o try→`abortar` do sell-in
`src/extract/cadastros.py:36,76,130` · **P** — aba errada = traceback cru em
vez de "arquivo REJEITADO". Agrava: a aba da estrutura chama `"Planilha1"`,
nome default que muda na primeira regravação do arquivo.

### C4 · `colunas_opcionais` do config é documentação morta
`config/config.yaml:52-58` × `src/extract/sellin.py:33-47` · **P** — a chave não
é lida por código nenhum (grep: zero usos) e `Comissão Faturada Líquida`,
presente nos arquivos, não tem destino — nunca é ingerida. Ou ingerir, ou
anotar; e validar que toda opcional declarada tem destino.

### C5 · Checagens de grão/órfãos re-implementadas no relatório
`src/qualidade.py:117-119,127-131` (vs `fato.py:54,75-77`) · **P** — se a
definição do grão mudar num lugar, o relatório mede outra coisa. O `fato.py`
deveria devolver os números; o relatório, só relatar.

### C6 · Reconhecimento de head por prefixo, no código
`src/qualidade.py:149-150` · **P** — `"Izabela - 2650"` casa por prefixo com o
gabarito "Izabela"; um head novo "Izabelania" seria reconhecido sem constar da
lista. Comparar o trecho antes de `" - "` por igualdade; regra no config.

### C7 · `dropna` do sell-in descarta sem contar
`src/extract/sellin.py:122` · **P** — hoje 0 linhas descartadas (medido);
célula mesclada em `Ano mês` viraria descarte mudo. Contar e avisar com a
receita descartada (a estrutura já faz assim, `cadastros.py:146-149`).

### C8 · Detecção do rodapé de filtros é frouxa
`src/extract/sellin.py:108-111` · **P** — se o rótulo "Total" mudar (ex.:
"Total geral"), a linha vira "filtro" e dispara falso aviso de recorte
divergente em todo mês novo. Restringir a linhas que comecem com "Filtros
aplicados" (padrão real medido).

### C9 · `razao()` do JS não espelha `div()` do Python
`dashboard/template.html:392` (vs `texto.py:90-98`) · **P** — `isFinite(null)`
é `true` em JS; `razao(x, null)` devolve lixo em vez de null. Hoje nenhum
call-site passa null (conferido um a um); a paridade prometida não existe.

### C10 · `pct()`/`div()` do Python não são chamados por ninguém
`src/utils/texto.py:74-98` · **P** — espelhos documentais das fórmulas do JS, e
o A2 mostra que o espelho já descolou. Ou virar teste de paridade com
casos-tabela, ou docstring dizendo que são referência.

### C11 · Comentário promete "soma exata"; a deriva real é sub-real
`src/load/cubos.py:12-15` · **P** — medido: cubo × fato difere R$ 0,11 e
R$ 0,36 (arredondamento de meio centavo por grupo; 1,6e-10 relativo). Só o
comentário está mais forte que o fato — enfraquecer o comentário.

### C12 · Código `"0"` no DePara vira NA e some sob aviso genérico
`src/extract/cadastros.py:146-150` + `texto.py: digitos()` · **P** — medido: 9
linhas com `Cód. cliente = "0"` (executivos KAR/Farma/Ecommerce) e 4 duplicadas
idênticas descartadas sob "sem Cod. cliente". Impacto na fato: zero (código 0
não existe no sell-in) — mas alguém preencheu e ninguém verá. Logar os códigos
literais descartados.

### C13 · Dtypes pandas mistos (`str` × `string`) na mesma tabela
`src/transform/fato.py:44` e `calendario.py` · **P** — no Parquet ambos viram
`large_string` (sem dado errado), mas código que dependa de semântica de NA
diverge por coluna. `astype("string")` uniforme.

### C14 · Arquivos manuais dentro da pasta gerida pelo pipeline
`data/quality/incluir_no_DePara_estrutura.xlsx`, `clientes_canal_key_account.csv` · **P**
— o pipeline sobrescreve só os 6 arquivos dele; esses dois (gerados a pedido,
para Comercial/BI) ficam parecendo saída de execução. Mover para `docs/pedidos/`
ou equivalente.

### C15 · Asserts como única guarda de cardinalidade
`src/transform/dimensoes.py:46,67` · **P** — some com `python -O` (mesma
correção do A15: `validate="m:1"`).

### C16 · Mensagem de aborto fixa e às vezes falsa
`src/utils/log.py:73` · **P** — "nenhum Parquet foi atualizado" não vale nos
cenários do A6. Parametrizar.

---

# O QUE ESTÁ BEM — verificado com medição

**A integridade numérica de ponta a ponta passou em tudo:**

| Verificação (refeita do zero pelos auditores) | Resultado |
|---|---|
| Grão da fato (3.085.119 linhas) | **0 duplicados** na chave declarada |
| Fatos órfãos nas 3 FKs | **0** |
| Chaves duplicadas/nulas nas 3 dimensões | **0** |
| Colisão da chave natural (`digitos()` sobre 3 fontes) | **0** — 16.131→16.131, 43.073→43.073 |
| Reconciliação fato × rodapés dos 28 Excel (relidos na auditoria) | **R$ −0,0001** / 0,0000 kg / 0,0000 cx |
| Reconciliação cubos × fato | máx. **R$ 0,36 em R$ 2,26 bi** (1,6e-10) |
| `ANO_MES_LY` (24 meses conferidos) | 0 erros; bordas nulas corretas |
| Dictionary encoding no Parquet | já ativo em todas as colunas string (ganho disponível: **zero**) |
| float64 para dinheiro | não é problema real: 6,7% das linhas têm fração além do centavo **vinda da fonte**; deriva de soma = R$ 1,70 em 2,26 bi, 1.300× dentro da tolerância |
| Cache staging | 31/31 hashes batem, 0 órfãos, 0 versões duplicadas |
| Schema entre execuções | único schema nos 28 caches; `fato.py:36-42` re-tipa antes do curated |
| `except` engolindo erro | nenhum relevante: os 9 try/except ou abortam com contexto ou são benignos documentados |
| Injeção no HTML | 0 ocorrências de `</script>`/marcadores nos dados; marcadores contados (=1); índices `D.perfil/D.sku/D.hc` seguros por construção |
| Sinais e acessibilidade | seta+sinal+cor em toda variação; n/d com tooltip; LY tracejado; sem-base interrompido, nunca zero |
| Honestidade dos drills | notas listam exatamente o que cada `passa()` aplica/ignora (conferido linha a linha) |

**Defesas de arquitetura que os auditores destacaram:** leitura por nome com
rejeição explícita e diagnóstico de onde procurar; gabarito da própria fonte
como trava; três camadas de reconciliação com aborto; piso de cobertura contra
o join zero-preenchido; LY por junção; `VERSAO_CACHE` com o incidente
documentado; linhagem por linha a custo ~zero; rótulo de ausência no config.

---

## Método

5 auditores independentes (ingestão, transformação, armazenamento, modelo
dimensional, dashboard), em paralelo, com acesso somente-leitura; scripts de
medição em diretório temporário; instrução explícita de só reportar o que
confirmassem em `arquivo:linha` e de listar também os **não-achados** (hipóteses
testadas e descartadas — dictionary encoding, float-para-dinheiro, int32,
leitura repetida de arquivo, resíduo de partição órfã, exceções engolidas).
Nenhum arquivo do projeto foi criado, alterado ou executado, exceto este
`AUDIT.md`.
