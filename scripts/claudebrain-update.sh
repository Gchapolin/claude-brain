#!/usr/bin/env bash
# ClaudeBrain — Atualizar tudo
#
# - Detecta projetos novos em $PROJETOS e adiciona ao vault
# - Roda 'graphify update' nos projetos existentes pra atualizar AST
# - Atualiza dropdown do Modal Forms (incremental: so adiciona, nao remove)
#
# Env overrides:
#   PROJETOS  (default: $HOME/PROJETOS)
#   ICLOUD    (default: $HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/ClaudeBrain-Mobile)
#   MAC_VAULT (default: $PROJETOS/Obsidian/ClaudeBrain)
#   REPO      (default: $HOME/PROJETOS/claude-brain) — onde estao scripts/init/
#   SKIP      (default: "Obsidian claude-brain") — pastas a ignorar (separadas por espaco)

set -u

PROJETOS="${PROJETOS:-$HOME/PROJETOS}"
ICLOUD="${ICLOUD:-$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/ClaudeBrain-Mobile}"
MAC_VAULT="${MAC_VAULT:-$PROJETOS/Obsidian/ClaudeBrain}"
REPO="${REPO:-$HOME/PROJETOS/claude-brain}"
SKIP="${SKIP:-Obsidian claude-brain}"

read -r -a SKIP_PROJECTS <<< "$SKIP"

GRAPHIFY_BIN="$(command -v graphify || true)"

NEW_PROJECTS=()
UPDATED_GRAPHS=()
ERRORS=()

is_skip() {
    local p="$1"
    for skip in "${SKIP_PROJECTS[@]}"; do
        [[ "$p" == "$skip" ]] && return 0
    done
    return 1
}

# Safely ensure a notes/ subdir is a symlink to the iCloud path.
# REFUSES to delete a real directory that has content (data-loss guard).
ensure_notes_symlink() {
    local dst="$1" src="$2" name="$3"
    if [ -L "$dst" ]; then
        local existing
        existing="$(readlink "$dst")"
        if [ "$existing" = "$src" ]; then return 0; fi
        ln -sfn "$src" "$dst"
        return 0
    fi
    if [ -e "$dst" ]; then
        if [ -d "$dst" ] && [ -z "$(ls -A "$dst" 2>/dev/null)" ]; then
            rmdir "$dst"
            ln -sfn "$src" "$dst"
            return 0
        fi
        ERRORS+=("$name: $dst existe com conteudo, nao convertendo pra symlink (movera manualmente?)")
        return 1
    fi
    ln -sfn "$src" "$dst"
}

setup_new_project() {
    local name="$1"
    local d="$PROJETOS/$name"

    mkdir -p "$d/notes"
    mkdir -p "$ICLOUD/$name/Pendencias"
    mkdir -p "$ICLOUD/$name/Geral"
    mkdir -p "$ICLOUD/$name/Sessoes"

    ensure_notes_symlink "$d/notes/Pendencias" "$ICLOUD/$name/Pendencias" "$name"
    ensure_notes_symlink "$d/notes/Geral" "$ICLOUD/$name/Geral" "$name"
    ensure_notes_symlink "$d/notes/Sessoes" "$ICLOUD/$name/Sessoes" "$name"

    if [ ! -L "$MAC_VAULT/$name" ] && [ ! -e "$MAC_VAULT/$name" ]; then
        ln -sfn "$ICLOUD/$name" "$MAC_VAULT/$name"
    fi

    if [ ! -f "$ICLOUD/$name/$name.md" ]; then
        cat > "$ICLOUD/$name/$name.md" <<EOF
---
type: project-hub-mobile
project: $name
tags: [projecthub, hub]
no_graphify: true
---

# $name

Projeto detectado em \`~/PROJETOS/$name\`. Sem grafo de codigo ainda — rode \`/graphify\` no Claude Code dentro dessa pasta pra gerar.

## Pendencias

(use [[Capturar]] e seleciona projeto = $name)

## Geral

(use [[Capturar]] e seleciona projeto = $name)
EOF
    fi
    NEW_PROJECTS+=("$name")
}

# Iterate through projects
for d in "$PROJETOS"/*/; do
    [ -d "$d" ] || continue
    name=$(basename "$d")
    is_skip "$name" && continue

    has_graph=0
    [ -f "$d/graphify-out/graph.json" ] && has_graph=1

    in_vault=0
    if [ -L "$MAC_VAULT/$name" ] || [ -d "$MAC_VAULT/$name" ]; then
        in_vault=1
    fi

    if [ "$in_vault" = "0" ]; then
        setup_new_project "$name"
    elif [ "$has_graph" = "1" ] && [ -n "$GRAPHIFY_BIN" ]; then
        if (cd "$d" && "$GRAPHIFY_BIN" update . >/dev/null 2>&1); then
            UPDATED_GRAPHS+=("$name")
        else
            ERRORS+=("graphify update failed: $name")
        fi
    fi
done

# Update Modal Forms dropdown if new projects added (incremental, idempotent)
if [ ${#NEW_PROJECTS[@]} -gt 0 ]; then
    INJECT="$REPO/scripts/init/inject_modalforms_projects.py"
    if [ ! -f "$INJECT" ]; then
        ERRORS+=("inject_modalforms_projects.py nao encontrado em $INJECT (REPO=$REPO)")
    else
        # Build JSON list to safely pass names with spaces/quotes
        PROJECTS_JSON=$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1:]))' "${NEW_PROJECTS[@]}")
        for VAULT_DIR in "$MAC_VAULT" "$ICLOUD"; do
            if [ -d "$VAULT_DIR/.obsidian/plugins/modalforms" ]; then
                python3 "$INJECT" --vault "$VAULT_DIR" --mode add --projects-json "$PROJECTS_JSON" \
                    || ERRORS+=("inject_modalforms_projects falhou em $VAULT_DIR")
            fi
        done
    fi
fi

# Print summary
echo "=== ClaudeBrain — Atualizar ==="
echo "Grafos atualizados: ${#UPDATED_GRAPHS[@]}"
[ ${#UPDATED_GRAPHS[@]} -gt 0 ] && printf '  - %s\n' "${UPDATED_GRAPHS[@]}"
echo "Projetos novos: ${#NEW_PROJECTS[@]}"
[ ${#NEW_PROJECTS[@]} -gt 0 ] && printf '  + %s\n' "${NEW_PROJECTS[@]}"
[ -z "$GRAPHIFY_BIN" ] && echo "AVISO: graphify nao esta no PATH — updates de grafo pulados"
[ ${#ERRORS[@]} -gt 0 ] && {
    echo "Erros: ${#ERRORS[@]}"
    printf '  ! %s\n' "${ERRORS[@]}"
}
echo "Done. $(date '+%H:%M:%S')"
