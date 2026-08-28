# Pedidos prontos para encaminhar

Material gerado sob demanda para os donos das bases — **não é saída do
pipeline** (por isso mora aqui, e não em `data/quality/`, que é regravada a
cada execução — auditoria, C14).

| Arquivo | Para quem | O quê |
|---|---|---|
| `incluir_no_DePara_estrutura.xlsx` | **Comercial** | as 71 linhas dos clientes sem estrutura, no layout exato do `DePara_Estrutura_Comercial.xlsx`, com `Novo Head = Vago - 2600` já preenchido (gerente/supervisor em branco para completar). Colar no arquivo-mestre; o pipeline absorve sozinho na execução seguinte |
| `clientes_canal_key_account.csv` | **BI** | os 3 clientes com canal `KEY ACCOUNT` no sell-in (todos com R$ 0,00) para reclassificar no `Canais.xlsx` — junto das 2 linhas de P&L (`Orçado KR`/`Rateio P&L KR`) que não são clientes |
