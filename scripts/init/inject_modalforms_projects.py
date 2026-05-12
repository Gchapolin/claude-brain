#!/usr/bin/env python3
"""Modal Forms dropdown manager.

Two modes:
  --mode replace (default, used by /claudebrain-init Phase 4):
      Replaces the entire options list with the provided projects plus the
      "(geral, sem projeto)" sink.

  --mode add (used by claudebrain-update.sh when new projects are detected):
      Inserts the provided projects right before the "geral" option, skipping
      any that already exist. Preserves existing options.

Both modes are idempotent.

Project names are passed as a JSON list via --projects-json (handles names
with spaces, commas, or other shell-hostile characters). For convenience,
--projects (comma-separated) is also accepted; use --projects-json when
names may contain commas.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

FORM_NAME = "capturar-nota"
FIELD_NAME = "projeto"
GERAL_OPTION = {"value": "geral", "label": "(geral, sem projeto)"}


def parse_projects(args: argparse.Namespace) -> list[str]:
    if args.projects_json:
        names = json.loads(args.projects_json)
        if not isinstance(names, list):
            raise ValueError("--projects-json must be a JSON list")
        return [str(n).strip() for n in names if str(n).strip()]
    if args.projects:
        return [p.strip() for p in args.projects.split(",") if p.strip()]
    return []


def find_field(data_json: Path) -> tuple[dict, dict]:
    """Return (data, target_field) or raise ValueError if not found."""
    data = json.loads(data_json.read_text())
    forms = data.get("formDefinitions", [])
    target_form = next((f for f in forms if f.get("name") == FORM_NAME), None)
    if target_form is None:
        raise ValueError(f"form '{FORM_NAME}' nao encontrado em {data_json}")
    target_field = next(
        (f for f in target_form.get("fields", []) if f.get("name") == FIELD_NAME),
        None,
    )
    if target_field is None:
        raise ValueError(f"field '{FIELD_NAME}' nao encontrado no form '{FORM_NAME}'")
    return data, target_field


def apply_replace(field: dict, projects: list[str]) -> tuple[bool, str]:
    new_options = [{"value": p, "label": p} for p in projects] + [GERAL_OPTION]
    if field.get("input", {}).get("options") == new_options:
        return False, f"options ja batem ({len(projects)} projetos + geral)"
    field.setdefault("input", {})["type"] = "select"
    field["input"]["source"] = "fixed"
    field["input"]["options"] = new_options
    return True, f"replaced com {len(projects)} projetos + geral"


def apply_add(field: dict, projects: list[str]) -> tuple[bool, str]:
    opts = field.setdefault("input", {}).setdefault("options", [])
    existing = {o.get("value") for o in opts}
    geral_idx = next(
        (i for i, o in enumerate(opts) if o.get("value") == "geral"),
        len(opts),
    )
    added = []
    for p in projects:
        if p in existing:
            continue
        opts.insert(geral_idx, {"value": p, "label": p})
        geral_idx += 1
        existing.add(p)
        added.append(p)
    # Ensure geral sink exists at the end
    if "geral" not in existing:
        opts.append(GERAL_OPTION)
    field["input"]["type"] = "select"
    field["input"].setdefault("source", "fixed")
    field["input"]["options"] = opts
    if not added:
        return False, "nada a adicionar (todos ja presentes)"
    return True, f"adicionados: {added}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--mode", choices=("replace", "add"), default="replace")
    parser.add_argument(
        "--projects",
        help="comma-separated project names (use --projects-json if names may contain commas)",
    )
    parser.add_argument(
        "--projects-json",
        help="JSON list of project names; preferred when names have shell-hostile chars",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.projects and not args.projects_json:
        print("ERRO: passe --projects ou --projects-json", file=sys.stderr)
        return 1

    try:
        projects = parse_projects(args)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"ERRO ao parsear projetos: {e}", file=sys.stderr)
        return 1

    if not projects:
        print("ERRO: nenhum projeto informado", file=sys.stderr)
        return 1

    data_json = args.vault / ".obsidian" / "plugins" / "modalforms" / "data.json"
    if not data_json.exists():
        print(f"ERRO: {data_json} nao existe. Rode a Fase 2 primeiro.", file=sys.stderr)
        return 1

    try:
        data, field = find_field(data_json)
    except ValueError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1

    if args.mode == "replace":
        changed, msg = apply_replace(field, projects)
    else:
        changed, msg = apply_add(field, projects)

    if not changed:
        print(f"OK   {msg}")
        return 0

    payload = json.dumps(data, indent=2, ensure_ascii=False)
    if args.dry_run:
        print(f"DRY-RUN escreveria em {data_json}: {msg}")
        return 0

    data_json.write_text(payload + "\n")
    print(f"OK   {data_json}: {msg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
