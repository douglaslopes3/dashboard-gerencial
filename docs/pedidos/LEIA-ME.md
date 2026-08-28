# Pedidos prontos para encaminhar

Material gerado sob demanda para os donos das bases — **não é saída do
pipeline** (por isso mora aqui, e não em `data/quality/`, que é regravada a
cada execução — auditoria, C14).

| Arquivo | Para quem | O quê |
|---|---|---|
| `bases/Bases para tabelas dimensões/Hierarquia_Complemento.xlsx` | **Comercial** | **validar (D-34)**: 2.612 clientes que faturam (554 ativos em ago/2026, R$ 136,4 mi/24m) e não constam da `Hierarquia_Consolidada.xlsx`, mapeados pelo supervisor da base anterior. A aba `LEIA-ME` explica; as colunas ORIGEM/DOMINÂNCIA/RECEITA são apoio à validação. O ideal é o dono **incorporá-los à base oficial** — aí o complemento esvazia sozinho |
| `incluir_no_DePara_estrutura.xlsx` | ~~Comercial~~ | **superado pela D-34** (o layout era o do `DePara_Estrutura_Comercial.xlsx`, substituído em 28/08/2026). Os mesmos 71 clientes seguem `NÃO ATRIBUÍDO` — se o Comercial for incluí-los, agora é no layout da `Hierarquia_Consolidada.xlsx` (`data/quality/clientes_sem_estrutura.csv` tem a lista viva) |
| `clientes_canal_key_account.csv` | **BI** | os 3 clientes com canal `KEY ACCOUNT` no sell-in (todos com R$ 0,00) para reclassificar no `Canais.xlsx` — junto das 2 linhas de P&L (`Orçado KR`/`Rateio P&L KR`) que não são clientes |
