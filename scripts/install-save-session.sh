#!/usr/bin/env bash
# Instala a skill /save-session globalmente.
#
# Usage: bash scripts/install-save-session.sh
#
# Depois de instalar, dentro do Claude Code de QUALQUER projeto, voce pode rodar:
#   /save-session
# pra salvar resumo estruturado da conversa atual no vault Obsidian E no
# memory/ do projeto (auto-carregado em sessoes futuras).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_SRC="$REPO_ROOT/skills/save-session/SKILL.md"
SKILL_DST_DIR="$HOME/.claude/skills/save-session"
SKILL_DST="$SKILL_DST_DIR/SKILL.md"

if [ ! -f "$SKILL_SRC" ]; then
    echo "ERRO: SKILL.md nao encontrado em $SKILL_SRC" >&2
    exit 1
fi

mkdir -p "$SKILL_DST_DIR"

if [ -e "$SKILL_DST" ] || [ -L "$SKILL_DST" ]; then
    if [ -d "$SKILL_DST" ] && [ ! -L "$SKILL_DST" ]; then
        echo "ERRO: $SKILL_DST e diretorio real. Remova manualmente." >&2
        exit 1
    fi
    rm -f "$SKILL_DST"
fi

ln -s "$SKILL_SRC" "$SKILL_DST"

echo "OK Skill /save-session instalada."
echo "   Skill: $SKILL_DST -> $SKILL_SRC"
echo
echo "Use dentro do Claude Code de qualquer projeto:"
echo "   /save-session                  # salva resumo da sessao atual"
echo "   /save-session --note \"X\"       # adiciona nota livre"
echo "   /save-session --dry-run        # preview sem salvar"
