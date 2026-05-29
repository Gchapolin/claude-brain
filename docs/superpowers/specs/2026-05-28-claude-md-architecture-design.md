---
title: Arquitetura de memoria/contexto via CLAUDE.md por projeto
date: 2026-05-28
status: draft
tags: [design, memory, claude-md, context]
---

# Arquitetura de memoria/contexto via CLAUDE.md por projeto

## Contexto

Hoje a info "estavel sobre o projeto" pode morar em 5 lugares com papeis sobrepostos:

- `~/.claude/CLAUDE.md` (global, auto-carregado)
- `~/.claude/projects/<encoded>/memory/MEMORY.md` (auto-carregado pelo harness)
- `~/.claude/projects/<encoded>/memory/*.md` (carregado on-demand)
- `<projeto>/notes/Geral/*.md` (humano le no Obsidian; Claude so quando vai buscar)
- `<projeto>/notes/Pendencias/` (cascata; mistura acionavel com contexto)

Consequencias:

- Decidir "onde colocar isso?" gera trava — 4 tipos diferentes de conteudo (operacional / arquitetural / convencao / estado) sem regra clara de roteamento.
- Claude comeca sessao em projeto novo sem CONTEXTO ESPECIFICO do projeto. So 46 linhas de regras globais + MEMORY.md (que so tem sessoes).
- Alavanca obvia subutilizada: o Claude Code **auto-carrega `<projeto>/CLAUDE.md`** quando CWD esta no projeto. Nenhum projeto do usuario usa isso.
- `notes/Geral/` e `memory/` competem pelo mesmo papel ("conhecimento estavel"), com consumidores diferentes.

## Objetivo

Eliminar a duvida "onde colocar?" definindo 4 papeis ortogonais (sem sobreposicao) e usando `<projeto>/CLAUDE.md` como porta de entrada auto-carregada. Comecar pelo claude-brain como piloto antes de rollout.

## Nao-objetivo

- Rollout pra todos os projetos. So claude-brain nesta fase.
- Skill nova de manutencao automatica. A regra e clara o suficiente pra ser seguida manualmente.
- Mexer em `~/.claude/CLAUDE.md` (regras globais). Continua como esta.
- Mexer em estruturas existentes do vault (`_root/`, `_communities/`, mirror). Intactos.
- Migracao preventiva de conteudo pra `notes/Geral/`. So criar conforme demanda real.

## Arquitetura

### 4 papeis, sem overlap

| Lugar | Papel | Auto-carrega? | Quem le |
|---|---|---|---|
| `~/.claude/CLAUDE.md` | Convencoes que valem pra TODO projeto do usuario | Sempre | Claude |
| `<projeto>/CLAUDE.md` | Convencoes do projeto + indice + decisao "onde poe?" | Sim (CWD=projeto) | Claude |
| `<projeto>/notes/Geral/` | Conhecimento operacional estavel (comandos, decisoes, URLs, secrets refs) | Nao | Voce no Obsidian + Claude on-demand |
| `<projeto>/notes/Pendencias/<slug>/` | Cascata da v1 (spec/task/tests/resultado) | Nao | Voce + Claude |
| `~/.claude/projects/<enc>/memory/` | So `session_*.md` (gerado por /save-session) + `feedback_*.md` cross-projeto | MEMORY.md sim | Claude |

### Regra de roteamento (embutida no CLAUDE.md do projeto)

```
Esse conteudo e...
  comando / URL / receita que vou consultar de novo  -> notes/Geral/<topico>.md
  decisao arquitetural com 'por que'                 -> notes/Geral/decisoes/<topico>.md
  convencao de como Claude deve agir AQUI            -> CLAUDE.md (este arquivo)
  convencao que vale pra TODO projeto meu            -> ~/.claude/CLAUDE.md (global)
  TODO acionavel                                     -> notes/Pendencias/<slug>/spec.md
  estado temporario que muda em dias                 -> notes/Pendencias/<slug>/spec.md
  resumo do que aconteceu nesta sessao               -> /save-session (gera nos 2 lugares)
```

### Estrutura do `<projeto>/CLAUDE.md`

Maximo ~80 linhas. Secoes obrigatorias:

