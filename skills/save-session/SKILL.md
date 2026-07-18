---
name: save-session
description: "Salva resumo estruturado da sessao atual do Claude Code em dois lugares: notes/Sessoes/ do projeto (visivel no vault Obsidian) e memory/ do projeto (auto-carregado no inicio de sessoes futuras). Depois atualiza o grafo graphify do projeto (update incremental + export obsidian + hub). Inline, sem chamar API."
trigger: /save-session
---

# /save-session

Gera um resumo estruturado da CONVERSA ATUAL e salva em dois lugares:
1. **Vault Obsidian**: `<projetos>/<projeto>/notes/Sessoes/<timestamp>.md` — visivel no Obsidian, indexado por graphify, espelhado pro iCloud
2. **Memory do projeto**: `~/.claude/projects/<encoded-cwd>/memory/session_<timestamp>.md` — auto-carregado pelo harness no inicio da proxima sessao via `MEMORY.md`

Depois de salvar, atualiza o grafo graphify do projeto (Step 4) pra que a sessao recem-salva e qualquer arquivo alterado entrem no grafo e no vault imediatamente.

Voce (Claude) e quem escreve. Use o que esta no contexto desta conversa — nao chame API externa, nao tente reler transcript do disco.

## Usage

```
/save-session                  # salva sessao corrente nos dois lugares + atualiza graphify
/save-session --note "X"       # adiciona observacao livre no rodape do resumo
/save-session --no-graph       # salva sem atualizar o grafo (save rapido)
/save-session --dry-run        # mostra o markdown que escreveria, sem salvar nem atualizar grafo
```

## What you MUST do when invoked

### Step 1 — Resolver paths

1. `CWD = $(pwd)` — o diretorio atual de trabalho
2. `PROJECT = basename(CWD)` se CWD for `~/PROJETOS/<algo>/...`; se nao, pergunte ao usuario qual projeto associar (ou aceite `--project <nome>`)
3. `TIMESTAMP = $(date +%Y-%m-%d-%H%M)` (ex: `2026-05-12-1430`)
4. `PROJETOS_ROOT` = primeiro componente que termina em `PROJETOS/` no CWD (default `~/PROJETOS`)
5. **Sessoes path** — Sessoes/ idealmente vive no iCloud (pra sync mobile + visibilidade no Obsidian vault):
   - Se `$PROJETOS_ROOT/$PROJECT/notes/Sessoes` ja existir como symlink, use o target dele (`readlink`).
   - Senao, se `$ICLOUD/$PROJECT/` existir (iCloud sync ja configurado), crie a pasta `$ICLOUD/$PROJECT/Sessoes/` e o symlink `notes/Sessoes -> $ICLOUD/$PROJECT/Sessoes`. Onde `$ICLOUD = ~/Library/Mobile Documents/iCloud~md~obsidian/Documents/ClaudeBrain-Mobile`.
   - Senao (projeto sem iCloud sync), apenas crie `$PROJETOS_ROOT/$PROJECT/notes/Sessoes/` local e avise o usuario que mobile nao vera essas sessoes ate ele rodar `/claudebrain-init` na Fase 6.
6. `VAULT_FILE = <sessoes-resolvido>/$TIMESTAMP.md`
7. Memory dir: `MEMORY_DIR = ~/.claude/projects/<encoded-cwd>/memory/` onde `<encoded-cwd>` substitui `/` por `-` no path (ja existe se voce usa Claude Code nesse projeto)
8. `MEMORY_FILE = $MEMORY_DIR/session_$TIMESTAMP.md`

### Step 2 — Sintetizar o resumo

Escreva um markdown com este formato exato (frontmatter + secoes):

```markdown
---
type: session-summary
project: <PROJECT>
session_date: YYYY-MM-DD
session_time: HH:MM
cwd: <CWD absoluto>
files_changed: [lista de paths relativos ao CWD que voce editou/criou nesta sessao]
commits: [shas de commits que voce criou nesta sessao, se houver]
tags: [sessao, <PROJECT>]
---

# Sessao YYYY-MM-DD HH:MM — <PROJECT>

## Intent
Resumo em 1-2 frases do que o usuario pediu (derive do primeiro prompt ou da intencao dominante da conversa).

## Done
- bullet 1 do que foi completado
- bullet 2
...

## Deferred
- TODO ou follow-up nao implementado
- (se nao houver, escreva: "Nada pendente.")

## Decisions
- escolha tecnica + breve justificativa
- (se nao houver, escreva: "Nenhuma decisao significativa.")

## Files
- `path/to/file.py` — motivo curto (criado, refatorado, fix do bug X, etc.)
- ...

## Open
- pergunta ou ponto que ficou em aberto
- (se nao houver, escreva: "Nada em aberto.")

<!-- se --note "X" foi passado, adicionar abaixo: -->
## Nota
X
```

### Step 3 — Escrever nos dois lugares

Crie os diretorios se nao existirem (`mkdir -p`).

