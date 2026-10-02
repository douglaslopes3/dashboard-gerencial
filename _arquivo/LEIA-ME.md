# _arquivo — o que está aqui e por quê (03/09/2026, D-53)

**Nada nesta pasta é lido pelo pipeline.** Ela existe para despoluir a raiz
do projeto (pedido do Douglas). Nada foi apagado — só movido. Verificado
após a mudança: `run_pipeline.py` exit 0 e testes verdes.

| Pasta | Conteúdo | Por que saiu |
|---|---|---|
| `bases-fora-do-escopo/` | Sell Out (MTRIX/FEMSA/KAN), Previsão de Vendas, Estoque Mtrix, Alavancas, scorecards-comerciais (+ COMO-INSTALAR.md), de-paras de sell-out | fora do escopo deste pipeline (docs/01 §3); o projeto vizinho dos Scorecards NÃO referencia esta pasta (verificado por grep em 02/09). Se a visão de sell out RTM (F6) sair do papel, volta o que ela precisar |
| `prototipo/` | Dashboard_Gerencial_Dori.html + o prompt original do projeto | referência histórica da engenharia reversa (docs/02) |
| `templates-antigos/` | template.html (v1), template_v2.html | o retorno rápido documentado é o template_v3 (D-51); v1/v2 são duas gerações atrás |
| `builds-antigos/` | builds _v4_HEAD_ da D-51 | substituídos pelos _N1_/_N2_/_N3_ da D-52; regeneráveis |
| `backups-pre-fases/` | *.pre_D48, *.pre_D49, backup_2026-09-02_pre_N3 | todo o conteúdo está no git (commits b08c588..bc571f3); eram o rollback antes dos commits |
| `staging-aposentado/` | cache do DePara_Estrutura_Comercial | base substituída pela Hierarquia_Consolidada na D-34 |
| `working/` | scripts de medição das fases | material de trabalho; as medições estão em docs/12 |
| `pedidos-encerrados/` | `desempate_vendedor_N4.csv` | pedido **respondido na origem** (D-56, 03/09/2026): o desempate dos 13 clientes com dois códigos N4 foi incorporado à `Hierarquia_Consolidada.xlsx`. O arquivo nunca foi lido por código nenhum — era material para o Comercial preencher. Fica aqui como histórico do pedido |
| `pedidos-encerrados/` | `saneamento_Q5_hierarquia_NAO_com_sellin.csv` | **substituído** (D-62, 03/09/2026) pelo `docs/pedidos/pedido_Q5_hierarquia_158.xlsx`, que tem a mesma lista com colunas de resposta. Nunca foi lido por código; a lista viva sai em `data/quality/saneamento_pendentes_decisao.csv` |
| `bases-fora-do-escopo/hierarquia_ate_2026-10-01/` | `Hierarquia_Consolidada.xlsx` e `Hierarquia_Clientes_Faltando.xlsx` (md5 conferido na mudança, 02/10/2026) | **substituídas** na D-83 (02/10/2026): a hierarquia é a `Hierarquia_AAAAMMDD.xlsx` mais recente de `../bases compartilhadas/` e o saneamento pela lista Faltando foi desligado (opção B). Verificado depois: `run_pipeline.py` exit 0, cobertura 99,94% |
