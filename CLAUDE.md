# claude-brain

Setup opinativo de Obsidian como segundo cerebro de desenvolvimento. Combina graphify (knowledge graph por projeto), vault Obsidian com sync iCloud, e skills Claude Code (`/claudebrain-init`, `/save-session`, `/pendencia`, `/project-new`).

## Onde achar contexto deste projeto (ordem de leitura)

1. **Este arquivo** — convencoes + decisao "onde colocar?"
2. `notes/Geral/` — conhecimento operacional (comandos, decisoes, URLs)
3. `notes/Pendencias/<slug>/` — cascata acionavel (spec/task/tests/resultado)
4. `notes/Sessoes/` — historico das sessoes (gerado por `/save-session`)
5. `README.md` — visao publica do projeto
6. `docs/superpowers/specs/`, `docs/superpowers/plans/` — historico de design

## Convencoes deste projeto

- **Sem acentos** em qualquer texto (markdown, comentarios, commits, strings de erro).
- **TDD obrigatorio** pra logica Python em `scripts/`. Test → fail → implement → pass → commit.
- Tests rodam via `python -m unittest discover tests`.
- **Stdlib only** em Python. Nao adicionar dependencias sem confirmar.
- Toda pendencia segue cascata `spec → task → tests → resultado` (ver `README.md` "Cascata de pendencias").
- Skills sao instaladas via `bash scripts/install-<nome>.sh` (symlink + `.repo-path`).
- Commits curtos no formato `tipo: descricao` (`feat:`, `fix:`, `docs:`, `refactor:`).

## Onde colocar coisa nova (decisao)

```
Esse conteudo e...
  comando / URL / receita que vou consultar de novo   -> notes/Geral/<topico>.md
  decisao arquitetural com 'por que'                  -> notes/Geral/decisoes/<topico>.md
  convencao de como Claude deve agir AQUI             -> CLAUDE.md (este arquivo)
  convencao que vale pra TODO projeto meu             -> ~/.claude/CLAUDE.md (global)
  TODO acionavel                                      -> notes/Pendencias/<slug>/spec.md
  estado temporario que muda em dias                  -> notes/Pendencias/<slug>/spec.md
  resumo do que aconteceu nesta sessao                -> /save-session (gera nos 2 lugares)
```

Se a regra for ambigua pra um caso, ajuste a tabela acima — nao improvise.

## Pontos sensiveis

- `vault/Index.md`: dataviewjs frageis. Toda mudanca valida com `node -e "...new Function('dv','app', body)..."` antes de commitar.
- `skills/*/SKILL.md`: frontmatter YAML obrigatorio. Validar com `python3 -c "import yaml; yaml.safe_load(...)"`.
- `vault/Templates/Captura.md`: bloco `<%* %>` do Templater. Validar como JS com `node -e` antes de commitar.
- `scripts/install-*.sh`: scripts idempotentes. Quebrar idempotencia = bug serio.
- `scripts/pendencia/migrate.py`: opera em arquivos do usuario. Mudancas precisam manter dry-run funcional.
- `scripts/init/detect_state.py`: usado pelo `/claudebrain-init` em sessoes interativas. Output JSON e contrato.

## Comandos uteis

```bash
python -m unittest discover tests          # roda tudo
bash scripts/install-pendencia.sh          # (re)instala skill /pendencia
bash scripts/install-project-new.sh        # (re)instala skill /project-new
bash scripts/install-skill.sh              # (re)instala /claudebrain-init
bash scripts/install-save-session.sh       # (re)instala /save-session
bash scripts/claudebrain-update.sh         # detecta projetos novos e integra
```

## Foco atual

Cascata de pendencias acabou de ser mergeada (commit `c55047f`, branch `main`). Proximo passo natural: usar a cascata em um projeto real e iterar.

## Anti-padroes

- NAO mexer em `vault/.obsidian/plugins-config/*.json.example` sem entender que vira config viva no vault apos `/claudebrain-init`.
- NAO criar arquivos `.md` soltos em `<Projeto>/Pendencias/` no vault — use a cascata (`/pendencia new`).
- NAO duplicar conteudo do `README.md` aqui. README e publico; este arquivo e operacional.
