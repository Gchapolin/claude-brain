"""Shared helpers for tests. Loads scripts/init/*.py as importable modules."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INIT_DIR = REPO_ROOT / "scripts" / "init"


def load_module(name: str, file_stem: str):
    """Load <file_stem>.py from scripts/init/ under module name `name`."""
    if name in sys.modules:
        return sys.modules[name]
    path = INIT_DIR / f"{file_stem}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