1. **Titulo + 1-2 frases**: o que e o projeto.
2. **Onde achar contexto**: ordem de leitura (este CLAUDE.md primeiro, depois notes/Geral, notes/Pendencias, notes/Sessoes, README).
3. **Convencoes deste projeto**: 3-7 bullets. So o que e ESPECIFICO; nao repetir regras globais.
4. **Onde colocar coisa nova**: a tabela de decisao acima inline.
5. **Pontos sensiveis**: arquivos/areas que exigem cuidado extra (frageis, idempotencia, validacoes especificas).
6. **Comandos uteis**: 3-5 comandos do dia-a-dia. Nao reproduzir tudo do README.

Secoes opcionais:

- **Foco atual**: 1 frase sobre o que esta sendo trabalhado agora (atualizada quando muda).
- **Anti-padroes**: o que NAO fazer aqui (ex: nao mexer em arquivo X sem perguntar).

NAO repetir o README. README e pra publico externo; CLAUDE.md e operacional pra Claude/voce.

### Migracao de conteudos atuais (claude-brain)

| De | Pra | Acao |
|---|---|---|
| `memory/feedback_no_accents.md` | Continua em `memory/` (vale cross-projeto) | Nao mexer |
| `memory/session_*.md` | Continua em `memory/` (gerado por /save-session) | Nao mexer |
| `memory/MEMORY.md` | Continua em `memory/`, mas com pointer pro CLAUDE.md do projeto | Adicionar linha de pointer; resto inalterado |
| (sem CLAUDE.md no repo) | `<repo>/CLAUDE.md` novo | Criar com template |
| (notes/Geral/ vazia hoje) | (continua vazia) | Criar arquivos so quando aparecer necessidade real, nao preventivamente |

### `MEMORY.md` apos a mudanca

```markdown
## Contexto do projeto
- [CLAUDE.md do projeto](../../../../PROJETOS/claude-brain/CLAUDE.md) — convencoes e indice (tambem auto-carregado quando CWD=claude-brain)

## Sessoes recentes
- [Sessao 2026-05-12 02:40](session_2026-05-12-0240.md) — ...
- [Sessao 2026-05-12 00:43](session_2026-05-12-0043.md) — ...

## Feedback / convencoes
- [Escrever sem acentos neste projeto](feedback_no_accents.md) — ...
```

A linha de pointer pro CLAUDE.md e redundante quando voce esta CWD=claude-brain (porque Claude Code ja vai auto-carregar). Mas tambem ajuda quando voce abre Claude em outro CWD e referencia claude-brain.

## Impacto pratico

**Hoje:** Abro Claude num projeto, contexto auto-loaded = global CLAUDE.md (46 linhas) + RTK.md (29) + MEMORY.md (7) = ~80 linhas, zero info especifica do projeto.

**Depois:** Mesmo + `claude-brain/CLAUDE.md` (~80 linhas) = ja sei convencoes do projeto, onde olhar pra mais detalhe, e regra clara de onde adicionar info nova. Overhead: 1 arquivo, ~80 linhas auto-loaded.

## Riscos

1. **CLAUDE.md desatualiza com o tempo.** Mitigacao: regra explicita no proprio arquivo "se voce notar que esta desatualizado, atualize antes de seguir". E voce pode acionar `/save-session` ao fim de sessoes grandes — eu (Claude) atualizo se notar drift.
2. **Tentacao de inchar o CLAUDE.md.** Mitigacao: limite informal de ~80 linhas. Conteudo profundo vai pra `notes/Geral/`.
3. **Duplicacao com README.md.** Mitigacao: regra explicita "CLAUDE.md nao repete README". README e publico; CLAUDE.md e operacional.
4. **Piloto so em claude-brain pode nao capturar problemas de outros stacks.** Mitigacao: aceito; rollout pra projetos diversos vem depois se piloto funcionar.

## Entregaveis

1. `claude-brain/CLAUDE.md` (~60-80 linhas).
2. `memory/MEMORY.md` atualizado com pointer pro CLAUDE.md.
3. Spec commitada (este arquivo).
4. Sem mudancas em codigo ou outros arquivos.

## Decisoes adiadas

- Rollout pros outros 30 projetos (decidir apos 1-2 semanas usando o piloto).
- Skill `/claude-md-init` pra auto-bootstrap de outros projetos (so se rollout for aprovado).
- Auto-deteccao de drift entre CLAUDE.md e estado real do repo.
- Integracao com graphify pra graph-aware "onde colocar?".
