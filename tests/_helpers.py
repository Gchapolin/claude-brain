"""Shared helpers for tests. Loads scripts/{init,pendencia}/*.py as importable modules."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INIT_DIR = REPO_ROOT / "scripts" / "init"
PENDENCIA_DIR = REPO_ROOT / "scripts" / "pendencia"


def _load_from(dir_path: Path, name: str, file_stem: str):
    if name in sys.modules:
        return sys.modules[name]
    path = dir_path / f"{file_stem}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_module(name: str, file_stem: str):
    """Load <file_stem>.py from scripts/init/."""
    return _load_from(INIT_DIR, name, file_stem)


def load_pendencia_module(name: str, file_stem: str):
    """Load <file_stem>.py from scripts/pendencia/."""
    return _load_from(PENDENCIA_DIR, name, file_stem)
