---
title: Cascata de pendencias + project init pelo vault
date: 2026-05-28
status: draft
tags: [design, vault, skills, workflow]
---

# Cascata de pendencias + project init pelo vault

## Contexto

Hoje no ClaudeBrain:

- `Notas Pendentes/` e a INBOX global; captura cai la com `status: pendente`.
- Triagem manual move pra `<Projeto>/Pendencias/` (acionavel) ou `<Projeto>/Geral/` (referencia).
- `<Projeto>/Pendencias/` sao notas `.md` soltas, sem estrutura interna nem ciclo de vida explicito.
- Nao existe convencao pra "pendencia em andamento" vs "pendencia realizada" — so o arquivo existir.
- Nao existe ferramenta pra iniciar um projeto novo a partir do vault.

Consequencias:

- Pendencias viram TODO lists soltas, sem rastreio do que foi feito ou como.
- Cada projeto inventa seu proprio formato de spec/task.
- Implementacao real (escrever codigo no projeto) nao tem ligacao explicita com a pendencia que motivou.
- Iniciar projeto novo exige criar pastas a mao em multiplos lugares (vault, iCloud, graphify).

## Objetivo

Padronizar o ciclo de vida de toda pendencia como uma **cascata documental de 4 estagios** (`spec → task → tests → resultado`), com automacao via skill Claude Code que orquestra a geracao de cada estagio e a implementacao TDD entre `tests.md` e `resultado.md`. Adicionar tambem um comando pra iniciar um projeto novo a partir do vault (so o lado vault; codigo vem depois).

## Nao-objetivo

- Reescrever Geral/ (continua como referencia operacional solta).
- Reescrever a estrutura espelhada do graphify (`_root/`, `_communities/`, `_misc/`, mirror de pastas) — intactos.
- Criar git init / esqueleto de codigo / CLAUDE.md template do projeto novo (project init e PURAMENTE vault; codigo vem em pendencia posterior).
- Substituir `/save-session` ou `/claudebrain-init`.

## Decisoes principais

| Variavel | Decisao | Por que |
|---|---|---|
| Lifecycle | Cascata `spec → task → tests → resultado` aplica a TODA pendencia | Padroniza pensar antes de implementar; rastreio uniforme |
| Forma no disco | `Pendencias/<slug>/{spec,task,tests,resultado}.md` (pasta por pendencia) | Cada estagio linkavel individualmente; estado por presenca de arquivos |
| Quem gera | Claude gera em cascata; usuario revisa entre estagios | Aproveita LLM, mas evita autoritarismo |
| Captura | Modal Form cria `spec.md` direto (com slug + projeto). `Notas Pendentes/` DEPRECATED | Elimina triagem manual; captura ja entra no fluxo |
| Estado | Definido por presenca de arquivos na pasta | Disco e fonte de verdade; sem frontmatter pra esquecer |
| Implementacao | Apos `tests.md`, skill dispara `superpowers:test-driven-development` no codigo real do projeto | Integra com fluxo TDD ja existente |
| Project init | Cria so o lado vault: `<Projeto>/` + hub + `Pendencias/visao-do-projeto/spec.md` | Pensa primeiro, codifica depois |
| Superficie | Uma skill `/pendencia` com subcomandos + `/project new` separada | Mental model unico; integra com botoes do Index |

## Arquitetura

### Estrutura de uma pendencia

```
<Projeto>/Pendencias/<slug>/
├── spec.md         O quê e por quê (Contexto, Problema, Criterios de aceitacao, Fora de escopo)
├── task.md         Como (Passos concretos, Dependencias, Riscos, Estimativa)
├── tests.md        O que provar (Casos de teste em linguagem natural, edge cases)
└── resultado.md    O que aconteceu (Commits, files alterados, decisoes durante implementacao, follow-ups)
```

Cada arquivo tem frontmatter padrao:

