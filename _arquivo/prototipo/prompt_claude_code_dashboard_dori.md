# PROMPT PARA CLAUDE CODE — Dashboard Gerencial de Canais (Sell In)

> **Antes de colar no Claude Code, preencha os 3 campos do bloco "PARÂMETROS".**
> Sugestão: abra o Claude Code já dentro da pasta do novo projeto e comece em *plan mode*.

---

## 0. PARÂMETROS (preencher)

- `NOVO_PROJETO` = `<"C:\Users\dldsouza\OneDrive - Dori Alimentos S.A\Documentos\Dashboard - Gerencial">`
- `HTML_REFERENCIA` = `<"C:\Users\dldsouza\OneDrive - Dori Alimentos S.A\Documentos\Dashboard - Gerencial\Dashboard_Gerencial_Dori.html">`
- `PROJETO_ANTERIOR` = `C:\Users\dldsouza\OneDrive - Dori Alimentos S.A\Documentos\Dashboards - Heads - Canais`
- `BASES_SELL_IN` = `<"C:\Users\dldsouza\OneDrive - Dori Alimentos S.A\Documentos\Dashboard - Gerencial\bases\Sell In">`

---

## 1. PAPEL E MISSÃO

Atue como Arquiteto de Dados Sênior + Analytics Engineer + Desenvolvedor Python, com experiência em modelagem dimensional e dashboards corporativos.

Construa, em `NOVO_PROJETO`, uma solução analítica **independente** para o Dashboard Gerencial de Canais da Dori:

```
Bases brutas → ETL Python → Modelo estrela → Parquet → Camada analítica → Dashboard
```

Operação final esperada, **sem qualquer IA envolvida**:

1. Usuário coloca um novo arquivo de Sell In em `data/raw/sell_in/`.
2. Usuário roda `python run_pipeline.py`.
3. Pipeline valida, processa, atualiza os Parquets e emite relatório de qualidade.
4. Usuário roda `python run_dashboard.py` e vê os dados atualizados.
5. Nenhuma edição manual de código em nenhuma etapa.

A IA é usada **apenas durante o desenvolvimento**. O produto entregue deve rodar sem Claude, sem ChatGPT e sem APIs de IA.

---

## 2. REGRAS INVIOLÁVEIS

### 2.1 Isolamento do projeto anterior

- `PROJETO_ANTERIOR` é **estritamente somente leitura**. Nunca escrever, mover, renomear, excluir ou executar scripts dele.
- Nenhum import, config, Parquet ou caminho absoluto do projeto anterior pode existir no novo projeto em produção.
- Componentes reaproveitados devem ser **copiados para o novo projeto, adaptados, documentados e testados** ali.
- O novo projeto deve continuar funcionando se o projeto anterior for apagado.
- Todas as escritas ficam dentro de `NOVO_PROJETO`. Se precisar escrever fora, pare e pergunte.

### 2.2 Fonte única da verdade

Toda informação exibida vem das bases. É proibido:

- inventar valores, fatores de conversão, classificações ou métricas;
- preencher ausências com dados fictícios ou sintéticos em produção;
- manter valores de negócio embutidos no código;
- corrigir grafias, mapeamentos ou divergências silenciosamente;
- esconder inconsistências para o dashboard "fechar".

Quando faltar informação: registre a ausência, identifique o indicador/visual impactado, indique a coluna ou tabela necessária, **não invente**, e continue construindo o que for possível.

### 2.3 Zero hardcode de negócio

Nada de listas fixas no código para canais, categorias, Heads, UFs, bandeiras, clientes, SKUs, períodos ou anos. Tudo vem das dimensões/bases dinamicamente.

Podem ir para `config/` (YAML ou similar): mês inicial do ano fiscal, pastas, formatos aceitos, nomes esperados de colunas de origem, tolerâncias de validação, formatos de saída, comportamento de logs.

Sem credenciais, tokens, senhas ou caminhos pessoais no código. Caminhos relativos ao projeto sempre que possível.

### 2.4 Escopo

**Incluir:** Valor R$, Volume (t), Caixas, Preço Médio, Ticket Médio (somente se houver definição validada na fonte); análises por período, canal, categoria, Head, UF, bandeira e SKU; comparação com ano anterior; YTD fiscal e calendário; rankings de ganhos e quedas; participação percentual.

