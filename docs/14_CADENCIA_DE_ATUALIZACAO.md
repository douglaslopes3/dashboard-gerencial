# 14 · Cadência de atualização das bases

Uma base é **diária** (Sell In); todas as outras são **estáticas** — só mudam
por alteração pontual. Este documento diz, para cada uma, o que fazer e o que
conferir. Nada aqui exige editar código.

---

## 1. Sell In — atualização DIÁRIA

### O passo a passo operacional

**1. Trocar o arquivo do mês corrente.**
Largue a extração nova em `bases\Sell In\` (ou `data\raw\sell_in\` — as duas
valem) e **apague ou sobrescreva a extração anterior do mesmo mês**.

> ⚠ **SUBSTITUIR, nunca adicionar.** O mês vem do **conteúdo** do arquivo
> (coluna `Ano mês`), não do nome. Se a extração de ontem e a de hoje do mesmo
> mês ficarem juntas na pasta, o mesmo mês entra duas vezes — e o pipeline
> **aborta de propósito** ("linhas fora do grão declarado"), apontando a chave
> e os dois arquivos. É a proteção funcionando, não um defeito.

Os meses fechados (arquivos antigos) ficam como estão. Mês partido em
`_p1`/`_p2` pela extração: largue **as duas partes** — o pipeline soma e
confere contra a soma dos dois gabaritos.

**2. Rodar o pipeline.**

```bash
python run_pipeline.py
```

~20 s (só o arquivo trocado é relido; o resto vem do cache). Tem de terminar em
`SUCESSO`. Se abortar, a mensagem diz o quê e onde — tabela de erros no
[guia operacional](10_GUIA_OPERACIONAL.md).

**3. Conferir — 4 olhadas em `data\quality\relatorio_qualidade.md`:**

| Olhar | O que denuncia |
|---|---|
| §1 Arquivos processados: o arquivo novo está lá, no mês certo, com mais linhas que ontem? | extração truncada ou mês trocado |
| §2 Período: o mês corrente é o máximo da série? | arquivo com competência errada |
| §6 Valores não reconhecidos: apareceu categoria/head/canal novo? | mudança de cadastro sem aviso |
| §10 Avisos: algum aviso **novo** em relação a ontem? | recorte da extração mudou, cobertura caiu |

As proteções automáticas que já travam sozinhas: soma × linha `Total` do
próprio arquivo (3 métricas), grão, filtro da extração comparado entre meses,
cobertura de estrutura (≥95%) e de canal (≥95%).

**4. Gerar o painel.**

```bash
python run_dashboard.py
```

Sai em `dashboard\build\Dashboard_Gerencial_Canais.html`. Distribuição para os
heads: ver o [plano SharePoint](15_PLANO_SHAREPOINT.md) (decisões em aberto).

**Tempo total do ciclo diário: ~1 minuto.**

---

## 2. Bases estáticas — o que caracteriza uma alteração e o que refazer

Para **todas** elas o "refazer" é o mesmo: `python run_pipeline.py` +
`python run_dashboard.py`. O cache invalida sozinho pela data de modificação do
arquivo — não há passo manual de limpeza. O que muda é **o que conferir** depois.

### 2.1 `bases/Canais/Canais.xlsx` (canal e subcanal por cliente)

| | |
|---|---|
| **O que caracteriza alteração** | reclassificação de canal/subcanal de clientes; entrada de clientes novos; correção dos casos apontados ao BI (os 3 clientes `KEY ACCOUNT` com R$ 0 e as 2 linhas de P&L `Orçado/Rateio KR`) |
| **Conferir depois** | `cobertura de canal` no resumo (tem de seguir ~100%); `data/quality/clientes_sem_canal.csv` (tem de seguir vazio); §6 do relatório (canal novo aparece como "não reconhecido" até entrar no gabarito `validacao.valores_esperados.canal` do config) |
| **Atenção** | o arquivo traz o código zero-preenchido — o piso de 95% aborta se um layout novo quebrar o join |

### 2.2 `bases/Bases para tabelas dimensões/DePara_Estrutura_Comercial.xlsx`

| | |
|---|---|
| **O que caracteriza alteração** | troca de head/gerente/supervisor; entrada dos **71 clientes hoje `NÃO ATRIBUÍDO`** (arquivo pronto para colar: `data/quality/incluir_no_DePara_estrutura.xlsx`, head `Vago - 2600` já preenchido); mudança de projeto; cliente novo |
| **Conferir depois** | `cobertura da estrutura` (hoje 99,98% — colando os 71 vai a 100%); avisos de cliente com dois supervisores/heads; se um head mudar de NOME, a correção declarável fica em `config → dimensoes.estrutura_comercial.correcoes_head` (como Maykon→Vago), nunca no código |
| **Atenção** | este arquivo tem **dono no Comercial** — alteração local que não voltar ao arquivo-mestre será desfeita na próxima atualização dele |

### 2.3 `bases/Bases para tabelas dimensões/Produtos.xlsx` (cadastro de SKU)

| | |
|---|---|
| **O que caracteriza alteração** | SKU novo; troca de descrição, categoria ou marca; entrada dos **7 SKUs hoje fora do cadastro** (lista em `data/quality/skus_sem_cadastro.csv`) |
| **Conferir depois** | `skus_sem_cadastro.csv` (idealmente vazio); §6 do relatório para categoria nova (ex.: `ESPECIAIS` passar a faturar) |

### 2.4 `config/config.yaml` e `config/geografia.yaml`

| | |
|---|---|
| **O que caracteriza alteração** | decisão de negócio: mês de início do fiscal, tolerâncias, pisos de cobertura, corte de bandeiras (300), correções declaradas, gabarito de valores esperados; rótulos de UF |
| **Conferir depois** | o pipeline inteiro re-valida; toda correção declarada sai no log ("N linha(s) corrigidas por ...") |

### 2.5 `dashboard/template.html` (interface) e `dashboard/lib/chart.umd.min.js`

| | |
|---|---|
| **O que caracteriza alteração** | mudança de layout/tela (template — editado à mão); atualização da biblioteca de gráfico (raro; hoje Chart.js 4.4.1) |
| **Refazer** | só `python run_dashboard.py` — o pipeline de dados não é tocado |
| **Atenção** | os marcadores de dados e de biblioteca têm de existir **exatamente 1 vez** cada; o gerador aborta se alguém duplicar um em comentário |

### 2.6 O que está em `bases/` e NÃO dispara nada

`Sell Out - MTRIX/`, `Sell Out - FEMSA/`, `Sell Out - KAN/`, `Metas/`,
`Previsão de Vendas/`, `Estoque Mtrix/`, `Alavancas/` e
`scorecards-comerciais/` **não são lidos por este pipeline** — atualizá-los não
muda o painel gerencial (são insumo dos Scorecards de canal, projeto vizinho
com pipeline próprio).
