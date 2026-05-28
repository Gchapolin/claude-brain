"""Classify a pendencia folder by which cascade files are present.

The disk is the source of truth: no `status` frontmatter to maintain.

Stages:
    aberta        — only spec.md
    planejamento  — spec.md + task.md
    pronta        — spec.md + task.md + tests.md
    realizada     — all four files
    invalid       — anything else (missing spec, gap in cascade)

next_stage() returns the suffix indicating which file to generate next:
    "task" | "tests" | "implement" | "done"
"""

from __future__ import annotations

from pathlib import Path

STAGES = ("spec.md", "task.md", "tests.md", "resultado.md")


def _present(folder: Path) -> tuple[bool, ...]:
    return tuple((folder / name).is_file() for name in STAGES)


def classify_pendencia(folder: Path) -> str:
    spec, task, tests, resultado = _present(folder)
    if not spec:
        return "invalid"
    if not task:
        return "invalid" if (tests or resultado) else "aberta"
    if not tests:
        return "invalid" if resultado else "planejamento"
    if not resultado:
        return "pronta"
    return "realizada"


def next_stage(folder: Path) -> str:
    """Return the next action: 'task', 'tests', 'implement', or 'done'.

    Raises ValueError on invalid state.
    """
    state = classify_pendencia(folder)
    mapping = {
        "aberta": "task",
        "planejamento": "tests",
        "pronta": "implement",
        "realizada": "done",
    }
    if state not in mapping:
        raise ValueError(f"Pendencia em {folder} esta em estado invalido")
    return mapping[state]


def classify_project_pendencias(pendencias_dir: Path) -> dict[str, str]:
    """For a <Projeto>/Pendencias/ folder, return {slug: stage} for each subdir."""
    result = {}
    if not pendencias_dir.is_dir():
        return result
    for child in sorted(pendencias_dir.iterdir()):
        if child.is_dir() and not child.name.startswith("_"):
            result[child.name] = classify_pendencia(child)
    return result


def count_legado(pendencias_dir: Path) -> int:
    """Count flat .md files in <Projeto>/Pendencias/ (legacy format)."""
    if not pendencias_dir.is_dir():
        return 0
    return sum(1 for f in pendencias_dir.iterdir() if f.is_file() and f.suffix == ".md")
