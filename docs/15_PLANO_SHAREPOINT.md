# 15 · Plano de disponibilização no SharePoint (saída do ambiente de IA)

Objetivo: os heads consumirem os painéis **sem depender do ambiente de
desenvolvimento**. O que segue é plano + **decisões em aberto para o Douglas**
— nada aqui foi decidido nem executado.

## 0. O que existe hoje, medido (26/08/2026)

| Painel | Arquivo | Tamanho | Onde está |
|---|---|---:|---|
| **Gerencial de Canais** | `Dashboard_Gerencial_Canais.html` | **14,3 MB** | `Dashboard - Gerencial\dashboard\build\` |
| Scorecard Distribuição | `Scorecard_Distribuição.html` | 16,9 MB | `Dashboards - Heads - Canais\Scorecards\` |
| Scorecard Atacado | `Scorecard_Atacado.html` | 6,8 MB | idem |
| Scorecard KAR | `Scorecard_KAR.html` | 4,8 MB | idem |
| Scorecard KAN | `Scorecard_KAN.html` | 0,7 MB | idem |

Todos são **HTML autocontidos**: um arquivo, zero rede, abrem por duplo clique.
As duas pastas de projeto já vivem em `OneDrive - Dori Alimentos S.A` — ou
seja, o armazenamento **já é** SharePoint/OneDrive corporativo; o que falta é a
**camada de distribuição** (biblioteca própria, permissões e rotina de cópia),
para os heads não enxergarem o projeto inteiro (bases, código, docs).

## 1. O que vai para o SharePoint

**Proposta: só os artefatos finais — nunca a pasta do projeto.**

| Vai | Não vai (fica no ambiente de desenvolvimento) |
|---|---|
| os 5 HTML dos painéis | `bases/` (dado bruto — 16 mil clientes, receita por cliente), `data/` (parquets), `src/`, `config/`, `docs/`, `tests/`, `.git/`, logs |
| (opcional, decisão D-e) 1 PDF de visão executiva por painel | os CSVs de exceção de `data/quality/` — são material de trabalho do BI/Comercial, não dos heads |

Motivo: o painel já embute **só agregado** (linha transacional nunca chega ao
HTML). Publicar a pasta completa exporia a base por cliente e o código sem
necessidade.

## 2. Estrutura sugerida na biblioteca

```
Painéis Comerciais/                    (biblioteca ou pasta dedicada no site do Comercial)
├── Gerencial/
│   └── Dashboard_Gerencial_Canais.html
├── Distribuição/
│   └── Scorecard_Distribuição.html
├── Atacado/
│   └── Scorecard_Atacado.html
├── KAR/
│   └── Scorecard_KAR.html
├── KAN/
│   └── Scorecard_KAN.html
└── _historico/                        (opcional: 1 cópia datada por mês fechado)
```

Permissões — ver decisão **D-b** (quem vê o quê é escolha sua, não técnica).

## 3. Fluxo de atualização diária depois da migração

```
extração do BI ──► bases\Sell In\ ──► run_pipeline.py ──► run_dashboard.py ──► cópia para
   (diária)         (substituir           (~20 s)             (~1 s)          Painéis Comerciais\Gerencial\
                     o mês corrente)                                          (pasta sincronizada — o OneDrive sobe sozinho)
