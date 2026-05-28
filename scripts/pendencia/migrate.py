"""Migrate legacy <Projeto>/Pendencias/*.md (flat) to <slug>/spec.md (cascade).

Two-phase:
    plan_migration(pendencias_dir, project) -> list of Migration dicts
    apply(plan, pendencias_dir, dry_run=False)

The plan items carry the project name so apply() needs no project arg.
Idempotent: only flat .md files (not subfolders) are considered.
"""

from __future__ import annotations

import datetime as _dt
import re
import sys
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).parent))
import slug as slug_mod  # noqa: E402


class Migration(TypedDict):
    source: str
    slug: str
    target_dir: str
    target_file: str
    project: str


def plan_migration(pendencias_dir: Path, project: str) -> list[Migration]:
    """List flat .md files in pendencias_dir and propose a migration plan.

    Returns sorted by source filename. Slugs are normalized + conflict-resolved
    against current pendencias_dir state AND slugs already chosen in this plan.
    """
    if not pendencias_dir.is_dir():
        return []

    plan: list[Migration] = []
    used_slugs: set[str] = set()

    for entry in sorted(pendencias_dir.iterdir()):
        if not entry.is_file() or entry.suffix != ".md":
            continue
        stem = entry.stem
        try:
            base_slug = slug_mod.normalize(stem)
        except ValueError:
            continue

        candidate = base_slug
        i = 2
        while (pendencias_dir / candidate).exists() or candidate in used_slugs:
            candidate = f"{base_slug}-{i}"
            i += 1
        used_slugs.add(candidate)

        plan.append(Migration(
            source=str(entry),
            slug=candidate,
            target_dir=str(pendencias_dir / candidate),
            target_file=str(pendencias_dir / candidate / "spec.md"),
            project=project,
        ))
    return plan


_FRONTMATTER_RE = re.compile(r"\A---\r?\n.*?\r?\n---\r?\n\r?\n?", re.DOTALL)


def _strip_existing_frontmatter(text: str) -> str:
    return _FRONTMATTER_RE.sub("", text, count=1)


def _new_frontmatter(project: str, slug: str, date: str) -> str:
    return (
        "---\n"
        f"type: pendencia-spec\n"
        f"project: {project}\n"
        f"slug: {slug}\n"
        f"stage: spec\n"
        f"created: {date}\n"
        f"updated: {date}\n"
        f"tags: [pendencia, {project}, migrated]\n"
        "---\n\n"
    )


def apply(plan: list[Migration], pendencias_dir: Path, dry_run: bool = False) -> None:
    """Execute the migration plan. Reads each source, writes target_file, deletes source.

    Skips entries whose target already exists (idempotent re-run safety).
    """
    today = _dt.date.today().isoformat()

    for item in plan:
        src = Path(item["source"])
        target_dir = Path(item["target_dir"])
        target_file = Path(item["target_file"])

        if target_file.exists():
            continue

        body = src.read_text(encoding="utf-8")
        body_no_fm = _strip_existing_frontmatter(body).lstrip("\n")
        new_text = _new_frontmatter(item["project"], item["slug"], today) + body_no_fm

        if dry_run:
            continue

        target_dir.mkdir(parents=True, exist_ok=True)
        target_file.write_text(new_text, encoding="utf-8")
        src.unlink()
