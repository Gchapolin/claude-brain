#!/usr/bin/env python3
"""Phase 0 of /claudebrain-init: detect current state of the system.

Outputs a JSON document on stdout describing:
  - vault existence and path
  - projects under PROJETOS root, with graphify-out and vault-link status
  - iCloud Obsidian folder availability
  - which plugins are already installed (id -> version or None)
  - which plugin configs (data.json) are already populated

Designed to be consumed by the SKILL.md so the skill can decide which
phases to offer and which to skip as idempotent no-ops.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

DEFAULT_PROJETOS = Path.home() / "PROJETOS"
DEFAULT_VAULT = Path.home() / "PROJETOS" / "Obsidian" / "ClaudeBrain"
DEFAULT_ICLOUD = (
    Path.home()
    / "Library"
    / "Mobile Documents"
    / "iCloud~md~obsidian"
    / "Documents"
    / "ClaudeBrain-Mobile"
)
# Dirs under PROJETOS that are NOT real projects (the vault container, the
# template repo itself, etc). Override with --skip if your layout differs.
DEFAULT_SKIP = ("Obsidian", "claude-brain")


def load_lock(repo_root: Path) -> dict:
    lock_path = repo_root / "plugins.lock.json"
    if not lock_path.exists():
        return {"plugins": [], "obsidian_core_configs": []}
    return json.loads(lock_path.read_text())


def detect_plugins(vault: Path, lock: dict) -> list[dict]:
    plugins_dir = vault / ".obsidian" / "plugins"
    out = []
    for entry in lock.get("plugins", []):
        folder = plugins_dir / entry["folder"]
        manifest = folder / "manifest.json"
        installed_version = None
        if manifest.exists():
            try:
                installed_version = json.loads(manifest.read_text()).get("version")
            except (json.JSONDecodeError, OSError):
                installed_version = "?"
        data_json = folder / "data.json"
        out.append(
            {
                "id": entry["id"],
                "folder": entry["folder"],
                "required": entry["required"],
                "installed_version": installed_version,
                "wanted_version": entry["version"],
                "matches": installed_version == entry["version"],
                "has_data_json": data_json.exists(),
                "config_example": entry.get("config_example"),
            }
        )
    return out


def detect_projects(projetos_root: Path, vault: Path, skip: tuple[str, ...]) -> list[dict]:
    if not projetos_root.exists():
        return []
    projects = []
    for child in sorted(projetos_root.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if child.name in skip:
            continue
        graphify_out = child / "graphify-out" / "obsidian"
        vault_link = vault / child.name
        projects.append(
            {
                "name": child.name,
                "path": str(child),
                "has_graphify_out": graphify_out.exists(),
                "graphify_out_path": str(graphify_out),
                "already_linked": vault_link.is_symlink() or vault_link.is_dir(),
                "vault_link_path": str(vault_link),
                "has_notes_symlinks": (child / "notes" / "Pendencias").exists()
                and (child / "notes" / "Geral").exists(),
            }
        )
    return projects


def detect_obsidian_core_configs(vault: Path, lock: dict) -> list[dict]:
    cfg_dir = vault / ".obsidian"
    out = []
    for entry in lock.get("obsidian_core_configs", []):
        target = cfg_dir / entry["target"]
        out.append({"target": entry["target"], "exists": target.exists()})
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--projetos-root", type=Path, default=DEFAULT_PROJETOS)
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    parser.add_argument("--icloud", type=Path, default=DEFAULT_ICLOUD)
    parser.add_argument(
        "--skip",
        nargs="*",
        default=list(DEFAULT_SKIP),
        help="folders sob projetos-root a ignorar (default: Obsidian claude-brain)",
    )
    args = parser.parse_args()

    lock = load_lock(args.repo_root)

    state = {
        "repo_root": str(args.repo_root),
        "projetos_root": {
            "path": str(args.projetos_root),
            "exists": args.projetos_root.exists(),
        },
        "vault": {
            "path": str(args.vault),
            "exists": args.vault.exists(),
            "has_obsidian_dir": (args.vault / ".obsidian").exists(),
            "has_index_md": (args.vault / "Index.md").exists()
            or (args.vault / "Index.md").is_symlink(),
            "has_capturar_md": (args.vault / "Capturar.md").exists()
            or (args.vault / "Capturar.md").is_symlink(),
            "has_templates": (args.vault / "Templates").exists(),
            "has_notas_pendentes": (args.vault / "Notas Pendentes").exists(),
        },
        "icloud": {
            "path": str(args.icloud),
            "exists": args.icloud.exists(),
        },
        "claudebrain_update_sh": {
            "path": str(Path.home() / ".local" / "bin" / "claudebrain-update.sh"),
            "installed": (Path.home() / ".local" / "bin" / "claudebrain-update.sh").exists(),
        },
        "projects": detect_projects(args.projetos_root, args.vault, tuple(args.skip)),
        "plugins": detect_plugins(args.vault, lock),
        "obsidian_core_configs": detect_obsidian_core_configs(args.vault, lock),
    }

    json.dump(state, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