```

* **Onde roda:** na máquina de quem operar — o pipeline é Python local, sem
  servidor (5 dependências, todas já instaladas). *Quem* roda e *como* dispara
  é a decisão **D-c**.
* **Como chega ao SharePoint:** a pasta de publicação fica **sincronizada** pelo
  cliente OneDrive; copiar o HTML para ela publica. A cópia pode ser manual,
  por um `.bat` de um clique, ou por um `publicar.py` com trava (decisão
  **D-d**). Detalhe prático já vivido neste projeto: o OneDrive segura arquivos
  durante a sincronização — a cópia deve **gravar em nome temporário e
  renomear**, nunca sobrescrever direto.
* Os Scorecards de canal seguem o ciclo do projeto vizinho (mensal, com
  `publicar.py` próprio, ensaio e pasta de referência de aceite); a mudança
  para eles é apenas **apontar a publicação** para a nova biblioteca.

## 4. Limitações conhecidas e alternativas

| # | Limitação | O que causa | Alternativas |
|---|---|---|---|
| L1 | **SharePoint Online não renderiza `.html` no navegador** — clicar num `.html` na biblioteca **baixa** o arquivo em vez de abrir a página | política padrão do SPO moderno (bloqueio de script em conteúdo de biblioteca) | (a) o head **sincroniza** a pasta e abre por duplo clique no Explorer — é exatamente o modo de uso atual dos Scorecards; (b) abrir o arquivo baixado (funciona, mas vira cópia local desatualizada); (c) renomear para `.aspx` **exige** TI habilitar *custom scripts* no site — decisão D-a |
| L2 | Painéis de 5–17 MB | tamanho dos dados embutidos | irrelevante para sync/download; só pesa na opção `.aspx` via navegador. Reduzível cortando `dashboard.top_bandeiras` (300→200 poupa ~0,8 MB) se um dia precisar |
| L3 | Link enviado por Teams/e-mail abre o **visualizador** do SharePoint, que não executa o painel | mesmo motivo de L1 | instruir uma vez: "sincronize a pasta e abra pelo Explorer"; ou decidir por PDF para quem só quer olhar (D-e) |
| L4 | Atualização diária depende de uma máquina ligada com Python | não há servidor no desenho atual | conviver (é 1 min/dia); agendador do Windows; ou transferir a execução ao BI/TI — decisão D-c |
| L5 | Painel aberto é uma **foto** do momento da última geração | dados embutidos por construção (é o que permite abrir offline) | o rodapé já declara data/hora e execução; o ciclo diário resolve o resto |

## 5. Decisões em aberto — para o Douglas

### D-a · Como o head ABRE o painel

| Opção | Prós | Contras | Esforço |
|---|---|---|---|
| **A. Pasta sincronizada + duplo clique** (modo atual dos Scorecards) | zero mudança nos painéis; interatividade completa; funciona offline; sem TI | primeiro acesso exige "Sincronizar" uma vez; clicar pelo site baixa em vez de abrir (L1) | **baixo** — criar a biblioteca e um guia de 3 linhas |
| B. Renomear para `.aspx` (abre dentro do site) | link clicável direto no navegador | depende de TI habilitar *custom scripts* (política de segurança que muitas TIs negam); arquivos grandes no viewer; a cada publicação renomear | médio + **dependência de TI** |
| C. Hospedagem web interna (IIS / Azure Static) | URL de verdade, sem sync | novo ambiente para pedir, manter e proteger; sai do SharePoint | alto + TI |

### D-b · Permissões — quem vê o quê

| Opção | Prós | Contras | Esforço |
|---|---|---|---|
| **A. Uma permissão só**: todos os heads veem as 5 pastas | simples de manter; o Gerencial é multi-canal por natureza | cada head vê o scorecard dos outros canais | baixo |
| B. Pasta por canal com permissão própria; Gerencial só para a diretoria | cada um só o seu | quebra de herança de permissão = manutenção manual a cada mudança de head (e houve: posição 2600 vaga) | médio |
| C. Híbrido: scorecards por canal restritos + Gerencial aberto aos 4 heads | equilíbrio | duas regras para lembrar | médio |

### D-c · Quem roda a atualização diária do Sell In

| Opção | Prós | Contras | Esforço |
|---|---|---|---|
| **A. Você, manualmente** (2 comandos + troca de arquivo, ~1 min) | controle total; o passo "conferir qualidade" é humano de propósito | depende de você todo dia | zero |
| B. Agendador de Tarefas do Windows na sua máquina (um `.bat`: pipeline → dashboard → cópia) | roda sozinho; o pipeline já aborta sozinho em dado ruim | máquina precisa estar ligada; troca de senha derruba a tarefa; a conferência do relatório vira disciplina, não etapa | baixo (1 `.bat` + agendamento) |
| C. Transferir para BI/TI num servidor | sai da sua máquina | precisa Python + acesso às bases + alguém que assuma; o projeto foi desenhado para não depender de servidor | alto |

### D-d · Publicação com ou sem trava

| Opção | Prós | Contras | Esforço |
|---|---|---|---|
| A. Copiar o HTML direto para a pasta publicada | simples | um painel gerado com dado ruim que passou despercebido vai direto aos heads | zero |
| **B. `publicar.py` com ensaio** (mesmo desenho dos Scorecards: valida o exit do pipeline + confere o rodapé + grava em nome temporário e renomeia; `--publicar` confirma) | publicar continua **ato humano deliberado**; resolve o lock do OneDrive (já vivido) | um passo a mais no dia | baixo (script de ~1 h, espelhado no `publicar.py` existente) |

### D-e · PDF executivo além do HTML?

| Opção | Prós | Contras | Esforço |
|---|---|---|---|
| **A. Não — só HTML** | um artefato só; o painel já cobre | quem só quer "ver o número" precisa abrir o painel | zero |
| B. Gerar 1 PDF da Visão Geral por publicação | abre em qualquer lugar, inclusive celular no corredor | é foto: sem filtro, sem drill, sem export; mais um passo no pipeline | médio (impressão automatizada do HTML) |

> Minha leitura, sem decidir por você: **A + A + A + B + A** é o caminho de
> menor atrito que preserva tudo o que foi construído — e nenhuma dessas
> escolhas tranca a porta para mudar depois. Mas as cinco são suas.

## 6. Checklist de migração (quando as decisões saírem)

1. Criar a biblioteca/pasta `Painéis Comerciais` no site do Comercial (D-b).
2. Sincronizar a pasta na máquina de quem publica.
3. (Se D-d = B) criar o `publicar.py` deste projeto espelhado no dos Scorecards.
4. Publicar os 5 painéis atuais; validar com um head piloto o fluxo
   "sincronizar → duplo clique" (D-a).
5. Apontar o `publicar.py` dos Scorecards para a nova biblioteca.
6. Guia de 3 linhas para os heads (como sincronizar uma vez e abrir).
7. (Se D-c = B) criar e agendar o `.bat` diário; combinar quem olha o
   relatório de qualidade.
