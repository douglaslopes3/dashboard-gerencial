# 15 · Distribuição no SharePoint — o que está em vigor e o que ficou aberto

> Reescrito em 03/09/2026. O plano original de 26/08 (5 decisões D-a a D-e,
> permissão por arquivo) foi **superado pela D-52/Q13** de 02/09/2026: pasta
> por colaborador, publicação feita pela própria geração. O histórico das
> opções está no git (`docs/15` até o commit da D-52) e em `docs/12`.

## 1. O modelo em vigor (D-52/Q13, D-58, D-60)

```
Documentos\Painéis Comerciais\Gerencial\
├── Dashboard_Gerencial.html                         Full: visão corporativa, só diretoria
├── 10 - DISTRIBUICAO - MICHEL MEIRA\
│   └── Dashboard_Gerencial_N1_10-distribuicao-michel-meira.html
├── 21000 - Ger Reg_SP - HEBER SILVA\
│   └── Dashboard_Gerencial_N2_21000-ger-reg-sp-heber-silva.html
├── 1110 - Superv_SPI - MURILO CUNHA\
│   └── Dashboard_Gerencial_N3_1110-superv-spi-murilo-cunha.html
└── ... (72 pastas: 4 N1 + 13 N2 + 55 N3)
```

| Aspecto | Como fica |
|---|---|
| **O que vai** | só os 73 HTML autocontidos (agregado; linha transacional nunca chega ao HTML). `bases/`, `data/`, `src/`, `config/`, `docs/`, logs e os CSVs de exceção ficam no ambiente de desenvolvimento |
| **Quem publica** | `python run_dashboard.py` (config `dashboard.publicacao`): copia **substituindo pelo mesmo nome** e confere o MD5 de cada cópia. Não há passo manual de cópia |
| **Segregação** | por **conteúdo**: o arquivo de um colaborador só contém os dados do escopo dele (recorte físico na geração, D-52). A permissão da pasta é a segunda camada, não a única |
| **Permissão** | o Douglas compartilha cada pasta com o respectivo colaborador **uma vez** (herança de permissão da pasta). Como o nome do arquivo não muda entre gerações, o link continua válido. O Full fica na raiz, fora das pastas |
| **Como o colaborador abre** | o SharePoint Online **não renderiza `.html`** no navegador (clicar baixa o arquivo). Modo de uso: sincronizar a pasta no OneDrive e abrir por duplo clique no Explorer, o mesmo dos Scorecards. Link por Teams abre o visualizador, que não executa o painel |
| **Nomes** | sem sufixo de versão desde a D-58 (`Dashboard_Gerencial*.html`); a versão do template é rastreada no config e no git |
| **Painel antigo que sobra numa pasta** | a geração não apaga o que não criou. `ferramentas/limpar_paineis_antigos.py` recolhe para quarentena (D-60) |
| **Foto do momento** | o painel embute os dados da última geração (é o que permite abrir offline); título e cabeçalho declaram execução e período |

## 2. Estado em 03/09/2026

| Item | Situação |
|---|---|
| 72 pastas criadas e populadas, Full na raiz | **feito** pela geração (02/09; regenerado em 03/09 com os nomes da D-58) |
| Painéis v3 de 01/09 na raiz do destino | **apagados** (02/09 à noite) |
| Painéis `_Canais_v4` antigos nas 72 pastas | **apagados** à mão em 03/09 (D-60) |
| Compartilhar cada pasta com o colaborador | **pendente**: previsto para 04/09/2026, após a apresentação. Até lá a segregação por pasta não está em vigor (a segregação por conteúdo já está) |
| Full restrito à diretoria | fica na raiz; sem compartilhamento explícito, só quem tem acesso à raiz vê |

## 3. O que ficou das decisões D-a a D-e

| Decisão original | Situação |
|---|---|
| D-a · como o head abre o painel | **na prática, opção A** (pasta sincronizada + duplo clique). `.aspx` e hospedagem interna não foram pedidos |
| D-b · quem vê o quê | **superada pela D-52/Q13**: pasta por colaborador, Full na raiz |
| D-c · quem roda a atualização diária | **na prática, opção A**: o Douglas, manualmente (2 comandos, ~1 min). Agendador e servidor não foram pedidos |
| D-d · publicação com ou sem trava | **superada pela D-52**: a publicação é a própria geração, com MD5; a trava é o pipeline abortar em dado ruim (nenhum Parquet nem painel sai de execução abortada) |
| D-e · PDF executivo além do HTML | **na prática, opção A**: só HTML. Não pedido |

Nenhuma das três "na prática" foi formalizada como decisão numerada; se algum
dia a resposta mudar (agendador, PDF, hospedagem), entra no `docs/12`.

## 4. Limitações que continuam valendo

| # | Limitação | Alternativa se incomodar |
|---|---|---|
| L1 | SharePoint Online não abre `.html` no navegador | sincronizar a pasta (modo atual); `.aspx` exigiria TI habilitar custom scripts |
| L2 | Full com 11,4 MB; N1 do Atacado com 7,2 MB | irrelevante para sync; `dashboard.top_bandeiras` 300→200 poupa ~0,8 MB se um dia precisar |
| L3 | Atualização depende de uma máquina com Python ligada | conviver (é 1 min/dia); Agendador do Windows num `.bat`; ou transferir ao BI/TI |
| L4 | Painel é foto da última geração | o ciclo diário resolve; título/cabeçalho declaram a execução |
