#!/usr/bin/env bash
# Installs the /project-new skill into ~/.claude/skills/.
#
# Usage: bash scripts/install-project-new.sh
#
# What it does:
#   1. Symlinks <repo>/skills/project-new/SKILL.md -> ~/.claude/skills/project-new/SKILL.md
#   2. Writes <repo> absolute path into ~/.claude/skills/project-new/.repo-path
#      (the skill reads this to find scripts/project-new/ helpers)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_SRC="$REPO_ROOT/skills/project-new/SKILL.md"
SKILL_DST_DIR="$HOME/.claude/skills/project-new"
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
echo "OK Skill /project-new instalado."
echo "   Skill:     $SKILL_DST -> $SKILL_SRC"
echo "   Repo path: $REPO_PATH_FILE ($REPO_ROOT)"
