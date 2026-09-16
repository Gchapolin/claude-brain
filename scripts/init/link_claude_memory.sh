#!/usr/bin/env bash
# Mantem a memoria do harness (~/.claude/projects/<nome>/memory/) no iCloud.
#
# Fonte de verdade: <icloud>/_claude-memory/<nome>/ (dentro do vault, sincroniza
# como qualquer nota). Cada ~/.claude/projects/<nome>/memory vira symlink pra la.
#
# Idempotente. Cobre os dois sentidos:
#   - pasta no iCloud sem symlink local  -> cria o symlink (Mac novo)
#   - pasta local real sem par no iCloud -> move pro iCloud e deixa symlink (Mac antigo)
#   - pasta local real E par no iCloud   -> mescla (iCloud vence em conflito) e symlink
#
# Uso:
#   link_claude_memory.sh <icloud_dir> [claude_projects_dir] [--dry-run]
#   claude_projects_dir default: ~/.claude/projects

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "uso: $0 <icloud_dir> [claude_projects_dir] [--dry-run]" >&2
    exit 1
fi

ICLOUD="$1"; shift
PROJECTS="$HOME/.claude/projects"
DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        *) PROJECTS="$arg" ;;
    esac
done

if [ ! -d "$ICLOUD" ]; then
    echo "ERRO: iCloud dir nao existe: $ICLOUD" >&2
    exit 1
fi

SRC="$ICLOUD/_claude-memory"
if [ ! -d "$SRC" ]; then
    if [ "$DRY_RUN" -eq 1 ]; then echo "DRY  criaria $SRC"; else mkdir -p "$SRC"; fi
fi
if [ "$DRY_RUN" -eq 0 ]; then mkdir -p "$PROJECTS"; fi

link_one() {
    # $1 = nome da pasta (encoded cwd), $2 = alvo no iCloud
    local name="$1" target="$2"
    local dst="$PROJECTS/$name/memory"
    if [ -L "$dst" ]; then
        if [ "$(readlink "$dst")" = "$target" ]; then
            echo "OK   $name"
        else
            echo "WARN $name apontava pra $(readlink "$dst"); religando"
            [ "$DRY_RUN" -eq 0 ] && ln -sfn "$target" "$dst"
        fi
        return 0
    fi
    if [ -d "$dst" ]; then
        if [ "$DRY_RUN" -eq 1 ]; then
            echo "DRY  mesclaria $dst em $target e trocaria por symlink"
            return 0
        fi
        rsync -a --ignore-existing -- "$dst/" "$target/"
        rm -rf -- "$dst"
        ln -s -- "$target" "$dst"
        echo "MESCLADO $name (iCloud venceu em conflitos)"
        return 0
    fi
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "DRY  criaria symlink $dst -> $target"
        return 0
    fi
    mkdir -p "$PROJECTS/$name"
    ln -s -- "$target" "$dst"
    echo "LINK $name"
}

# 1) pastas que ja existem no iCloud
if [ -d "$SRC" ]; then
    for t in "$SRC"/-*/; do
        [ -d "$t" ] || continue
        t="${t%/}"
        link_one "$(basename "$t")" "$t"
    done
fi

# 2) pastas locais reais sem par no iCloud -> migrar
for d in "$PROJECTS"/-*/memory; do
    [ -d "$d" ] && [ ! -L "$d" ] || continue
    name="$(basename "$(dirname "$d")")"
    target="$SRC/$name"
    [ -d "$target" ] && continue   # ja tratado no passo 1
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "DRY  migraria $d -> $target"
        continue
    fi
    mkdir -p "$target"
    rsync -a -- "$d/" "$target/"
    if diff -rq -- "$d" "$target" >/dev/null; then
        rm -rf -- "$d"
        ln -s -- "$target" "$d"
        echo "MIGRADO $name"
    else
        echo "ERRO copia divergente, origem preservada: $d" >&2
        exit 1
    fi
done