**Não incluir:** Sell Out, Metas, Previsão de Vendas, Planejamento, Verbas, Forecast, S&OP, múltiplas fatos sem necessidade, integrações não solicitadas, funcionalidades do projeto anterior fora deste MVP.

Use o **menor nível de complexidade** que atenda corretamente aos requisitos. Isto é um MVP enxuto, não uma plataforma analítica.

---

## 3. COMO TRABALHAR

- Trabalhe por fases, na ordem. **Não comece pelo front-end.**
- Antes de codar cada fase, apresente um plano curto e mantenha uma lista de tarefas rastreável.
- **Não pare a cada passo pedindo confirmação.** Sem bloqueio crítico: registre a decisão em `docs/12_REGISTRO_DE_DECISOES.md` e siga.
- Com bloqueio crítico de dados: documente em `docs/04_GAPS_E_RISCOS.md`, construa tudo que não depende dele e sinalize no relatório final.
- Faça commit (ou snapshot) ao final de cada fase, com mensagem descritiva.
- Toda premissa não confirmada vira pendência escrita, nunca uma suposição silenciosa no código.

---

## 4. FASES

### FASE 0 — Proteção e isolamento

1. Confirmar que o diretório de trabalho é `NOVO_PROJETO`.
2. Marcar `PROJETO_ANTERIOR` como somente leitura no seu modo de operação.
3. Inventariar os arquivos já existentes no novo projeto.
4. Não sobrescrever nada sem backup e justificativa registrada.
5. Inicializar git, `.gitignore` (excluir `data/`, `logs/`, credenciais).

### FASE 1 — Descoberta

1. Engenharia reversa **funcional** do `HTML_REFERENCIA`: navegação, páginas, filtros, cards, KPIs, gráficos, tabelas, hierarquias, comparações, fluxo de uso, identidade visual, densidade.
   Classifique cada elemento como: *requisito confirmado* / *referência visual* / *depende de validação de dados* / *fora de escopo* / *deve ser melhorado*.
   **Não copie o código, a arquitetura, arrays fixos, cálculos estáticos ou dados demonstrativos do HTML.** Um cálculo estar no protótipo não significa que esteja certo.
2. Inventariar as bases disponíveis: formatos, colunas, tipos, volume, período coberto, grão, chaves, métricas, dimensões.
3. Perfilar qualidade: nulos, duplicidades, grafias divergentes, valores fora do padrão.
4. Analisar o ETL do projeto anterior como **referência técnica**: ingestão de Sell In, leitura de Excel/CSV/Parquet, padronização de colunas, tipos, datas, chaves, produto, cliente, canal, categoria, Head, UF, bandeira, dimensão calendário, regra de ano fiscal, cálculos de receita/peso/caixas, deduplicação, validações, logging, erros, config, geração e particionamento de Parquet, testes, orquestração.
   Para cada componente, classifique em: **(1)** reutilizar sem mudança relevante, **(2)** reutilizar com adaptação, **(3)** reescrever simplificado, **(4)** não utilizar, **(5)** exige validação de negócio.
   Registre: arquivo de origem, função/bloco, finalidade, dependências, regra atendida, motivo, adaptação necessária, risco.
   Não reaproveite código morto, duplicado, obsoleto ou ligado a Sell Out/Metas/Previsão/Planejamento.

**Entregas:** `docs/01_INVENTARIO_FONTES.md`, `docs/02_ENGENHARIA_REVERSA_HTML.md`, `docs/03_MATRIZ_REAPROVEITAMENTO_ETL.md`, `docs/04_GAPS_E_RISCOS.md`

### FASE 2 — Definição funcional e modelagem

Definir, com base nas fontes reais: grão da fato, dimensões estritamente necessárias, chaves, relacionamentos, métricas, regras temporais, comportamento dos filtros, comparações, tratamento de divisão por zero, parâmetros de ranking, critério de ganhos e perdas, tratamento de itens sem classificação, procedimento de atualização e arquitetura mínima.

**Grão:** não presumir. Determinar a partir das fontes e documentar explicitamente a frase "Uma linha da `FATO_SELLIN` representa: ...". Validar se o grão comporta período, cliente/bandeira, produto/SKU, canal, Head, UF, receita, peso e caixas. Não agregar prematuramente; não manter granularidade que não agrega valor.

