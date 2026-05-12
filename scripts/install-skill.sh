#!/usr/bin/env bash
# Installs the /claudebrain-init skill into ~/.claude/skills/.
#
# Usage: bash scripts/install-skill.sh
#
# What it does:
#   1. Symlinks <repo>/skills/claudebrain-init/SKILL.md -> ~/.claude/skills/claudebrain-init/SKILL.md
#   2. Writes <repo> absolute path into ~/.claude/skills/claudebrain-init/.repo-path
#      (the skill reads this to find its helper scripts in <repo>/scripts/init/)
#
# After install, type `/claudebrain-init` inside Claude Code from any directory.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_SRC="$REPO_ROOT/skills/claudebrain-init/SKILL.md"
SKILL_DST_DIR="$HOME/.claude/skills/claudebrain-init"
SKILL_DST="$SKILL_DST_DIR/SKILL.md"
REPO_PATH_FILE="$SKILL_DST_DIR/.repo-path"

if [ ! -f "$SKILL_SRC" ]; then
    echo "ERRO: SKILL.md nao encontrado em $SKILL_SRC" >&2
    echo "Confirme que voce clonou o repo completo." >&2
    exit 1
fi

mkdir -p "$SKILL_DST_DIR"

if [ -e "$SKILL_DST" ] || [ -L "$SKILL_DST" ]; then
    if [ -d "$SKILL_DST" ] && [ ! -L "$SKILL_DST" ]; then
        echo "ERRO: $SKILL_DST e diretorio real (nao symlink). Remova manualmente antes de re-instalar." >&2
        exit 1
    fi
    echo "Removendo install anterior: $SKILL_DST"
    rm -f "$SKILL_DST"
fi

ln -s "$SKILL_SRC" "$SKILL_DST"
echo "$REPO_ROOT" > "$REPO_PATH_FILE"

echo
echo "OK Skill instalado."
echo "   Skill:     $SKILL_DST -> $SKILL_SRC"
echo "   Repo path: $REPO_PATH_FILE ($REPO_ROOT)"
echo
echo "Agora, dentro do Claude Code, rode:"
echo "   /claudebrain-init"
