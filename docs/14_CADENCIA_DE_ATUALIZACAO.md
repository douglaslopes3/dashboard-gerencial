# 14 · Cadência de atualização das bases

Uma base é **diária** (Sell In); todas as outras são **estáticas**: só mudam
por alteração pontual. Este documento diz, para cada uma, o que fazer e o que
conferir. Nada aqui exige editar código. Reescrito em 03/09/2026 para o
estado atual (painel v4, arquivos por nível, publicação automática).

---

## 1. Sell In — atualização DIÁRIA

### O passo a passo operacional

**1. Trocar o arquivo do mês corrente.**
Largue a extração nova em `bases\Sell In\` (ou `data\raw\sell_in\`; as duas
valem) e **apague ou sobrescreva a extração anterior do mesmo mês**.

> **SUBSTITUIR, nunca adicionar.** O mês vem do **conteúdo** do arquivo
> (coluna `Ano mês`), não do nome. Se a extração de ontem e a de hoje do mesmo
> mês ficarem juntas na pasta, o pipeline **aborta de propósito** já na
> ingestão ("mês partido com o MESMO recorte de extração = cópia duplicada",
> auditoria A3), listando os dois arquivos; um arquivo sem rodapé de filtro
> cai na segunda defesa, o grão. É a proteção funcionando, não um defeito:
> ela existe porque uma cópia de conflito do OneDrive dobraria o mês.

Os meses fechados (arquivos antigos) ficam como estão. Mês partido em
`_p1`/`_p2` pela extração: largue **as duas partes**; o pipeline soma e
confere contra a soma dos dois gabaritos.

**2. Rodar o pipeline.**

```bash
python run_pipeline.py
```

~20 s (só o arquivo trocado é relido; o resto vem do cache). Tem de terminar em
`SUCESSO`. Se abortar, a mensagem diz o quê e onde; tabela de erros no
[guia operacional](10_GUIA_OPERACIONAL.md).

**3. Conferir: 4 olhadas em `data\quality\relatorio_qualidade.md`.**

| Olhar | O que denuncia |
|---|---|
| §1 Arquivos processados: o arquivo novo está lá, no mês certo, com mais linhas que ontem? | extração truncada ou mês trocado |
| §2 Período: o mês corrente é o máximo da série? | arquivo com competência errada |
| §6 Valores não reconhecidos: apareceu categoria/head/canal novo? | mudança de cadastro sem aviso |
| §10 Avisos: algum aviso **novo** em relação a ontem? | recorte da extração mudou, cobertura caiu |

As proteções automáticas que já travam sozinhas: soma × linha `Total` do
próprio arquivo (3 métricas), grão, filtro da extração comparado entre meses,
cobertura de estrutura (≥95%) e de canal (≥95%).

> **Aviso aberto com o BI (desde 01/09/2026):** ago/26 e set/26 vieram com
> recortes de extração diferentes dos 19 meses anteriores (o relatório lista
> os 3 recortes). Até o BI confirmar qual é o oficial, a série pode não ser
> comparável mês a mês nesses dois meses.

**4. Gerar o painel: a publicação vai junto.**

```bash
python run_dashboard.py
```

Uma execução (~10 s) gera os **73 arquivos** em `dashboard\build\` e os
**publica substituindo** em `Documentos\Painéis Comerciais\Gerencial\`
(D-52/Q13, MD5 conferido; `dashboard.publicacao.ativo: false` desliga):

```
Dashboard_Gerencial.html                  painel completo -> raiz do destino
Dashboard_Gerencial_N1_<head>.html        4  -> pasta de cada head
Dashboard_Gerencial_N2_<gerente>.html     13 -> pasta de cada gerente
Dashboard_Gerencial_N3_<sup-exec>.html    55 -> pasta de cada Sup./Exec.
```

O recorte por nível é aplicado na geração (o arquivo de um colaborador não
contém os dados de fora do escopo dele); o log confere que cada nível
particiona a base ao centavo. Configuração em `config → dashboard.por_nivel`
e `dashboard.publicacao`.

**5. O que NÃO é automático.**

1. **Compartilhar a pasta** de cada colaborador no SharePoint, uma vez (ação
   do Douglas; previsto para 04/09/2026). Depois disso, cada geração substitui
   o arquivo com o mesmo nome e o link continua válido.
2. **Recolher painel antigo** quando um nome de saída mudar ou um colaborador
   sair da estrutura: a geração não apaga o que não criou. Rode
   `python ferramentas/limpar_paineis_antigos.py` depois de gerar (D-60).
3. **Distribuição**: cada colaborador só recebe a própria pasta; o Full não
   vai para as pastas compartilhadas.

**Tempo total do ciclo diário: ~1 minuto.**

---

## 2. Bases estáticas — o que caracteriza uma alteração e o que refazer

Para **todas** elas o "refazer" é o mesmo: `python run_pipeline.py` +
`python run_dashboard.py`. O cache invalida sozinho pela data de modificação do
arquivo; não há passo manual de limpeza. O que muda é **o que conferir**
depois.

### 2.1 `bases/Canais/Canais.xlsx` (canal e subcanal por cliente)

| | |
|---|---|
| **O que caracteriza alteração** | reclassificação de canal/subcanal de clientes; entrada de clientes novos; correção dos casos apontados ao BI (os 3 clientes `KEY ACCOUNT` com R$ 0 e as 2 linhas de P&L `Orçado/Rateio KR`) |
| **Conferir depois** | `cobertura de canal` no resumo (tem de seguir ~100%); `data/quality/clientes_sem_canal.csv` (hoje 1 cliente, R$ 20 mil); §6 do relatório (canal novo aparece como "não reconhecido" até entrar no gabarito `validacao.valores_esperados.canal` do config) |
| **Atenção** | o arquivo traz o código zero-preenchido; o piso de 95% aborta se um layout novo quebrar o join |

### 2.2 `bases/Bases para tabelas dimensões/Hierarquia_Consolidada.xlsx` (D-34, D-50, D-56)

> **02/10/2026 (D-83):** a `Hierarquia_Consolidada.xlsx` deixou de ser lida. A hierarquia vem da `Hierarquia_AAAAMMDD.xlsx` mais recente em `../bases compartilhadas/` (comum ao DN e ao ROTA; aba `Hierarquia Vendas`, 1 linha por cliente, N1 a N4 com código e nome, rótulo "código - nome") e a bandeira do cadastro da `Estrutura de Clientes_AAAAMMDD.xlsx` da mesma pasta. O texto abaixo descreve a base anterior (histórico). Ver docs/12 D-83.


| | |
|---|---|
| **O que caracteriza alteração** | troca de head/gerente/sup./exec./vendedor de um cliente; cliente novo; posto que fica vago ou é preenchido; mudança de projeto; correção de duplicidade (como o desempate dos 13 clientes com dois códigos N4, incorporado na origem em 03/09/2026, D-56) |
| **Antes de salvar** | conferir que os **27 códigos de distribuidor** do `RTM_DePara_Transicao.xlsx` continuam na base. Distribuidor removido arrasta os 1.596 clientes RTM que apontam para ele (a cascata da D-61: em 03/09 a cobertura caiu de 97,65% para 75,40% e o pipeline abortou, até os distribuidores serem restaurados) |
| **Conferir depois** | `cobertura da estrutura` (hoje 97,65%; piso 95%); §10 do relatório: avisos de conflito N1–N4 (hoje zero) e correções `[Vago]` → `[VAGO]` (433 + 780 linhas, esperadas); §7b: RTM reatribuídos (1.596) e inativados (612) não devem mudar sem motivo. Se abortar no piso, `python ferramentas/diagnostico_cobertura.py` diz quem ficou fora e por quê |
| **Atenção** | este arquivo tem **dono no Comercial**: alteração local que não voltar ao arquivo-mestre será desfeita na próxima atualização dele. Os cabeçalhos têm quebra de linha interna (o leitor normaliza); a granularidade é cliente × vendedor (N4, ingerido desde a D-50). Grafia nova de posto vago → correção declarada em `config → dimensoes.estrutura_comercial.correcoes_*`, nunca no código |

### 2.3 `../bases compartilhadas/RTM_DePara_Transicao.xlsx` (D-85; até 02/10/2026 em `bases/RTM-Transicao/`) (D-50, D-59)

| | |
|---|---|
| **O que caracteriza alteração** | cliente novo migrado para distribuidor; cliente que volta ao atendimento direto; os **166 sem código de distribuidor** ("NOVO RIBEIRÃO PRETO"/"NOVO SJRP") ganharem código |
| **Conferir depois** | §7b do relatório: reatribuídos, distribuidores (27) e sem distribuidor; a receita que "entra" no canal Distribuidor (R$ 82,76 mi hoje); `data/quality/rtm_sem_distribuidor.csv` |
| **Atenção** | o cliente RTM herda do distribuidor hierarquia, canal, projeto **e bandeira** (D-59, parâmetro `saneamento.rtm_herda_bandeira`); o distribuidor precisa ter sell-in próprio para ceder o perfil, senão o cliente vira exceção |

### 2.4 `bases/Bases para tabelas dimensões/Hierarquia_Clientes_Faltando.xlsx` (D-50)

> **02/10/2026 (D-83, opção B do Douglas):** base DESLIGADA no config (`fontes.hierarquia_faltando: {}`); a hierarquia nova cobre 849 dos 850 clientes. Texto abaixo = histórico.


| | |
|---|---|
| **O que caracteriza alteração** | cliente que sai da lista (foi incorporado à Hierarquia_Consolidada); mudança SIM/NÃO; resposta do Comercial aos 158 pendentes Q5 |
| **Conferir depois** | §7b: inativados (612) e pendentes (158); `saneamento_inativados.csv` e `saneamento_pendentes_decisao.csv`. A janela de 6 meses é ancorada na última competência **fechada**, então a lista de inativos só muda quando um mês fecha |

### 2.5 `../bases compartilhadas/Produtos.xlsx` (D-85; até 02/10/2026 em `bases/Bases para tabelas dimensões/`) (cadastro de SKU)

| | |
|---|---|
| **O que caracteriza alteração** | SKU novo; troca de descrição, categoria ou marca; entrada dos **4 SKUs hoje fora do cadastro** (lista em `data/quality/skus_sem_cadastro.csv`, R$ 1,04 mi) |
| **Conferir depois** | `skus_sem_cadastro.csv` (idealmente vazio); §6 do relatório para categoria nova |

### 2.6 `config/config.yaml` e `config/geografia.yaml`

| | |
|---|---|
| **O que caracteriza alteração** | decisão de negócio: mês de início do fiscal, tolerâncias, pisos de cobertura, corte de exibição de bandeiras (`top_bandeiras`, `exibir_todas_bandeiras_em`), rótulos de tela das linhas Σ (`rotulos_exibicao`), correções declaradas, regras do saneamento (`rtm_herda_bandeira`, janela), nomes de saída, destino de publicação, gabarito de valores esperados |
| **Conferir depois** | o pipeline inteiro re-valida; toda correção declarada sai no log ("N linha(s) corrigidas por ..."). Nome de saída novo → rodar `ferramentas/limpar_paineis_antigos.py` depois de gerar (D-58/D-60) |

### 2.7 `dashboard/template_v4.html` (interface) e `dashboard/lib/chart.umd.min.js`

| | |
|---|---|
| **O que caracteriza alteração** | mudança de layout/tela (template editado à mão; o ativo é o que `dashboard.template` aponta; `template_v3.html` é retorno rápido e exige o pipeline pré-D-51 via git); atualização da biblioteca de gráfico (raro; hoje Chart.js 4.4.1) |
| **Refazer** | só `python run_dashboard.py`: o pipeline de dados não é tocado, e os 73 arquivos saem (e são publicados) na mesma execução |
| **Atenção** | os marcadores de dados e de biblioteca têm de existir **exatamente 1 vez** cada; o gerador aborta se alguém duplicar um em comentário. Depois de editar o template, **sempre regenerar antes de distribuir**; e regenerar publica |

### 2.8 O que NÃO dispara nada

`bases/Metas/` não tem leitor desde a D-49; Sell Out, Previsão, Estoque,
Alavancas e scorecards-comerciais estão em `_arquivo/bases-fora-do-escopo/`
(D-53). Atualizá-los não muda o painel gerencial.
