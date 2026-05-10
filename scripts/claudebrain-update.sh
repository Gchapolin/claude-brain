#!/bin/bash
# ClaudeBrain — Atualizar tudo
# - Detecta projetos novos em ~/PROJETOS e adiciona ao vault
# - Roda 'graphify update' nos projetos existentes pra atualizar AST
# - Atualiza dropdown do Modal Forms

set -u

PROJETOS="$HOME/PROJETOS"
ICLOUD="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/ClaudeBrain-Mobile"
MAC_VAULT="$PROJETOS/Obsidian/ClaudeBrain"
GRAPHIFY_BIN="$HOME/.local/bin/graphify"
SKIP_PROJECTS=("Obsidian")  # adicione aqui pastas privadas a ignorar

NEW_PROJECTS=()
UPDATED_GRAPHS=()
SKIPPED_NEW=()
ERRORS=()

is_skip() {
    local p="$1"
    for skip in "${SKIP_PROJECTS[@]}"; do
        [[ "$p" == "$skip" ]] && return 0
    done
    return 1
}

setup_new_project() {
    local name="$1"
    local d="$PROJETOS/$name"

    mkdir -p "$d/notes"
    mkdir -p "$ICLOUD/$name/Pendencias"
    mkdir -p "$ICLOUD/$name/Geral"

    if [ ! -L "$d/notes/Pendencias" ]; then
        rm -rf "$d/notes/Pendencias" 2>/dev/null
        ln -sfn "$ICLOUD/$name/Pendencias" "$d/notes/Pendencias"
    fi
    if [ ! -L "$d/notes/Geral" ]; then
        rm -rf "$d/notes/Geral" 2>/dev/null
        ln -sfn "$ICLOUD/$name/Geral" "$d/notes/Geral"
    fi

    if [ ! -L "$MAC_VAULT/$name" ]; then
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
        # NEW project
        setup_new_project "$name"
    elif [ "$has_graph" = "1" ] && [ -x "$GRAPHIFY_BIN" ]; then
        # Existing graphified — update
        if (cd "$d" && "$GRAPHIFY_BIN" update . >/dev/null 2>&1); then
            UPDATED_GRAPHS+=("$name")
        else
            ERRORS+=("graphify update failed: $name")
        fi
    fi
done

# Update Modal Forms dropdown if new projects added
if [ ${#NEW_PROJECTS[@]} -gt 0 ]; then
    /usr/bin/env python3 - <<PYEOF
import json
new = ${NEW_PROJECTS[@]@Q}
new_projects = list("${NEW_PROJECTS[@]}".split())
for vault_data in [
    "$MAC_VAULT/.obsidian/plugins/modalforms/data.json",
    "$ICLOUD/.obsidian/plugins/modalforms/data.json"
]:
    try:
        with open(vault_data) as f: data = json.load(f)
        opts = data['formDefinitions'][0]['fields'][0]['input']['options']
        existing = {o['value'] for o in opts}
        geral_idx = next((i for i,o in enumerate(opts) if o.get('value')=='geral'), len(opts))
        added = []
        for p in new_projects:
            if p not in existing:
                opts.insert(geral_idx, {'value': p, 'label': p})
                geral_idx += 1
                added.append(p)
        with open(vault_data, 'w') as f: json.dump(data, f, indent=2)
        if added: print(f'  form atualizado ({vault_data}): +{added}')
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f'  erro form ({vault_data}): {e}')
PYEOF
fi

# Print summary
echo "=== ClaudeBrain — Atualizar ==="
echo "Grafos atualizados: ${#UPDATED_GRAPHS[@]}"
[ ${#UPDATED_GRAPHS[@]} -gt 0 ] && printf '  - %s\n' "${UPDATED_GRAPHS[@]}"
echo "Projetos novos: ${#NEW_PROJECTS[@]}"
[ ${#NEW_PROJECTS[@]} -gt 0 ] && printf '  + %s\n' "${NEW_PROJECTS[@]}"
[ ${#ERRORS[@]} -gt 0 ] && {
    echo "Erros: ${#ERRORS[@]}"
    printf '  ! %s\n' "${ERRORS[@]}"
}
echo "Done. $(date '+%H:%M:%S')"
