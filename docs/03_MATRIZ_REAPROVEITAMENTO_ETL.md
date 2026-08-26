# 03 · Matriz de reaproveitamento do ETL anterior

**Projeto anterior:** `C:\Users\dldsouza\OneDrive - Dori Alimentos S.A\Documentos\Dashboards - Heads - Canais`

**Regime de acesso:** somente leitura. Nada foi escrito, movido, renomeado,
apagado ou executado lá. A única coisa que saiu de lá foi **uma cópia** do bundle
`lib/chart.umd.min.js` (arquivo de biblioteca, não código de negócio), hoje em
`dashboard/lib/chart.umd.min.js`.

**Teste de independência:** ver `docs/11_RESULTADO_DOS_TESTES.md`, teste T-14.

## Legenda

**(1)** reutilizar sem mudança relevante · **(2)** reutilizar com adaptação ·
**(3)** reescrever simplificado · **(4)** não utilizar · **(5)** exige validação
de negócio.

---

## 1. Arquivos analisados

| Arquivo | Linhas | Papel no projeto anterior |
|---|---:|---|
| `etl/_comum.py` | 497 | config, log, cache, IO de camadas, normalização, calendário |
| `etl/_fontes.py` | ~900 | um leitor por fonte (camada bronze) |
| `etl/01_dim_produto.py` | ~170 | DIM_PRODUTO |
| `etl/02_dim_cliente_master.py` | — | DIM_CLIENTE (sell-out) |
| `etl/03_dim_hierarquia.py`, `03b_dim_cliente_canal.py` | — | hierarquia comercial |
| `etl/04_dim_data.py` | ~140 | DIM_DATA (dois calendários) + DIM_REGIAO |
| `etl/05_fato_sellout.py` | — | FATO_SELLOUT |
| `etl/06_fato_sellin.py` | ~200 | FATO_SELLIN |
| `etl/07_fato_previsao_vendas.py` | — | previsão |
| `etl/08_kpis.py`, `09_dashboard_data.py`, `09b_gerar_D.py` | — | camada analítica → JSON |
| `etl/10_build_html.py` | ~120 | injeta JSON + libs no template |
| `etl/99_validacao.py` | — | relatório de validação |
| `run_pipeline.py` | ~150 | orquestração dos 13 passos |
| `config.yaml` | 85 KB | configuração |

---

## 2. Matriz componente a componente

### 2.1 Reutilizados **com adaptação (2)** — o núcleo do aproveitamento

