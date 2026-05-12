#!/usr/bin/env bash
# Phase 3 of /claudebrain-init: integrate ONE project into the vault.
#
# What it does (idempotent):
#   1. Verifies <projetos>/<name>/graphify-out/obsidian exists
#   2. Creates symlink <vault>/<name> -> <projetos>/<name>/graphify-out/obsidian
#   3. Runs reorganize_vault.py on the project vault
#
# Usage:
#   integrate_project.sh <project_name> <projetos_root> <vault_dir> <repo_root> [--dry-run]
#
# Exit codes:
#   0 = ok (integrated or skipped because already integrated)
#   1 = usage error
#   2 = project has no graphify-out — caller should suggest /graphify first

set -euo pipefail

if [ $# -lt 4 ]; then
    echo "uso: $0 <project_name> <projetos_root> <vault_dir> <repo_root> [--dry-run]" >&2
    exit 1
fi

NAME="$1"
PROJETOS="$2"
VAULT="$3"
REPO="$4"
DRY_RUN=0
[ "${5:-}" = "--dry-run" ] && DRY_RUN=1

PROJ_DIR="$PROJETOS/$NAME"
GRAPHIFY_OUT="$PROJ_DIR/graphify-out/obsidian"
LINK="$VAULT/$NAME"

if [ ! -d "$PROJ_DIR" ]; then
    echo "ERRO: projeto nao existe: $PROJ_DIR" >&2
    exit 1
fi

if [ ! -d "$GRAPHIFY_OUT" ]; then
    echo "SKIP $NAME: graphify-out nao existe. Rode '/graphify $PROJ_DIR' primeiro."
    exit 2
fi

# 1. Symlink (idempotent: skip if already pointing to the right place)
if [ -L "$LINK" ]; then
    EXISTING="$(readlink "$LINK")"
    if [ "$EXISTING" = "$GRAPHIFY_OUT" ]; then
        echo "OK   $NAME: symlink ja existe ($LINK)"
    else
        echo "WARN $NAME: symlink existe mas aponta pra $EXISTING (esperado $GRAPHIFY_OUT)"
        if [ "$DRY_RUN" -eq 0 ]; then
            ln -sfn "$GRAPHIFY_OUT" "$LINK"
            echo "     atualizado"
        fi
    fi
elif [ -d "$LINK" ]; then
    echo "WARN $NAME: $LINK existe como diretorio normal (nao symlink) — nao tocando"
else
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "DRY  $NAME: criaria $LINK -> $GRAPHIFY_OUT"
    else
        ln -sfn "$GRAPHIFY_OUT" "$LINK"
        echo "NEW  $NAME: $LINK -> $GRAPHIFY_OUT"
    fi
fi

# 2. Reorganize the project vault (mirror code tree)
if [ "$DRY_RUN" -eq 1 ]; then
    echo "DRY  $NAME: rodaria reorganize_vault.py $GRAPHIFY_OUT"
else
    python3 "$REPO/scripts/reorganize_vault.py" "$GRAPHIFY_OUT" >/dev/null 2>&1 || {
        echo "WARN $NAME: reorganize_vault.py falhou (pode ja estar reorganizado)"
    }
    echo "     reorganize_vault.py ok"
fi