1. Escrever VAULT_FILE com o markdown acima
2. Escrever MEMORY_FILE com o mesmo conteudo MAS com frontmatter ajustado pro formato de memoria:
   ```yaml
   ---
   name: Sessao YYYY-MM-DD HH:MM em <PROJECT>
   description: <copia do Intent>
   type: project
   ---
   ```
   (Mantem o body identico apos o frontmatter.)

3. Atualizar `$MEMORY_DIR/MEMORY.md`:
   - Se o arquivo nao existe, cria com header e a primeira entrada
   - Se ja existe, adiciona a entrada NO TOPO da lista (mais recente primeiro)
   - Formato da entrada: `- [Sessao YYYY-MM-DD HH:MM](session_$TIMESTAMP.md) — <Intent resumido em 1 linha>`
   - Limite: manter no maximo 20 entradas mais recentes em MEMORY.md (o harness corta apos 200 linhas; cada entrada deve caber em 1 linha curta)

### Step 4 — Atualizar o grafo graphify do projeto

Pule este step inteiro (sem erro) se: `--no-graph` ou `--dry-run` foi passado, OU `$PROJETOS_ROOT/$PROJECT/graphify-out/` nao existe (nesse caso mencione na confirmacao que vale rodar `/graphify` uma vez pra criar o grafo).

1. **Update incremental do grafo**: siga o fluxo `--update` da skill graphify (`~/.claude/skills/graphify/SKILL.md`, secao "For --update") com `INPUT_PATH = $PROJETOS_ROOT/$PROJECT`. Isso re-extrai apenas arquivos novos/alterados desde o ultimo manifest — incluindo a sessao que voce acabou de salvar — e regenera `graph.json`, `GRAPH_REPORT.md` e `graph.html`. Como a sessao e um `.md` (nao code-only), a extracao semantica via subagente roda para os arquivos novos; o resto vem do cache.
2. **Re-exportar o vault Obsidian** (as notas que o ClaudeBrain enxerga via symlink):
   ```bash
   cd "$PROJETOS_ROOT/$PROJECT" && graphify export obsidian
   ```
3. **Reorganizar e reconstruir o hub** — resolva `REPO = $(cat ~/.claude/skills/claudebrain-init/.repo-path)` (fallback `~/PROJETOS/claude-brain`; se nao existir, pule com aviso):
   ```bash
   python3 "$REPO/scripts/reorganize_vault.py" "$PROJETOS_ROOT/$PROJECT/graphify-out/obsidian"
   python3 "$REPO/scripts/build_project_hubs.py" "$PROJECT"
   ```
4. Se qualquer sub-passo falhar, NAO desfaca o save (Steps 1-3 ja estao no disco); reporte o erro na confirmacao e siga em frente.

### Step 5 — Confirmar pro usuario

Imprima:
```
Sessao salva:
  Vault:   <VAULT_FILE>
  Memory:  <MEMORY_FILE>
  Index:   $MEMORY_DIR/MEMORY.md (entrada adicionada no topo)
  Grafo:   <resultado do Step 4 — ex: "atualizado (N nos, M arestas, hub re-gerado)",
            "pulado (--no-graph)", "pulado (sem graphify-out/)" ou o erro ocorrido>
```

### Step 6 — Dry-run

Se `--dry-run` foi passado, NAO escreva nada e NAO atualize o grafo. So mostre o markdown que escreveria + os 3 paths de destino.

## Notas pro agente executor

- **NUNCA chame API externa pra gerar o resumo**. Voce TEM o contexto da conversa, use-o.
- **Honest sobre o que esta no contexto**: se a sessao foi tao longa que o inicio foi comprimido, mencione na secao Intent: "(inicio da sessao comprimido do contexto)".
- **Files changed deve ser concreto**: liste APENAS arquivos que voce realmente editou nesta sessao (use git status como verificacao quando em duvida). Nao invente.
- **Se CWD nao parecer ser um projeto** (ex: ~/Downloads): pergunte ao usuario qual projeto associar antes de salvar.
- **Encoded-cwd format**: o harness usa `~/.claude/projects/<cwd-with-slashes-replaced-by-hifens>/`. Exemplo: `/Users/foo/PROJETOS/claude-brain` -> `-Users-foo-PROJETOS-claude-brain`.
- **Idempotente em re-runs proximos**: se voce rodar `/save-session` 2x no mesmo minuto, o segundo overwrite-ria o primeiro (mesmo timestamp em minutos). Se for um problema, adicione `-2` ao timestamp.
- **Custo do Step 4**: o update incremental so re-extrai arquivos novos/alterados (normalmente a propria sessao + o que mudou na conversa) — custo pequeno de LLM e ~1-3 min. Se o usuario quiser o save instantaneo, e so passar `--no-graph`.
- **Symlinks no detect**: `notes/Sessoes` pode ser symlink pro iCloud. Se o detect do graphify nao seguir o symlink e a sessao nao aparecer entre os arquivos novos do update, mencione isso na confirmacao em vez de silenciar.
