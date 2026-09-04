# ferramentas/ — scripts de medição e manutenção

Nada aqui é etapa do pipeline: `run_pipeline.py` e `run_dashboard.py` não
importam nem chamam nada desta pasta. São ferramentas para **medir antes de
decidir** e para **arrumar a publicação**, versionadas porque o resultado
delas sustenta decisões do `docs/12`. Rodam de qualquer pasta
(`python ferramentas/<script>.py`) e só leem as bases e o curated; nenhum
altera base, config, cubo ou Parquet.

| Script | Para quê | Quando rodar | Escreve |
|---|---|---|---|
| `diagnostico_cobertura.py` | explica uma queda de cobertura da estrutura comercial: tamanho, quem ficou fora, se a causa é a **cascata do RTM** (distribuidor que saiu da `Hierarquia_Consolidada` arrasta todos os clientes que apontam para ele) ou a chave que parou de casar (D-61) | sempre que o pipeline abortar no piso de cobertura depois de uma edição da `Hierarquia_Consolidada.xlsx` | `data/quality/diagnostico_fora_da_estrutura.csv` e `diagnostico_distribuidores_orfaos.csv` |
| `analise_bandeira_rtm.py` | mede, por head, quanto do faturamento vem de cliente RTM, quantas bandeiras cada head vê e o custo de o cliente RTM herdar a bandeira do distribuidor (a medida da D-59) | para reproduzir o "antes" da D-59 (`saneamento.rtm_herda_bandeira: false`) ou reavaliar a regra | `data/quality/analise_bandeira_rtm_perdas.csv` |
| `limpar_paineis_antigos.py` | recolhe para uma quarentena (`_ANTIGOS_PARA_APAGAR/`) todo `.html` das pastas de publicação que a geração **atual** não produz; calcula a lista esperada com o mesmo config e o mesmo `cubos.json` do gerador, e aborta se faltar algum painel atual (D-60) | depois de `python run_dashboard.py`, sempre que um nome de saída mudar (D-58) ou um colaborador sair da estrutura | move arquivos dentro do destino de publicação; `--listar` só mostra |
| `comparar_paineis.py` | compara dois conjuntos de painéis sem navegador (por padrão o **publicado** × o recém-gerado em `dashboard/build`): descompacta o bloco de dados de cada HTML e confere total geral, total por mês, total por bandeira (dentro do teto teórico de arredondamento: 1 unidade por linha de cubo), o cubo de SKU exato e as listas de dimensão; pareia pelo caminho e avisa de cópias avulsas em subpastas (D-72) | **antes de religar a publicação** depois de qualquer mudança de grão ou de template: a prova de que nenhum número que o leitor vê mudou | nada; `exit 1` se algum arquivo diferir |

Os CSVs saem em `data/quality/`, que é regravada a cada execução do pipeline
(o pipeline só regrava os arquivos dele, mas a pasta não é versionada): o
número que virou decisão vai para o `docs/12`, não fica só no CSV.