```yaml
---
type: pendencia-{spec|task|tests|resultado}
project: <Projeto>
slug: <slug>
stage: {spec|task|tests|resultado}
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

### Estado por presenca de arquivos

| Arquivos presentes | Estado |
|---|---|
| `spec.md` so | aberta |
| `spec.md + task.md` | em planejamento |
| `spec.md + task.md + tests.md` | pronta pra implementar |
| `spec.md + task.md + tests.md + resultado.md` | realizada |

Sem campo `status` em frontmatter — disco e fonte de verdade.

### Skill `/pendencia`

Instalada em `~/.claude/skills/pendencia/SKILL.md` via `scripts/install-skill.sh` (mesmo padrao das outras skills do repo). Subcomandos:

- `/pendencia new <projeto>/<slug> [--quick]`
  Cria a pasta. Pergunta intent. Gera `spec.md`. Com `--quick`, pula direto pra `resultado.md` minimo (1-line log, pra pendencias triviais).

- `/pendencia next [<slug>]`
  Le a pasta, anuncia o que vai gerar, pede confirmacao, gera. Se `<slug>` omitido, lista pendencias em andamento e pergunta qual. Comportamento por estado:
  - `spec.md` so → gera `task.md`
  - `+task.md` → gera `tests.md`
  - `+tests.md` → invoca `superpowers:test-driven-development` no codigo real do projeto, com `tests.md` como input
  - `+implementacao concluida` → gera `resultado.md` lendo `git log` recente e files alterados
  - tudo presente → "Pendencia realizada. Reabrir?"

- `/pendencia status [<projeto>]`
  Lista pendencias por estagio. Sem argumento: agrupa por projeto.

- `/pendencia migrate <projeto>`
  Detecta `.md` soltos em `<Projeto>/Pendencias/`, oferece converter cada um pra `<slug>/spec.md` preservando conteudo. Idempotente, nao destrutivo (gera diff antes de aplicar).

- `/pendencia from-geral <projeto>/<arquivo>` (opcional)
  Promove uma nota de `Geral/` pra cascata (caso voce decida que algo virou acionavel).

### Skill `/project new`

- `/project new <nome>`
  Cria `<Projeto>/` no vault com:
  - `<Projeto>.md` (hub minimo, frontmatter `type: project-hub` + `tags: [#projecthub]`)
  - `Pendencias/visao-do-projeto/spec.md` ja com perguntas guia ("Qual problema resolve?", "Quem usa?", "Como sabemos que funcionou?", "Restricoes?")
  - `Geral/` vazia
  - Sem `_root/`, `_communities/` etc (esses sao gerados pelo graphify quando o projeto ganhar codigo)
  - Sem symlink iCloud ainda (a primeira `/pendencia next` ou `/claudebrain-init` configura quando o projeto for "promovido")

Project init e separado de `/pendencia` porque sua natureza e diferente (cria estrutura, nao avanca workflow).

### Integracao com Modal Form (captura mobile)

O form atual (`vault/Templates/Captura.md`) ja pergunta projeto via dropdown. Mudancas:

1. Adicionar campo `slug` (texto livre, sugerido a partir do titulo).
2. Em vez de salvar em `Notas Pendentes/<nome>.md`, salvar em `<Projeto>/Pendencias/<slug>/spec.md`.
3. Frontmatter padrao da pendencia (em vez de `status: pendente`).
4. Se `<slug>` ja existir, sufixar com `-2`, `-3`, etc.

`Notas Pendentes/` continua existindo como pasta legada (pra migracao gradual) mas o form nao escreve la mais. Enquanto a pasta tiver conteudo, o Index mostra um banner sugerindo `/pendencia migrate` em cima das notas remanescentes. Nada e deletado automaticamente.

### Integracao com Index.md (dataviewjs)

A tab atual "Notas Pendentes" no Index e substituida por "Pendencias" com:

- KPIs: `aberta`, `planejamento`, `pronta`, `realizada` (counts globais).
- Tabela por projeto: colunas = estagios, valores = count.
- Click em celula filtra pra mostrar slugs daquela combinacao.
- Botao "Nova pendencia" abre Modal Form atualizado.

A query Dataview ganha um helper que classifica cada pasta `Pendencias/<slug>/` pelo conjunto de arquivos presentes (uso de `dv.io.load` ou checagem de `file.folder`).

### Integracao com `/claudebrain-init`

Fase nova (provavelmente Fase 9): instalar skill `/pendencia` e `/project new`. Mesmo padrao das outras (copia pra `~/.claude/skills/`, grava `.repo-path`). Idempotente.

### Integracao com `/save-session`

Sem mudanca. `/save-session` continua gerando `notes/Sessoes/<timestamp>.md` e `memory/session_<timestamp>.md`. Quando uma sessao implementa uma pendencia, o `resultado.md` daquela pendencia pode linkar a sessao via wikilink (`[[2026-05-28-1430]]`).

## Fluxo end-to-end (exemplo)

1. **Captura mobile**: usuario captura via Modal Form: projeto=`HarmonicMapApp`, slug=`oauth-apple`, conteudo="Adicionar Sign in with Apple, ja temos Google. iOS so."
   → Cria `HarmonicMapApp/Pendencias/oauth-apple/spec.md`.

2. **No Mac, refinar spec**: usuario abre Claude Code em `~/PROJETOS/HarmonicMapApp/`, roda `/pendencia next oauth-apple`.
   → Skill detecta so `spec.md`. Anuncia: "Vou gerar task.md a partir do spec. Ok?". Usuario aprova.
   → Gera `task.md` com passos (configurar Apple Developer, integrar SDK, callback, store de tokens).

3. **Revisar task**: usuario edita `task.md` direto no Obsidian. Roda `/pendencia next oauth-apple`.
   → Detecta `spec+task`. Gera `tests.md` com casos: "fluxo feliz", "cancelamento", "token expirado", "primeira vez vs login subsequente".

4. **Implementar**: roda `/pendencia next oauth-apple`.
   → Detecta `spec+task+tests`. Invoca `superpowers:test-driven-development` no codigo real, com `tests.md` como input. Escreve testes, implementa, roda. Commit.

5. **Fechar**: roda `/pendencia next oauth-apple`.
   → Detecta implementacao concluida (ha commits relacionados desde tests.md). Gera `resultado.md` listando commits, files alterados, decisoes feitas, follow-ups (ex: "ainda falta UI de unlink").

6. **Index.md** mostra `HarmonicMapApp / realizada: +1`.

## Migracao de projetos existentes

Pendencias atuais (`.md` soltos em `<Projeto>/Pendencias/`) podem ser migradas via `/pendencia migrate <projeto>`. Operacao:

1. Lista cada `.md` em `<Projeto>/Pendencias/` (nao subpastas).
2. Sugere slug (kebab-case do nome do arquivo).
3. Mostra preview do destino (`<Projeto>/Pendencias/<slug>/spec.md`).
4. Usuario aprova lote ou item-a-item.
5. Move conteudo, ajusta frontmatter, commita no git do vault (se aplicavel).

Operacao e idempotente — rodar 2x nao duplica. Notas que ja sao pastas sao ignoradas.

## Casos de falha

- **`/pendencia next` em pasta com arquivos inesperados** (ex: so `task.md` sem spec): falha com erro claro listando o que esta faltando, sugere `/pendencia new` pra recomecar.
- **`<slug>` invalido** (espacos, acentos): skill normaliza (kebab-case, sem acentos) e confirma com usuario.
- **Projeto nao existe no vault**: skill oferece criar via `/project new <projeto>`.
- **Tests.md vazio ou sem casos claros**: skill se recusa a invocar TDD e pede revisao.
- **Sem commits desde a fase de tests** ao tentar gerar `resultado.md`: skill avisa e oferece pular pra resultado manual ou abortar.

## Riscos / pontos de atrito conhecidos

1. **Slug na captura mobile**: usuario precisa pensar num identificador na hora. Mitigacao: se omitido, Claude infere na primeira `/pendencia next` no Mac (le `spec.md` e propoe slug).
2. **Pendencias triviais**: cascata e overkill pra "trocar texto do botao". Mitigacao: `/pendencia new --quick` pula direto pra `resultado.md` minimo.
3. **`/pendencia next` magico**: o "proximo passo" e inferido pelo disco. Mitigacao: skill sempre anuncia explicitamente o que vai fazer antes de fazer; usuario tem chance de abortar.
4. **Dataviewjs do Index**: ler estado de centenas de pastas pode ficar lento. Mitigacao: cache via arquivo `.pendencia-index.json` no root do vault, regerado por trigger ou no `/pendencia next`.
5. **Deprecation de `Notas Pendentes/`**: usuarios existentes podem ter coisas la nao migradas. Mitigacao: warning periodico no Index ate `Notas Pendentes/` ficar vazia; nao deletar nada automaticamente.

## Decisoes adiadas

- Como `/pendencia` lida com pendencias **cross-projeto** (ex: refatorar algo que afeta 2 projetos): por enquanto, criar uma pendencia em cada projeto manualmente.
- Notificacao mobile quando uma pendencia muda de estado: fora de escopo desta fase.
- Visualizacao Kanban no Obsidian: fora de escopo; tabela Dataview e o suficiente por enquanto.

## Estrutura final (resumo visual)

```
vault/<Projeto>/
├── <Projeto>.md
├── Pendencias/
│   ├── oauth-apple/                   (realizada)
│   │   ├── spec.md
│   │   ├── task.md
│   │   ├── tests.md
│   │   └── resultado.md
│   ├── refatorar-cache/               (em planejamento)
│   │   ├── spec.md
│   │   └── task.md
│   └── crash-android-10/              (aberta)
│       └── spec.md
├── Geral/                             (sem mudanca)
└── (resto sem mudanca)
```

## Entregaveis desta fase

1. Skill `/pendencia` em `skills/pendencia/SKILL.md` com subcomandos `new`, `next`, `status`, `migrate`, `from-geral`.
2. Skill `/project new` em `skills/project-new/SKILL.md`.
3. Atualizacao do Modal Form (`vault/Templates/Captura.md`) pra escrever em `Pendencias/<slug>/spec.md`.
4. Atualizacao do `vault/Index.md` (dataviewjs com tabela de pendencias por estagio).
5. Atualizacao do `scripts/install-skill.sh` pra instalar as 2 skills novas.
6. Fase nova em `/claudebrain-init` que instala as skills.
7. Testes Python pra logica de classificacao por presenca de arquivos e parsing de slug.
8. Documentacao no `README.md` (secao nova "Cascata de pendencias").
