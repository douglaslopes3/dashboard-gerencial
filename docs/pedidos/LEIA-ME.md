# Pedidos prontos para encaminhar

Material gerado sob demanda para os donos das bases — **não é saída do
pipeline** (por isso mora aqui, e não em `data/quality/`, que é regravada a
cada execução — auditoria, C14).

| Arquivo | Para quem | O quê |
|---|---|---|
| `bases/Bases para tabelas dimensões/Hierarquia_Complemento.xlsx` | **Comercial** | **validar (D-34)**: 2.612 clientes que faturam (554 ativos em ago/2026, R$ 136,4 mi/24m) e não constam da `Hierarquia_Consolidada.xlsx`, mapeados pelo supervisor da base anterior. A coluna `PROJETO` está **em branco por decisão** (28/08): o painel só mostra projetos da hierarquia nova; o valor da base anterior está na coluna de apoio. A aba `LEIA-ME` explica. O ideal é o dono **incorporá-los à base oficial**: aí o complemento esvazia sozinho |
| `clientes_sem_estrutura.xlsx` | **Comercial** | os **71 clientes** que faturam no Sell In e não constam de nenhuma base de estrutura (nem oficial, nem complemento): 69 ativos em ago/2026, R$ 421 mil/24m, códigos altos (clientes novos, criados depois das extrações). Pedido: classificá-los na `Hierarquia_Consolidada.xlsx`. Lista viva em `data/quality/clientes_sem_estrutura.csv` |
| `incluir_no_DePara_estrutura.xlsx` | ~~Comercial~~ | **superado pela D-34** (layout da base substituída em 28/08/2026); o pedido dos mesmos 71 clientes foi refeito acima, no formato novo |
| `clientes_canal_key_account.csv` | **BI** | os 3 clientes com canal `KEY ACCOUNT` no sell-in (todos com R$ 0,00) para reclassificar no `Canais.xlsx` — junto das 2 linhas de P&L (`Orçado KR`/`Rateio P&L KR`) que não são clientes |
| `pedido_metas_cruzamento.xlsx` + `pedido_metas_cruzamento.md` | **Comercial** | fechar o cruzamento **Metas FY 26/27 × Realizado** (hoje 73,9% do R$ pareado): abrir os baldes `Sem Mudança` (R$ 26,07 mi) e `Projeto L` (R$ 4,44 mi) por bandeira, dar par aos códigos DISO/UNIVALE/PELLAH (R$ 1,36 mi), identificar o executivo `4210` e confirmar a fusão LASA+HORTIFRUTTI (cód. 8200372). O `.md` é o texto de e-mail pronto; a planilha tem uma aba por item com colunas em branco para preencher. Gerados em 01/09/2026, reconciliados ao centavo |
