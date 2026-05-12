#!/usr/bin/env python3
"""Build a central hub note per project that wikilinks to all notes in its vault.

Hub esta em <project>/notes/<project>-hub.md e e symlinkado pra vault root
como <project>.md (aparece no topo do sidebar do Obsidian).

Uso:
    python3 build_project_hubs.py CV Housi SmartScore
    python3 build_project_hubs.py --all                # detecta projetos com graphify-out
    python3 build_project_hubs.py --projetos-root /caminho/custom CV
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_BASE = Path("~/PROJETOS").expanduser()


def list_notes(vault: Path, project_name: str) -> list[Path]:
    """All .md files in the vault, excluding .obsidian and the hub itself."""
    notes = []
    for p in vault.rglob("*.md"):
        try:
            rel = p.relative_to(vault)
        except ValueError:
            continue
        if rel.parts and rel.parts[0] == ".obsidian":
            continue
        if len(rel.parts) == 1 and rel.name == f"{project_name}.md":
            continue
        notes.append(rel)
    return notes


def build_hub_content(project_name: str, notes: list[Path]) -> str:
    n = len(notes)
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        "---",
        "type: project-hub",
        f"project: {project_name}",
        f"created: {today}",
        "tags: [projecthub]",
        f"notes_count: {n}",
        "---",
        "",
        f"# {project_name}",
        "",
        f"Hub central conectando todas as {n} notas deste projeto.",
        "",
        "## Notas",
        "",
    ]
    for note in sorted(notes, key=lambda p: str(p).lower()):
        target = str(note.with_suffix(""))
        display = note.stem
        if "|" in display or "]" in display or "[" in display:
            display = display.replace("|", "_").replace("[", "(").replace("]", ")")
        lines.append(f"- [[{target}|{display}]]")
    return "\n".join(lines) + "\n"


def make_project_hub(project: str, base: Path) -> bool:
    project_dir = base / project
    vault = project_dir / "graphify-out" / "obsidian"
    if not vault.is_dir():
        print(f"  SKIP {project}: vault nao encontrado em {vault}")
        return False
    notes_dir = project_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    hub_file = notes_dir / f"{project}-hub.md"

    notes = list_notes(vault, project)
    hub_file.write_text(build_hub_content(project, notes))

    symlink = vault / f"{project}.md"
    if symlink.is_symlink() or symlink.exists():
        try:
            symlink.unlink()
        except IsADirectoryError:
            print(f"  WARN {project}: {symlink} existe como diretorio, pulando symlink")
            return False
    rel_target = os.path.relpath(hub_file, vault)
    symlink.symlink_to(rel_target)
    print(f"  OK {project}: notes/{project}-hub.md ({len(notes)} wikilinks) + symlink no vault")
    return True


def detect_projects(base: Path) -> list[str]:
    if not base.is_dir():
        return []
    out = []
    for child in sorted(base.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if child.name in ("Obsidian", "claude-brain"):
            continue
        if (child / "graphify-out" / "obsidian").is_dir():
            out.append(child.name)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("projects", nargs="*", help="nomes de projetos (pastas em projetos-root)")
    parser.add_argument(
        "--all",
        action="store_true",
        help="auto-detecta todos os projetos com graphify-out",
    )
    parser.add_argument("--projetos-root", type=Path, default=DEFAULT_BASE)
    args = parser.parse_args()

    if args.all and args.projects:
        print("ERRO: use ou --all ou nomes posicionais, nao ambos", file=sys.stderr)
        return 1

    projects = detect_projects(args.projetos_root) if args.all else args.projects
    if not projects:
        print("Nenhum projeto pra processar. Use --all ou passe nomes.", file=sys.stderr)
        return 1

    print(f"Building hubs em {args.projetos_root} pra: {projects}")
    ok = 0
    for proj in projects:
        if make_project_hub(proj, args.projetos_root):
            ok += 1
    print(f"\nTotal: {ok}/{len(projects)} hubs criados")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
