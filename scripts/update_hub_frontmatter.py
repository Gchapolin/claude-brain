#!/usr/bin/env python3
"""Adiciona/atualiza description, stack, color no frontmatter dos hubs de projeto.

Uso:
    # Modo 1: arquivo JSON com varios projetos
    python3 update_hub_frontmatter.py --config hubs.json

    # Modo 2: um projeto via flags
    python3 update_hub_frontmatter.py --project CV \\
        --description "CV pessoal em PDF + site" --stack PY,JS --color purple

Formato do arquivo --config:
    {
      "CV": {"description": "...", "stack": ["PY", "JS"], "color": "purple"},
      "Housi": {"description": "...", "stack": ["KT", "SW"], "color": "blue"}
    }

Cores disponiveis (combinam com brain-hub.css):
    purple, blue, green, pink, orange, lavender, yellow, gray

Stack tags disponiveis:
    SW (Swift), KT (Kotlin), JS, TS, HTML, PY (Python), RS (Rust), WORK

Atualiza tanto o hub do Mac (~/PROJETOS/<projeto>/notes/<projeto>-hub.md)
quanto o hub do iCloud (.../ClaudeBrain-Mobile/<projeto>/<projeto>.md).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_ICLOUD = Path(
    "~/Library/Mobile Documents/iCloud~md~obsidian/Documents/ClaudeBrain-Mobile"
).expanduser()
DEFAULT_PROJETOS = Path("~/PROJETOS").expanduser()


def yaml_scalar(value) -> str:
    """JSON-encoded scalar — valid YAML for any string (handles quotes, newlines)."""
    if isinstance(value, list):
        # Inline YAML list of JSON-encoded scalars
        return "[" + ", ".join(yaml_scalar(v) for v in value) + "]"
    return json.dumps(value, ensure_ascii=False)


def update_frontmatter(path: Path, fields: dict) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^(---\n)(.*?)(\n---\n)(.*)$", text, re.DOTALL)
    if not m:
        return False
    fm_block = m.group(2)

    for key in fields:
        fm_block = re.sub(rf"^{re.escape(key)}:.*$", "", fm_block, flags=re.MULTILINE)
    fm_block = re.sub(r"\n+", "\n", fm_block).strip("\n")

    additions = [f"{key}: {yaml_scalar(value)}" for key, value in fields.items()]
    new_fm = fm_block + "\n" + "\n".join(additions)
    new_text = m.group(1) + new_fm + m.group(3) + m.group(4)
    path.write_text(new_text, encoding="utf-8")
    return True


def apply(project: str, meta: dict, projetos: Path, icloud: Path) -> int:
    fields = {
        "description": meta["description"],
        "stack": meta["stack"],
        "color": meta["color"],
    }
    count = 0
    mac_hub = projetos / project / "notes" / f"{project}-hub.md"
    if update_frontmatter(mac_hub, fields):
        count += 1
        print(f"  Mac hub atualizado: {project}")
    icloud_hub = icloud / project / f"{project}.md"
    if update_frontmatter(icloud_hub, fields):
        count += 1
        print(f"  iCloud hub atualizado: {project}")
    if count == 0:
        print(f"  AVISO {project}: nenhum hub encontrado pra atualizar")
    return count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="JSON file com mapping de projetos")
    parser.add_argument("--project", help="nome do projeto (modo single)")
    parser.add_argument("--description", help="(single mode) descricao curta")
    parser.add_argument(
        "--stack",
        help="(single mode) comma-separated, ex: 'PY,JS'",
    )
    parser.add_argument("--color", help="(single mode) cor do CSS snippet")
    parser.add_argument("--projetos-root", type=Path, default=DEFAULT_PROJETOS)
    parser.add_argument("--icloud", type=Path, default=DEFAULT_ICLOUD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.config:
        if not args.config.exists():
            print(f"ERRO: {args.config} nao existe", file=sys.stderr)
            return 1
        config = json.loads(args.config.read_text())
    elif args.project:
        missing = [f for f in ("description", "stack", "color") if not getattr(args, f)]
        if missing:
            print(f"ERRO: em modo --project, faltam: {missing}", file=sys.stderr)
            return 1
        config = {
            args.project: {
                "description": args.description,
                "stack": [s.strip() for s in args.stack.split(",") if s.strip()],
                "color": args.color,
            }
        }
    else:
        print("ERRO: passe --config <file> ou --project <nome> + flags", file=sys.stderr)
        return 1

    total = 0
    for project, meta in config.items():
        total += apply(project, meta, args.projetos_root, args.icloud)
    print(f"\nTotal: {total} hubs atualizados")
    return 0 if total else 1


if __name__ == "__main__":
    sys.exit(main())
