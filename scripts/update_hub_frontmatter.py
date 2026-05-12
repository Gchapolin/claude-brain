#!/usr/bin/env python3
"""Adiciona/atualiza description, stack, color no frontmatter dos hubs de projeto.

Uso:
    # Modo 1: arquivo JSON com varios projetos
    python3 update_hub_frontmatter.py --config hubs.json

    # Modo 2: um projeto via flags
    python3 update_hub_frontmatter.py --project CV \\
        --description "CV pessoal em PDF + site" --stack PY,JS --color purple

    # Modo 3: auto-detecta tudo (stack via extensoes de arquivo,
    # description via primeira frase do README, color via hash do nome)
    python3 update_hub_frontmatter.py --project CV --auto

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
import collections
import json
import re
import sys
from pathlib import Path


STACK_BY_EXT = {
    ".swift": "SW",
    ".kt": "KT", ".kts": "KT",
    ".ts": "TS", ".tsx": "TS",
    ".js": "JS", ".jsx": "JS", ".mjs": "JS",
    ".html": "HTML", ".htm": "HTML",
    ".py": "PY",
    ".rs": "RS",
}

EXCLUDE_DIRS = {
    "node_modules", ".git", "build", "dist", "target",
    "Pods", ".gradle", "__pycache__", "venv", ".venv",
    "graphify-out", ".next", "DerivedData", "build-device",
    "vendor", ".pytest_cache", ".tox",
}

COLOR_PALETTE = ("purple", "blue", "green", "pink", "orange", "lavender", "yellow")


def detect_stack(project_dir: Path, top_n: int = 3) -> list[str]:
    """Conta extensoes de arquivo e retorna ate top_n tags de stack."""
    if not project_dir.is_dir():
        return []
    counts: collections.Counter[str] = collections.Counter()
    for p in project_dir.rglob("*"):
        if not p.is_file():
            continue
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        tag = STACK_BY_EXT.get(p.suffix.lower())
        if tag:
            counts[tag] += 1
    return [tag for tag, _ in counts.most_common(top_n)]


def detect_description(project_dir: Path, max_len: int = 80) -> str:
    """Le README.md (ou variantes) e retorna primeira frase nao-heading, sem markdown."""
    if not project_dir.is_dir():
        return ""
    for name in ("README.md", "readme.md", "Readme.md", "README.MD"):
        readme = project_dir / name
        if not readme.exists():
            continue
        try:
            text = readme.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Pula frontmatter
        if text.startswith("---"):
            end = text.find("\n---", 4)
            if end > 0:
                text = text[end + 4:]
        for para in text.split("\n\n"):
            para = para.strip()
            if not para or para.startswith("#") or para.startswith("```"):
                continue
            # Remove emphasis e inline code
            para = re.sub(r"\*+", "", para)
            para = re.sub(r"`+", "", para)
            # Remove links markdown: [texto](url) -> texto
            para = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", para)
            para = para.strip()
            if not para:
                continue
            sentence = re.split(r"(?<=[.!?])\s", para)[0].strip()
            if sentence:
                return sentence[:max_len].rstrip(".,;:").strip()
        break
    return ""


def detect_color(project_name: str) -> str:
    """Cor deterministica via hash simples — mesma cor toda vez pro mesmo nome."""
    h = sum(ord(c) for c in project_name)
    return COLOR_PALETTE[h % len(COLOR_PALETTE)]


def autodetect(project_name: str, projetos_root: Path) -> dict:
    proj_dir = projetos_root / project_name
    return {
        "description": detect_description(proj_dir) or "(sem descricao)",
        "stack": detect_stack(proj_dir),
        "color": detect_color(project_name),
    }

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
    parser.add_argument(
        "--auto",
        action="store_true",
        help="auto-detecta description/stack/color (so em --project mode)",
    )
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
        if args.auto:
            config = {args.project: autodetect(args.project, args.projetos_root)}
            meta = config[args.project]
            print(f"  auto-detected {args.project}: stack={meta['stack']}, color={meta['color']}")
            print(f"    description: {meta['description']!r}")
        else:
            missing = [f for f in ("description", "stack", "color") if not getattr(args, f)]
            if missing:
                print(f"ERRO: em modo --project, faltam: {missing} (ou use --auto)", file=sys.stderr)
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