| # | Origem | Função / bloco | Finalidade | Regra atendida | Adaptação feita | Risco |
|---|---|---|---|---|---|---|
| A1 | `_comum.py` | `texto()` | trim + colapso de espaço + maiúscula, vazio → `<NA>` | §14 (grafias divergentes) | copiado quase igual; `src/utils/texto.py` | baixo |
| A2 | `_comum.py` | `digitos()` | extrai só dígitos, tolera `1010846.0`, máscara e sujeira | §2.2 (chaves) | idem, com `lstrip("0")` explícito no chamador | baixo |
| A3 | `_comum.py` | `numero()` | float tolerando formato BR | §6 | simplificado: a fonte já entrega float | baixo |
| A4 | `_comum.py` | `ano_mes()` | normaliza `2025/JUL`, `2025/07` → `2025-07` | §7 | mantido (a fonte só usa `AAAA/MM`, mas o leitor aceita as duas) | baixo |
| A5 | `_comum.py` | `ano_fiscal()`, `mes_fiscal()`, `rotulo_fiscal()` | ano fiscal set→ago, mês fiscal 1..12 | §7 | mês de início continua vindo do config; **nomenclatura mudou** (ver D-02) | médio → validado |
| A6 | `_comum.py` | `pct()`, `div()` | divisão segura, base zero → `None` | §8 (nunca exibir infinito) | mantido; `None` vira `n/d` na tela | baixo |
| A7 | `_comum.py` | `salvar()` / `carregar()` | IO de camada em parquet com log | §3 | mantido | baixo |
| A8 | `_comum.py` | `ler_cache()` + `VERSAO_CACHE` | cache de leitura de Excel por (nome, tamanho, mtime, versão) | performance | mantido **com a lição**: a versão do cache sobe quando um leitor muda | médio |
| A9 | `_fontes.py` | `_ler_um_sellin_sku()` | rodapé `Total` como gabarito + texto dos filtros | §14 (reconciliação) | mantido; passou a ler também `Qtde Faturado` do gabarito | baixo |
| A10 | `_fontes.py` | `_conferir_sellin()` | soma × gabarito, mês a mês, aborta se estourar tolerância | §14 | estendido para as **três** métricas | baixo |
| A11 | `_fontes.py` | `_conferir_filtro_extracao()` | detecta mudança de recorte da extração entre meses | §14 (linhagem) | **simplificado**: a assinatura passa a ignorar a cláusula `Ano mês é ...`, que muda por construção | baixo |
| A12 | `_fontes.py` | `_ler_depara_estrutura()` | Head/Gerente/Supervisor por `Cód. cliente`, com `lstrip("0")` | §2.2 | mantido; desempate e correções continuam **no config**, nunca no código | médio |
| A13 | `04_dim_data.py` | `construir_data()` | DIM_CALENDARIO com os dois calendários na mesma tabela | §7 | **simplificado**: saíram `DIAS_UTEIS`, feriados e `ANO_MES_MOM` (sem uso neste MVP) | baixo |
| A14 | `04_dim_data.py` | `NOME_UF`, `NOME_REGIAO` | nomes de UF e região | §11.2 | mantido em `config/geografia.yaml` (é referência, não regra de negócio) | baixo |
| A15 | `10_build_html.py` | `embutir_libs()` | embute o bundle JS no HTML, escapando `</script>` | §4 (rodar local) | mantido quase igual | baixo |
| A16 | `10_build_html.py` | injeção `/*DADOS_INICIO*/…/*DADOS_FIM*/` | template editado à mão, só os dados mudam | §12, §4 | mantido | baixo |
| A17 | `09_dashboard_data.py` | `n()`, `i()`, `t()` | número pronto para JSON, sem `NaN`/`numpy` | §8 | mantido | baixo |
| A18 | `06_fato_sellin.py` | checagem de FK fato↔dimensão | integridade referencial, aborta | §14 | mantido, generalizado | baixo |

### 2.2 Reescritos **simplificados (3)**

| # | Origem | Por que não foi copiado |
|---|---|---|
| B1 | `06_fato_sellin.py` inteiro | 80% do arquivo é `CANAL` + `FLAG_NO_RECORTE` + `FLAG_TEM_SELLOUT` + ponte para sell-out. **Nada disso existe neste escopo.** Sobrou o núcleo: ler, checar grão, checar FK, gravar |
| B2 | `01_dim_produto.py` | `derivar_peso()` (gramatura por regex), `EAN` da FEMSA e as flags de sell-out saem. O cadastro novo **tem** coluna `Marca` — que lá era inferida e foi removida por isso |
| B3 | `run_pipeline.py` | 13 passos viram 6. Orquestração por lista de funções, sem `subprocess` |
| B4 | `_comum.py` `log()` | ganhou saída em arquivo (`logs/`) além do console, exigida pelo §5 do prompt |
| B5 | `99_validacao.py` | reescrito em torno do checklist do §14, sem os itens de sell-out/meta |

### 2.3 **Não utilizados (4)**