**Modelo estrela — ponto de partida:** `FATO_SELLIN` + dimensões candidatas `DIM_CALENDARIO`, `DIM_PRODUTO`, `DIM_CLIENTE`, `DIM_ESTRUTURA_COMERCIAL`.
A lista de dimensões candidatas do escopo (canal, categoria, Head, UF, bandeira, SKU) **não é uma ordem para criar todas separadamente**. Antes de criar cada uma: verifique fonte, chave, cardinalidade, uso no dashboard e se a separação agrega valor. É permitido consolidar (ex.: categoria como atributo do produto; UF e bandeira como atributos do cliente; canal e Head na estrutura comercial) desde que a fonte sustente e a integridade seja preservada. Evite snowflake e duplicação de atributos. **Justifique a proposta final.**

**Entregas:** `docs/05_DICIONARIO_DADOS.md`, `docs/06_MODELO_ESTRELA.md`, `docs/07_CATALOGO_METRICAS.md`, `docs/08_ESPECIFICACAO_FUNCIONAL_DASHBOARD.md`, `docs/09_ARQUITETURA_SOLUCAO.md`

### FASE 3 — ETL

ETL Python modular, legível, configurável, auditável, **idempotente**, reprocessável, com logs, tratamento de erros, validação de schema, validação de qualidade e testes das regras críticas. Sem dependência do projeto anterior.

O pipeline deve: localizar os arquivos de entrada automaticamente → verificar formato suportado → validar colunas obrigatórias → **impedir ingestão silenciosa de arquivo incompatível** → padronizar nomes e tipos → preservar rastreabilidade da origem → tratar duplicidade conforme regra documentada → gerar dimensões → gerar fato → validar integridade referencial → reconciliar métricas contra a origem → gravar Parquets → registrar logs → gerar relatório de qualidade → finalizar com status claro de sucesso ou erro (exit code).

Comando único: `python run_pipeline.py`.

Não implemente carga incremental sem uma chave de controle segura e definida. Na dúvida, faça **reprocessamento completo**, priorizando correção e simplicidade.

### FASE 4 — Dashboard

Só depois do modelo analítico gerado e validado.

Antes de escolher a tecnologia, verifique o ambiente disponível, dependências já instaladas, modo de distribuição, volume de dados e necessidade de interatividade — e **documente a escolha**. Opções aceitáveis conforme justificativa: Streamlit, Dash, Plotly, DuckDB ou outra alternativa local. Não escolher por preferência.

Implementar: filtros globais, seletor de métrica, páginas, comparações, rankings, tabelas detalhadas. Minimizar leitura dos Parquets, otimizar agregações, evitar carregar a fato inteira na interface. Rodar 100% local, sem IA.

### FASE 5 — Testes e entrega

Testar: arquivos atuais; inclusão de nova base de Sell In; reprocessamento; duplicidade; arquivo inválido; coluna ausente; integridade referencial; reconciliação; filtros; comparação LY; YTD fiscal; YTD calendário; troca de métrica; divisão por zero; execução com o projeto anterior indisponível (renomeie temporariamente o caminho na config ou simule); execução sem IA.

**Entregas:** `README.md`, `requirements.txt`, `config/`, `logs/`, `tests/`, `docs/10_GUIA_OPERACIONAL.md`, `docs/11_RESULTADO_DOS_TESTES.md`, `docs/12_REGISTRO_DE_DECISOES.md`

---

## 5. ESTRUTURA DE PASTAS

```
novo_dashboard_gerencial_dori/
├── data/{raw/sell_in, staging, curated, quality}/
├── src/{extract, transform, load, models, utils}/
├── dashboard/
├── config/
├── docs/
├── logs/
├── tests/
├── run_pipeline.py
├── run_dashboard.py
├── requirements.txt
└── README.md
```

Adaptar apenas com justificativa. Evitar excesso de pastas, abstrações e camadas sem utilidade concreta.

---

## 6. MÉTRICAS

Seletor global: **Valor R$ | Volume (t) | Caixas**. Toda visualização de performance responde ao seletor.

