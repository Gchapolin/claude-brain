#!/usr/bin/env bash
# Phase 6 of /claudebrain-init: setup iCloud sync for ONE project.
#
# Creates the iCloud-side Pendencias/Geral folders, then symlinks them
# from <projetos>/<name>/notes/{Pendencias,Geral}. Same mechanism the
# manual SETUP.md step 9 uses, but per-project and idempotent.
#
# Usage:
#   setup_icloud_sync.sh <project_name> <projetos_root> <icloud_dir> [--dry-run]

set -euo pipefail

if [ $# -lt 3 ]; then
    echo "uso: $0 <project_name> <projetos_root> <icloud_dir> [--dry-run]" >&2
    exit 1
fi

NAME="$1"
PROJETOS="$2"
ICLOUD="$3"
DRY_RUN=0
[ "${4:-}" = "--dry-run" ] && DRY_RUN=1

PROJ_NOTES="$PROJETOS/$NAME/notes"
ICLOUD_PROJ="$ICLOUD/$NAME"

if [ ! -d "$PROJETOS/$NAME" ]; then
    echo "ERRO: projeto nao existe: $PROJETOS/$NAME" >&2
    exit 1
fi

ensure_dir() {
    local d="$1"
    if [ -d "$d" ]; then return; fi
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "DRY  criaria $d"
    else
        mkdir -p "$d"
    fi
}

ensure_symlink() {
    local src="$1" dst="$2"
    if [ -L "$dst" ]; then
        local existing
        existing="$(readlink "$dst")"
        if [ "$existing" = "$src" ]; then
            echo "OK   symlink ja existe: $dst"
            return
        fi
        echo "WARN $dst aponta pra $existing (esperado $src)"
        [ "$DRY_RUN" -eq 0 ] && ln -sfn "$src" "$dst" && echo "     atualizado"
        return
    fi
    if [ -d "$dst" ]; then
        echo "WARN $dst existe como diretorio normal — nao tocando"
        return
    fi
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "DRY  criaria symlink $dst -> $src"
    else
        ln -sfn "$src" "$dst"
        echo "NEW  $dst -> $src"
    fi
}

ensure_dir "$PROJ_NOTES"
ensure_dir "$ICLOUD_PROJ/Pendencias"
ensure_dir "$ICLOUD_PROJ/Geral"
ensure_symlink "$ICLOUD_PROJ/Pendencias" "$PROJ_NOTES/Pendencias"
ensure_symlink "$ICLOUD_PROJ/Geral" "$PROJ_NOTES/Geral"
