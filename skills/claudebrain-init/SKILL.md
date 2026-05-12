---
name: claudebrain-init
description: "Bootstrap interativo do ClaudeBrain vault. Cria vault Obsidian, instala plugins pinados, integra projetos com graphify-out, configura iCloud sync. Cada fase pergunta antes de aplicar. Idempotente."
trigger: /claudebrain-init
---

# /claudebrain-init

Bootstrap conversacional do ClaudeBrain. NAO ha install.sh — voce (agente) guia o usuario por 8 fases, pergunta antes de cada uma, aplica so o aprovado.

## Usage

```
/claudebrain-init              # full setup, pergunta antes de cada fase
/claudebrain-init --dry-run    # mostra o que faria, nao escreve nada
/claudebrain-init --only 1,3,4 # roda so as fases listadas (uteis pra re-run)
```

## Filosofia

- **Idempotente**: cada fase checa estado antes de agir; rodar 2x e seguro.
- **Granular**: usuario pode pular qualquer fase, escolher subconjunto de projetos.
- **Honest**: se algo nao pode ser automatizado (toggle UI, "Trust author" do Obsidian), avise explicitamente.

## What you MUST do when invoked

### Step 0 — Resolve repo path

Leia `~/.claude/skills/claudebrain-init/.repo-path`. Esse arquivo contem o path absoluto do clone do repo `claude-brain`. Guarde como `$REPO`.

Se nao existir, pare e diga ao usuario:
> Arquivo `.repo-path` nao encontrado. Voce instalou o skill? Rode `bash scripts/install-skill.sh` dentro do clone do repo.

### Step 1 — Parse args

Argumentos validos (todos opcionais):
- `--dry-run` — passar pra todos os sub-scripts; nada escrito em disco.
- `--only <lista>` — comma-separated phase numbers (1,2,3...). Default: todas (1..8).

Se houver argumento que voce nao reconheca, pergunte ao usuario antes de continuar.

### Step 2 — Detect state

Rode:
```bash
python3 "$REPO/scripts/init/detect_state.py" --repo-root "$REPO"
```

Parse o JSON. Imprima um resumo conciso pro usuario (3-5 linhas), tipo:
```
Vault: existe em <path> (Index.md presente)
Projetos: 12 em ~/PROJETOS — 8 com graphify-out, 6 ja integrados ao vault
iCloud: <path> acessivel
Plugins: 6/6 instalados nas versoes pinadas
```

Se o vault NAO existe, isso e setup inicial. Se ja existe, e re-run/manutencao. Adapte o tom.

### Step 3 — Executar fases

Use `AskUserQuestion` antes de cada fase. Pule fases que `state` ja indica como completas, MAS confirme com o usuario antes de pular ("Vault ja existe e tem Index.md — pular Fase 1?").

Pra cada fase nao incluida em `--only`, pule silenciosamente.

---

## Phase 1 — Vault skeleton

**Quando pular**: se `state.vault.exists` E `state.vault.has_index_md` E `state.vault.has_capturar_md` E `state.vault.has_templates`.

**Pergunta**: "Criar/preencher o vault Obsidian em `<vault_path>`? (path custom?)"

Aplicar (substituindo `$VAULT` pelo escolhido):
```bash
mkdir -p "$VAULT"
cp -rn "$REPO/vault/." "$VAULT/"
```

Use `cp -rn` (no-clobber) pra nao sobrescrever arquivos existentes.

---

## Phase 2 — Plugins do Obsidian

**Pergunta multi-select** (default = required only):
- [x] Plugins obrigatorios (Dataview, Templater, Modal Forms, Buttons, Shell Commands)
- [ ] Meld Encrypt (opcional, criptografa trechos sensiveis)

Rode:
```bash
python3 "$REPO/scripts/init/install_plugins.py" \
    --repo-root "$REPO" \
    --vault "$VAULT" \
    [--include-optional] \
    [--dry-run]
```

Mostre o output cru pro usuario — o script ja imprime status linha-a-linha.

**Importante**: depois de rodar, AVISE explicitamente:
> Na primeira vez que voce abrir o vault no Obsidian, ele vai pedir "Trust author" pros plugins da comunidade. Isso e seguranca do Obsidian e nao pode ser automatizado. Um click, vale pro vault inteiro.

---

## Phase 3 — Integrar projetos

**Pre-condicao**: voce tem em `state.projects` a lista de projetos e quais tem `graphify-out`.

**Pergunta multi-select**: "Quais projetos integrar ao vault?"
- Para projetos COM `graphify-out`: opcao normal.
- Para projetos SEM: opcao tambem aparece, mas com label `(precisa rodar /graphify primeiro)`.