| Métrica | Regra | Condição |
|---|---|---|
| Valor R$ | Coluna de receita/faturamento validada na fonte | Documentar coluna de origem, tratamento, unidade, sinal e exclusões |
| Volume (t) | `Peso_KG / 1000` se a origem estiver em kg | Registrar coluna de origem e conversão no catálogo |
| Caixas | Coluna existente, ou conversão por SKU validada | Se por conversão: identificar a tabela, validar cobertura de SKUs, listar produtos sem fator. **Não inventar nem assumir fator padrão** |
| Preço Médio | `SUM(Valor R$) / SUM(Peso KG)` em R$/kg | Nunca média simples das linhas. Só implementar após confirmar unidades, tratamento de devoluções e comportamento com denominador zero |
| Ticket Médio | Só existe se houver definição validada na fonte | Sem definição validada: não implementar, registrar como gap |

---

## 7. CALENDÁRIO

Suportar simultaneamente **ano calendário** (jan–dez) e **ano fiscal** (set–ago). Convenção esperada: set/2025 a ago/2026 = **FY2026** — validar essa nomenclatura antes de implementar.

Atributos, conforme o grão das fontes: data, ano, número e nome do mês, ano-mês, ordenação de ano-mês, trimestre e semestre calendário, ano calendário, ano fiscal, número do mês fiscal, nome do período fiscal, trimestre e semestre fiscal, início e fim do período.

YTD **não** deve ser gravado como flag permanente dependente da data atual se isso quebrar análise histórica. Acumulados são calculados conforme o período selecionado.

---

## 8. COMPARAÇÕES

Para Valor R$, Volume (t) e Caixas:

- **YTD Fiscal:** acumulado fiscal até o período selecionado vs. mesmo intervalo do FY anterior.
- **YTD Calendário:** acumulado calendário até o período selecionado vs. mesmo intervalo do ano anterior.
- **Mês vs LY:** mês selecionado vs. mesmo mês do ano anterior.
- **Variação absoluta:** `Atual − LY`.
- **Variação %:** `(Atual − LY) / LY`. Definir e documentar o comportamento quando LY for zero, nulo ou negativo. **Nunca exibir infinito ou erro técnico na interface.**
- **Participação %:** calcular sobre o total do contexto analítico correto. Documentar quais filtros são preservados e quais são removidos no denominador.

---

## 9. VALORES ESPERADOS (para validação, **não** para hardcode)

- **Canais:** ATACADO ESPECIALIZADO, ATACADO GENERALISTA, VAREJO ESPECIALIZADO, VAREJO, CASH & CARRY, NOVOS CANAIS, DISTRIBUIDOR
- **Categorias:** AMENDOIM, BALA, CHOCOLATE, COMPOUND, GELATINA, GOMAS, GRANULADO, JUBES FRUIT SNACK, PIRULITO, REGALIZ
- **Heads:** Ademir, Izabela, Michel, Vago
- **Geografia:** Brasil → UF

Compare os valores reais das bases com essa lista. Verifique variações de grafia, espaços e acentuação. **Não ajuste silenciosamente** (ex.: "CHOLOCATE" → "CHOCOLATE" só com registro da correção ou referência válida). Gere relatório de valores não reconhecidos em `data/quality/`.

---

## 10. FILTROS GLOBAIS

Conforme presença real no modelo: métrica, tipo de comparação, ano fiscal, ano calendário, período, mês, canal, categoria, Head, UF, bandeira, SKU.

Derivados dinamicamente das dimensões; exibindo apenas valores disponíveis; combináveis; aplicados a todas as visualizações pertinentes; seleções inválidas tratadas; botão claro de limpar filtros; estado dos filtros visível. Documentar o comportamento quando ano fiscal e ano calendário forem usados juntos.

---

## 11. PÁGINAS

**Página 1 — Visão Geral (executiva).**
Cards: Valor R$, Volume (t), Caixas, Preço Médio, Ticket Médio (se validado) — todos respeitando período, filtros, métrica e base de comparação.
Evolução mensal: atual, mesmo período LY, tendência, variação.
Comparativos: YTD Fiscal atual e anterior + variação absoluta e %; YTD Calendário atual e anterior + variação absoluta e %.
Detalhamentos por categoria, canal e Head, com: atual, LY, variação absoluta, variação % e participação.

**Página 2 — Geográfica.**
Brasil e UF, com evolução por período e recortes por categoria, SKU, canal e Head; atual, LY, variação absoluta e variação %.

**Página 3 — Preço Médio.**
O seletor global (Valor/Volume/Caixas) **não pode alterar a definição do Preço Médio**. Mantenha o seletor onde for pertinente aos demais elementos da página, preservando a métrica de preço como `SUM(Valor) / SUM(Peso KG)`.

