# Pedido ao Comercial: 158 clientes ativos sem hierarquia (Q5)

*Texto pronto para e-mail. Planilha anexa: `pedido_Q5_hierarquia_158.xlsx`
(aba `clientes`, com colunas em branco para preencher). Gerado em 03/09/2026
a partir da execução `20260903-155531` do pipeline (D-62).*

---

Pessoal,

Na base `Hierarquia_Clientes_Faltando.xlsx` há **158 clientes marcados com
`Hierarquia = NÃO` que continuam faturando**: todos têm sell-in entre mar/26 e
ago/26, 100 deles compraram em jul ou ago/26, e 6 já faturaram em set/26.
Somam **R$ 36,5 mi em 24 meses** e **R$ 5,46 mi nos últimos 6 meses fechados**.

O painel gerencial não inventa vínculo: hoje esses 158 aparecem como
`NÃO ATRIBUÍDO`, fora da matriz Head → Gerente → Sup./Exec. → Vend./RCA, e a
receita deles não entra no painel de nenhum colaborador.

Os maiores da janela mar–ago/26:

| Cliente | Canal | UF | R$ mar–ago/26 |
|---|---|---|---:|
| EPOCA COMERCIO E DISTRIBUICAO | ATACADO GENERALISTA | MG | 539.318 |
| CASA E VIDEO BRASIL | VAREJO ESPECIALIZADO | RJ | 472.775 |
| KRUPER DISTRIBUIDORA DE ALIMENTOS | DISTRIBUIDOR | RS | 374.736 |
| AVANT DISTRIBUIDORA DE ALIMENTOS | DISTRIBUIDOR | SP | 355.872 |
| FALEKA ATACADISTA E VAREJISTA | DISTRIBUIDOR | SP | 306.802 |

Por canal: 17 distribuidores (R$ 2,25 mi na janela, 41%), 45 cash & carry,
47 varejo, 20 varejo especializado, 9 atacado generalista, 20 atacado
especializado.

**O que precisamos**, para cada linha da planilha:

1. os códigos N1 a N4 (head, gerente, sup./exec., vend./RCA) na estrutura
   atual; ou
2. a marcação **INATIVAR = S**, se o cliente de fato saiu da carteira (aí ele
   vai para o balde de inativos, com o histórico preservado nos totais).

O ideal é incorporar as linhas direto na `Hierarquia_Consolidada.xlsx`: o
pipeline lê de lá, e a lista esvazia sozinha na próxima atualização. Nenhum
desses clientes é distribuidor de cliente RTM, então a inclusão não tem efeito
em cascata.

Obrigado,
Douglas
