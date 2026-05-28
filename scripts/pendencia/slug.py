"""Slug normalization for pendencias.

Rules:
- lowercase, ASCII only (accents stripped)
- non-alphanumeric becomes single dash
- multiple dashes collapsed
- no leading/trailing dashes
- empty/all-invalid raises ValueError

Conflict resolution: append -2, -3, ... when the slug folder already exists.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path


def normalize(text: str) -> str:
    if not text:
        raise ValueError("slug vazio")

    nfkd = unicodedata.normalize("NFKD", text)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    lower = ascii_only.lower()
    replaced = re.sub(r"[^a-z0-9]+", "-", lower)
    stripped = replaced.strip("-")

    if not stripped:
        raise ValueError(f"slug {text!r} virou vazio apos normalizacao")
    return stripped


def resolve_conflict(parent: Path, slug: str) -> str:
    """Return slug as-is if no folder/file with that name exists in parent;
    otherwise append -2, -3, ... until unique."""
    if not (parent / slug).exists():
        return slug
    i = 2
    while (parent / f"{slug}-{i}").exists():
        i += 1
    return f"{slug}-{i}"
