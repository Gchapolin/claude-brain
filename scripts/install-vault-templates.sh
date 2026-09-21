#!/usr/bin/env bash
# Deploya os templates versionados em <repo>/vault/ pro vault Obsidian vivo.
#
# Uso:
#   bash scripts/install-vault-templates.sh              # aplica
#   bash scripts/install-vault-templates.sh --dry-run    # mostra o que faria
#   bash scripts/install-vault-templates.sh --dry-run --check
#                                                        # idem, mas sai 1 se ha divergencia
#
# Env (mesmos nomes do claudebrain-update.sh):
#   ICLOUD     default: ~/Library/Mobile Documents/iCloud~md~obsidian/Documents/ClaudeBrain-Mobile
#   MAC_VAULT  default: ~/PROJETOS/Obsidian/ClaudeBrain
#
# Por arquivo:
#   destino ausente    -> copia                      (NOVO)
#   destino identico   -> nao escreve nada           (OK)
#   destino divergente -> backup ao lado + copia     (ATUALIZADO)
#
# Idempotente: rodar duas vezes seguidas nao escreve nada na segunda.
# O backup (.{nome}.bak-{timestamp}) torna todo overwrite reversivel, entao
# nao existe --force: sobrescrever e sempre seguro.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC_ROOT="$REPO_ROOT/vault"

ICLOUD="${ICLOUD:-$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/ClaudeBrain-Mobile}"
MAC_VAULT="${MAC_VAULT:-$HOME/PROJETOS/Obsidian/ClaudeBrain}"

# Arquivos que vivem no iCloud (sincronizam pro iPhone/iPad).
ICLOUD_FILES=(
    "Index.md"
    "Capturar.md"
    "Templates/Captura.md"
)
# Arquivos que vivem so no vault do Mac (config do Obsidian nao vai pro iCloud).
MAC_FILES=(
    ".obsidian/snippets/brain-hub.css"
)

DRY_RUN=0
CHECK=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --check) CHECK=1 ;;
        *) echo "ERRO: argumento desconhecido: $arg" >&2; exit 1 ;;
    esac
done

if [ ! -d "$SRC_ROOT" ]; then
    echo "ERRO: fonte nao encontrada: $SRC_ROOT" >&2
    exit 1
fi
for dest_root in "$ICLOUD" "$MAC_VAULT"; do
    if [ ! -d "$dest_root" ]; then
        echo "ERRO: destino nao existe: $dest_root" >&2
        echo "      (rode /claudebrain-init antes, ou ajuste ICLOUD/MAC_VAULT)" >&2
        exit 1
    fi
done

NEW=0
UPDATED=0
SAME=0

backup_path() {
    # Backup escondido ao lado do arquivo, com contador em caso de colisao.
    local dest="$1"
    local dir base stamp candidate i
    dir="$(dirname "$dest")"
    base="$(basename "$dest")"
    stamp="$(date '+%Y%m%d-%H%M%S')"
    candidate="$dir/.$base.bak-$stamp"
    i=2
    while [ -e "$candidate" ]; do
        candidate="$dir/.$base.bak-$stamp-$i"
        i=$((i + 1))
    done
    printf '%s' "$candidate"
}

deploy_one() {
    local rel="$1" dest_root="$2"
    local src="$SRC_ROOT/$rel"
    local dest="$dest_root/$rel"

    if [ ! -f "$src" ]; then
        echo "ERRO: template ausente no repo: $src" >&2
        exit 1
    fi

    if [ ! -e "$dest" ]; then
        NEW=$((NEW + 1))
        if [ "$DRY_RUN" -eq 1 ]; then
            echo "DRY    $rel (criaria em $dest_root)"
            return 0
        fi
        mkdir -p "$(dirname "$dest")"
        cp -- "$src" "$dest"
        echo "NOVO   $rel"
        return 0
    fi

    if cmp -s -- "$src" "$dest"; then
        SAME=$((SAME + 1))
        echo "OK     $rel"
        return 0
    fi

    UPDATED=$((UPDATED + 1))
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "DRY    $rel (sobrescreveria, $(diff -U0 -- "$dest" "$src" | grep -c '^[+-][^+-]' || true) linhas diferentes)"
        return 0
    fi
    local bak
    bak="$(backup_path "$dest")"
    cp -- "$dest" "$bak"
    cp -- "$src" "$dest"
    echo "ATUALIZADO $rel (backup: $bak)"
}

for rel in "${ICLOUD_FILES[@]}"; do
    deploy_one "$rel" "$ICLOUD"
done
for rel in "${MAC_FILES[@]}"; do
    deploy_one "$rel" "$MAC_VAULT"
done

echo
echo "Resumo: novos=$NEW atualizados=$UPDATED iguais=$SAME"
echo "  iCloud:    $ICLOUD"
echo "  Mac vault: $MAC_VAULT"

if [ "$CHECK" -eq 1 ] && [ $((NEW + UPDATED)) -gt 0 ]; then
    exit 1
fi
exit 0
