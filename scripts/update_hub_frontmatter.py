#!/usr/bin/env python3
"""Adiciona description, stack, color ao frontmatter dos hubs de projeto.

Uso:
    1. Edite a constante PROJECTS abaixo com os seus projetos.
    2. Rode: python3 update_hub_frontmatter.py
    3. Os hubs em ~/PROJETOS/<projeto>/notes/<projeto>-hub.md e
       em iCloud~md~obsidian/.../ClaudeBrain-Mobile/<projeto>/<projeto>.md
       receberao os campos atualizados.

Cores disponiveis (combinam com o snippet CSS brain-hub.css):
    purple, blue, green, pink, orange, lavender, yellow, gray

Stack tags disponiveis:
    SW (Swift), KT (Kotlin), JS, TS, HTML, PY (Python), RS (Rust), WORK
"""
import re
from pathlib import Path

# >>> EDITE AQUI COM SEUS PROJETOS <<<
PROJECTS = {
    # exemplo:
    # "MeuProjeto": {
    #     "description": "Descricao curta (1 linha)",
    #     "stack": ["PY", "JS"],
    #     "color": "purple",
    # },
}

ICLOUD = Path("~/Library/Mobile Documents/iCloud~md~obsidian/Documents/ClaudeBrain-Mobile").expanduser()
PROJETOS = Path("~/PROJETOS").expanduser()


def update_frontmatter(path: Path, fields: dict):
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    m = re.match(r'^(---\n)(.*?)(\n---\n)(.*)$', text, re.DOTALL)
    if not m:
        return False
    fm_block = m.group(2)

    for key in fields.keys():
        fm_block = re.sub(rf'^{key}:.*$', '', fm_block, flags=re.MULTILINE)
    fm_block = re.sub(r'\n+', '\n', fm_block).strip('\n')

    additions = []
    for key, value in fields.items():
        if isinstance(value, list):
            additions.append(f"{key}: [{', '.join(value)}]")
        else:
            additions.append(f'{key}: "{value}"')
    new_fm = fm_block + "\n" + "\n".join(additions)
    new_text = m.group(1) + new_fm + m.group(3) + m.group(4)
    path.write_text(new_text, encoding="utf-8")
    return True


def main():
    if not PROJECTS:
        print("ERRO: PROJECTS esta vazio. Edite este script com seus projetos primeiro.")
        return

    count = 0
    for proj, meta in PROJECTS.items():
        fields = {"description": meta["description"], "stack": meta["stack"], "color": meta["color"]}
        mac_hub = PROJETOS / proj / "notes" / f"{proj}-hub.md"
        if update_frontmatter(mac_hub, fields):
            count += 1
            print(f"  Mac hub atualizado: {proj}")
        icloud_hub = ICLOUD / proj / f"{proj}.md"
        if update_frontmatter(icloud_hub, fields):
            count += 1
            print(f"  iCloud hub atualizado: {proj}")

    print(f"\nTotal: {count} hubs atualizados")


if __name__ == "__main__":
    main()
