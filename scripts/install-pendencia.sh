#!/usr/bin/env bash
# Installs the /pendencia skill into ~/.claude/skills/.
#
# Usage: bash scripts/install-pendencia.sh
#
# What it does:
#   1. Symlinks <repo>/skills/pendencia/SKILL.md -> ~/.claude/skills/pendencia/SKILL.md
#   2. Writes <repo> absolute path into ~/.claude/skills/pendencia/.repo-path
#      (the skill reads this to find scripts/pendencia/ helpers)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_SRC="$REPO_ROOT/skills/pendencia/SKILL.md"
SKILL_DST_DIR="$HOME/.claude/skills/pendencia"
SKILL_DST="$SKILL_DST_DIR/SKILL.md"
REPO_PATH_FILE="$SKILL_DST_DIR/.repo-path"

if [ ! -f "$SKILL_SRC" ]; then
    echo "ERRO: SKILL.md nao encontrado em $SKILL_SRC" >&2
    exit 1
fi

mkdir -p "$SKILL_DST_DIR"

if [ -e "$SKILL_DST" ] || [ -L "$SKILL_DST" ]; then
    if [ -d "$SKILL_DST" ] && [ ! -L "$SKILL_DST" ]; then
        echo "ERRO: $SKILL_DST e diretorio real (nao symlink). Remova manualmente." >&2
        exit 1
    fi
    echo "Removendo install anterior: $SKILL_DST"
    rm -f "$SKILL_DST"
fi

ln -s "$SKILL_SRC" "$SKILL_DST"
echo "$REPO_ROOT" > "$REPO_PATH_FILE"

echo
echo "OK Skill /pendencia instalado."
echo "   Skill:     $SKILL_DST -> $SKILL_SRC"
echo "   Repo path: $REPO_PATH_FILE ($REPO_ROOT)"