| Componente | Motivo |
|---|---|
| `_fontes.py`: `ler_mtrix`, `ler_femsa`, `_ler_um_mtrix`, `_conferir_mes_duplicado`, `ler_depara_femsa`, `ler_depara_distribuidores` | Sell Out — fora do escopo |
| `_fontes.py`: `ler_metas`, `ler_previsao`, `ler_alavancas`, `_competencia_meta` | Metas / Previsão / Planejamento — fora do escopo |
| `_fontes.py`: `ler_clientes_canal`, `clientes_do_canal`, `clientes_do_recorte` | lista congelada de um canal específico. O painel gerencial **não recorta canal** |
| `_comum.py`: `cnpj14`, `raiz_cnpj`, `_cnpj_ok`, `_cpf_ok`, `tipo_documento` | não há CNPJ nem CPF na base de sell-in |
| `_comum.py`: `classificar_cluster`, `mapa_regiao`+config de cluster | classifica **segmento de PDV** do MTRIX. Não se aplica |
| `_comum.py`: `feriados_nacionais`, `dias_uteis`, `anos_sem_feriado` | servem à projeção de mês parcial, que não está no escopo |
| `_comum.py`: `canal_ativo`, `fato_sellin(canal)` | o recorte por canal ativo não existe aqui |
| `05_fato_sellout.py`, `07_fato_previsao_vendas.py`, `08_kpis.py`, `09b_gerar_D.py` | fatos e KPIs fora do escopo |
| `02_dim_cliente_master.py`, `03_dim_hierarquia.py`, `03b_dim_cliente_canal.py` | modelam a hierarquia de distribuidor com CNPJ e sell-out. Aqui a estrutura é **um join direto** pelo `Cód. cliente` |
| `extrair_regras.py`, `extrair_scorecards.py`, `mapear_D.py`, `conferir_painel.py`, `publicar.py`, `preparar_template.py`, `lacunas.py`, `renomear_sellin.py`, `verificar_*.py` | ferramentas do ciclo de publicação dos Scorecards de canal |
| `config.yaml` (85 KB) | 95% é configuração de canal, meta, alavanca e patch de painel. O config novo tem ~120 linhas |

### 2.4 **Exigem validação de negócio (5)**

| # | Componente | O que precisa ser validado | Estado |
|---|---|---|---|
| C1 | `rotulo_fiscal()` | o anterior rotula set/25–ago/26 como `FY25/26`; o prompt (§7) pede `FY2026` | **decidido** — ver D-02. `ANO_FISCAL = 2026` (ano de fechamento), rótulo `FY2026`, os dois na dimensão |
| C2 | correção de rótulo de head (`Maykon - 2600` → `Vago`) | é decisão do Comercial | **GAP-03** — nada foi corrigido; o config tem a chave vazia |
| C3 | desempate de cliente com dois supervisores | 1 cliente afetado | vence a 1ª linha, **com aviso**; a chave de desempate fica no config |
| C4 | conversão para Caixas | o anterior derivava `UNID_POR_CAIXA` por regex sobre a descrição | **não reaproveitado** — aqui a caixa é **coluna de origem**, validada em `01 §1.5`. Regex não entra em produção |

---

## 3. Código morto, duplicado ou obsoleto — não reaproveitado

Nada ligado a Sell Out, Metas, Previsão, Planejamento ou Verbas foi copiado.
Também não foram copiados: os patches de painel (`patch32..51`), o congelamento
de `FATO_META`, o mecanismo de publicação com pasta de referência de aceite, e as
regras de `PROJETO`/alavanca — todos específicos dos Scorecards de canal.

---

## 4. A lição mais cara do projeto anterior, aplicada aqui

Os comentários do `_comum.py` e do `_fontes.py` registram erros reais que
custaram medição. Três foram incorporados como regra deste projeto:

1. **Versão de cache** — cache que sobrevive à mudança do leitor faz a checagem
   rodar "de mão vazia" e o painel fechar verde com dado errado.
   `src/extract/cache.py` carrega `VERSAO_CACHE` e a documenta.
2. **Quem conhece a origem corrige a origem** — a normalização vive no leitor,
   não espalhada pelos passos. Corrigir em um passo só faz os outros lerem outra
   verdade.
3. **A mensagem de erro diz ONDE se procurou** — quando a pasta de entrada não
   tem arquivo, o erro imprime o caminho tentado, se ele existe e quantos
   arquivos há lá. Um caminho fixo na mensagem manda procurar no lugar errado.