Se o usuario marcar um sem graphify-out, AVISE e ofereca duas opcoes:
1. Rodar `/graphify <path>` agora (voce pode invocar o skill graphify diretamente).
2. Pular esse projeto, integrar depois.

Pra cada projeto aprovado COM graphify-out:
```bash
bash "$REPO/scripts/init/integrate_project.sh" \
    "$NAME" "$PROJETOS_ROOT" "$VAULT" "$REPO" \
    [--dry-run]
```

Mantenha lista dos integrados — Fase 4 precisa dela.

---

## Phase 4 — Modal Forms dropdown

**Pergunta**: "Adicionar os <N> projetos integrados ao dropdown do form de captura? [s/n]"

Se sim:
```bash
python3 "$REPO/scripts/init/inject_modalforms_projects.py" \
    --vault "$VAULT" \
    --projects "Projeto1,Projeto2,..." \
    [--dry-run]
```

A lista vem da Fase 3.

---

## Phase 5 — claudebrain-update.sh

**Pergunta**: "Instalar `claudebrain-update.sh` em `~/.local/bin/`? (Permite detectar projetos novos e re-graphificar via botao no Index)"

Se sim — usar **symlink** (nao cp) pra que git pulls no repo propaguem direto:
```bash
mkdir -p "$HOME/.local/bin"
ln -sfn "$REPO/scripts/claudebrain-update.sh" "$HOME/.local/bin/claudebrain-update.sh"
chmod +x "$REPO/scripts/claudebrain-update.sh"
```

Se o usuario quer caminhos custom (`PROJETOS`, `ICLOUD`), oriente a passar via env vars (o script ja respeita `${PROJETOS:-...}` etc) — nao editar o script in-place.

Cheque que `~/.local/bin` esta no `$PATH` do usuario. Se nao, avise.

---

## Phase 6 — iCloud sync (opcional)

**Pre-condicao**: `state.icloud.exists`. Se nao, AVISE que o usuario precisa ter iCloud Drive ativo e a app Obsidian instalada (que cria o diretorio). Pule a fase.

**Pergunta multi-select**: "Habilitar sync mobile pra quais projetos integrados?"
Defaults = todos os integrados na Fase 3.

Pra cada projeto:
```bash
bash "$REPO/scripts/init/setup_icloud_sync.sh" \
    "$NAME" "$PROJETOS_ROOT" "$ICLOUD_DIR" \
    [--dry-run]
```

---

## Phase 7 — CSS snippet (manual — nao automatizavel)

NAO ha como automatizar. Imprima exatamente:

```
Para habilitar o visual Notion-like (`brain-hub`):

1. Abra o vault no Obsidian
2. Settings -> Aparencia -> CSS snippets
3. Ative o toggle "brain-hub"

(O arquivo brain-hub.css ja esta em .obsidian/snippets/, voce so precisa do toggle.)
```

Tambem mencione:
> Settings -> Community Plugins -> Trust author (na primeira vez)
> Settings -> Plugin options -> Dataview -> habilita "Enable JavaScript Queries" e "Enable Inline JavaScript Queries"

### Phase 8 — Verificacao

Imprima o checklist:
```
Setup completo. Verifique:

1. Abra Index.md no Obsidian
   - Voce deve ver: KPI strip, botoes "Nova captura" e "Atualizar tudo",
     tabs "Projetos" e "Notas Pendentes", tabela com projetos coloridos.

2. Se nao ver:
   - Confira que CSS snippet "brain-hub" esta ativo (Phase 7)
   - Confira que DataviewJS esta ativo (Dataview settings)
   - Confira que cssclasses: [brain-hub] esta no frontmatter do Index.md

3. Teste a captura:
   - Cmd+P -> "Templater: Captura"
   - Deve abrir form com seus projetos no dropdown
```

---

## Notas pro agente executor

- **NAO use TaskCreate pra fases**: usa AskUserQuestion. As fases sao decisoes do usuario, nao TODO do agente.
- **Mantenha estado em memoria** entre fases (lista de projetos integrados, escolhas do usuario).
- **Em caso de erro num sub-script**: nao siga em frente. Mostre o erro, pergunte ao usuario se quer abortar ou continuar pulando a fase.
- **Dry-run global**: se `--dry-run` foi passado, propague pra TODOS os sub-scripts. Continue perguntando, so nao escreve.
- **`--only`**: respeite exatamente. Se `--only 3,4`, nao pergunte sobre 1,2,5,6,7,8. Mas RODE Step 2 (detect_state) sempre — voce precisa do estado pra decidir o que mostrar.
