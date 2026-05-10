#!/usr/bin/env python3
"""Build a central hub note per project that wikilinks to all notes in its vault.
Stores hub at <project>/notes/<project>-hub.md and symlinks to vault root as <project>.md.

Uso:
    1. Edite a lista PROJECTS abaixo com os nomes de pastas em ~/PROJETOS que voce
       quer hub-ificar. Cada projeto precisa ter graphify-out/obsidian/ ja gerado.
    2. Rode: python3 build_project_hubs.py
"""
import sys
import os
from pathlib import Path

# >>> EDITE AQUI COM OS NOMES DAS PASTAS DOS SEUS PROJETOS <<<
PROJECTS = [
    # "MeuProjeto1",
    # "MeuProjeto2",
]
BASE = Path("~/PROJETOS").expanduser()

def list_notes(vault: Path):
    """All .md files in the vault, excluding .obsidian and the hub itself."""
    notes = []
    for p in vault.rglob('*.md'):
        try:
            rel = p.relative_to(vault)
        except ValueError:
            continue
        if rel.parts and rel.parts[0] in ('.obsidian',):
            continue
        # Skip if it's the hub file itself (would be at root)
        if rel.parts and len(rel.parts) == 1 and rel.name == f'{vault.parent.parent.name}.md':
            continue
        notes.append(rel)
    return notes

def build_hub_content(project_name: str, notes: list):
    n = len(notes)
    lines = [
        '---',
        'type: project-hub',
        f'project: {project_name}',
        'created: 2026-05-09',
        'tags: [projecthub]',
        f'notes_count: {n}',
        '---',
        '',
        f'# {project_name}',
        '',
        f'Hub central conectando todas as {n} notas deste projeto.',
        '',
        '## Notas',
        '',
    ]
    for note in sorted(notes, key=lambda p: str(p).lower()):
        # Strip trailing .md but keep e.g. .swift.md → .swift
        target = str(note.with_suffix(''))  # 'android/.../SettingsModels.kt'
        display = note.stem  # 'SettingsModels.kt'
        # Escape backslashes (none expected) and brackets
        if '|' in display or ']' in display or '[' in display:
            display = display.replace('|', '_').replace('[', '(').replace(']', ')')
        lines.append(f'- [[{target}|{display}]]')
    return '\n'.join(lines) + '\n'


def make_project_hub(project: str):
    project_dir = BASE / project
    vault = project_dir / 'graphify-out' / 'obsidian'
    if not vault.is_dir():
        print(f"  SKIP: vault not found at {vault}")
        return
    notes_dir = project_dir / 'notes'
    notes_dir.mkdir(parents=True, exist_ok=True)
    hub_file = notes_dir / f'{project}-hub.md'

    notes = list_notes(vault)
    content = build_hub_content(project, notes)
    hub_file.write_text(content)

    # Symlink into vault root as <project>.md (so it shows at top-level in sidebar)
    symlink = vault / f'{project}.md'
    if symlink.is_symlink() or symlink.exists():
        try:
            symlink.unlink()
        except IsADirectoryError:
            print(f"  WARN: {symlink} exists as directory, skipping symlink")
            return
    rel_target = os.path.relpath(hub_file, vault)
    symlink.symlink_to(rel_target)
    print(f"  {project}: hub at notes/{project}-hub.md ({len(notes)} wikilinks), symlink at vault root")


def main():
    print("Building per-project hub notes...")
    for proj in PROJECTS:
        make_project_hub(proj)


if __name__ == '__main__':
    main()