> A especificação original mistura os elementos das páginas 2 e 3. Confirme a divisão com o HTML de referência e registre a decisão em `docs/12_REGISTRO_DE_DECISOES.md`.

---

## 12. DESIGN

Interface nova, usando o HTML apenas como referência visual. Identidade corporativa, visual limpo, foco executivo, poucos elementos por tela, hierarquia clara, filtros organizados, cores consistentes, títulos dinâmicos, indicação clara de período e de base de comparação, tooltips úteis, tabelas legíveis, responsivo, sem excesso de efeitos.

Formatação: receita em R$; volume em toneladas; caixas como quantidade; preço em R$/kg; percentuais com casas decimais controladas; negativos claramente identificados; abreviação de milhares/milhões consistente. **Cor não pode ser o único indicador de ganho ou queda** (use sinal, seta ou rótulo).

---

## 13. PERFORMANCE

Preparar o modelo para milhões de registros. Avaliar e documentar: DuckDB para consultas, predicate pushdown sobre Parquet, seleção só das colunas necessárias, tipos de dados, codificação de categorias, particionamento, tabelas agregadas, cache, lazy loading, paginação de tabelas, redução de recomputações.

Não particionar sem evidência de benefício. Toda camada agregada deve ser **reconciliável com a fato**.

---

## 14. QUALIDADE E LINHAGEM

Validar e reportar: linhas por arquivo; período mínimo e máximo; arquivos processados e rejeitados; colunas ausentes; tipos inválidos; chaves nulas e duplicadas; registros duplicados; totais de receita, peso e caixas; integridade fato↔dimensões; categorias, canais e Heads inesperados; UFs inválidas; SKUs sem cadastro; clientes sem bandeira; registros sem classificação; divisões por zero; cobertura dos períodos LY.

Linhagem mínima na fato: arquivo de origem, data/hora de processamento, identificador da execução, período de referência quando disponível.

**Nenhuma divergência pode ser corrigida silenciosamente.** Dados sensíveis não vão para os logs.

---

## 15. CRITÉRIOS DE ACEITE

- [ ] Novo projeto isolado; projeto anterior inalterado; sem dependência entre eles
- [ ] HTML usado só como referência funcional e visual, sem dados demonstrativos migrados
- [ ] ETL anterior analisado com matriz de reaproveitamento; só o pertinente foi copiado e adaptado
- [ ] Nova base de Sell In pode ser adicionada à pasta de entrada
- [ ] Um único comando executa o pipeline e atualiza os Parquets
- [ ] Dashboard consome automaticamente os dados atualizados
- [ ] Filtros dinâmicos e visuais respondendo corretamente
- [ ] Valor, Volume e Caixas funcionando pelo seletor
- [ ] YTD Fiscal, YTD Calendário e mês vs LY corretos
- [ ] Métricas reconciliadas com as fontes
- [ ] Sem dados fictícios e sem regras de negócio hardcoded
- [ ] Ticket Médio só existe se houver definição validada
- [ ] Preço Médio calculado como razão das somas
- [ ] Projeto roda sem IA
- [ ] README explica a operação completa; testes e resultados documentados

---

## 16. RELATÓRIO FINAL

Ao concluir, entregue um resumo objetivo com: estrutura criada; fontes utilizadas; arquivos analisados no projeto anterior; componentes reaproveitados, reescritos e descartados; modelo estrela final; grão da fato; métricas implementadas; páginas implementadas; testes realizados; resultado das reconciliações; gaps e pendências; riscos residuais; como executar o pipeline; como executar o dashboard; como adicionar uma nova base; lista de arquivos criados ou alterados.

---

## 17. PRIORIDADES (em caso de conflito)

**1.** Correção dos dados → **2.** Rastreabilidade → **3.** Independência do projeto → **4.** Simplicidade → **5.** Automação → **6.** Performance → **7.** Experiência visual

Nunca altere uma definição de negócio para os números fecharem. Nunca declare sucesso sem reconciliar. Incerteza que não bloqueia: registre a premissa e siga. Incerteza que muda materialmente uma métrica ou regra: documente o bloqueio, implemente o resto e sinalize no relatório final.

---

**Comece pela Fase 0 e prossiga sequencialmente.** Antes de escrever qualquer código, confirme o diretório de trabalho e apresente o plano da Fase 1.
