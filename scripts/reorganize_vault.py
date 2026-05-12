#!/usr/bin/env python3
"""Reorganize a graphify obsidian vault into folder structure mirroring source_file paths.
Resolves basename-only source_files by searching the project filesystem."""
import sys
import re
import shutil
from pathlib import Path

def get_frontmatter(md_path: Path):
    try:
        text = md_path.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return None
    m = re.match(r'^---\n(.*?)\n---', text, re.DOTALL)
    if not m:
        return None
    return m.group(1)

def get_source_file(fm: str):
    if not fm:
        return None
    m = re.search(r'^\s*source_file:\s*"?([^"\n]+?)"?\s*$', fm, re.MULTILINE)
    if not m:
        return None
    sf = m.group(1).strip()
    if sf.lower() in ('', 'null', 'none'):
        return None
    return sf

def build_basename_index(project_root: Path):
    """Map basename -> relative path under project_root.
    Excludes node_modules/.git/build/dist/target/etc."""
    EXCLUDE = {'node_modules', '.git', '.next', 'build', 'dist', 'target',
               'Pods', '.gradle', '__pycache__', 'venv', '.venv',
               'graphify-out', 'cache', 'DerivedData', 'build-device'}
    index = {}
    if not project_root.is_dir():
        return index
    for p in project_root.rglob('*'):
        if not p.is_file():
            continue
        if any(part in EXCLUDE for part in p.parts):
            continue
        try:
            rel = p.relative_to(project_root)
        except ValueError:
            continue
        # Don't index files at the project root itself for the basename map;
        # those should resolve to themselves.
        index.setdefault(p.name, str(rel))
    return index

def reorganize(vault_dir: Path):
    if not vault_dir.is_dir():
        print(f"ERROR: not a directory: {vault_dir}", file=sys.stderr)
        return 0, 0, 0

    # Try to resolve project root from graphify metadata
    project_root = None
    root_marker = vault_dir.parent / '.graphify_root'
    if root_marker.is_file():
        try:
            project_root = Path(root_marker.read_text().strip())
        except Exception:
            pass
    basename_index = build_basename_index(project_root) if project_root else {}

    md_files = [p for p in vault_dir.iterdir() if p.is_file() and p.suffix == '.md']
    if not md_files:
        print(f"  empty or already organized: {vault_dir}")
        return 0, 0, 0

    moves = []
    skipped = 0
    resolved = 0
    for md in md_files:
        name = md.name
        if name.startswith('_COMMUNITY_'):
            dest = vault_dir / '_communities' / name
        else:
            fm = get_frontmatter(md)
            sf = get_source_file(fm) if fm else None
            if sf:
                # If source_file is just a basename and we have an index, resolve it
                if '/' not in sf and basename_index:
                    full = basename_index.get(sf)
                    if full and '/' in full:
                        sf = full
                        resolved += 1
                src_dir = Path(sf).parent
                # Filtra '..', '/', '.' pra evitar path traversal — uma nota
                # com source_file: "../../../etc/passwd" nao deve escapar do vault.
                parts = [p for p in src_dir.parts if p not in ('', '..', '/', '.')]
                if parts:
                    dest = vault_dir.joinpath(*parts) / name
                else:
                    dest = vault_dir / name
            else:
                dest = vault_dir / '_misc' / name

        if dest != md:
            moves.append((md, dest))
        else:
            skipped += 1

    moved = 0
    for src, dest in moves:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            stem = dest.stem
            i = 2
            while True:
                alt = dest.with_name(f"{stem}_{i}{dest.suffix}")
                if not alt.exists():
                    dest = alt
                    break
                i += 1
        shutil.move(str(src), str(dest))
        moved += 1
    return moved, skipped, resolved


def main():
    if len(sys.argv) < 2:
        print("usage: reorganize_vault.py <vault_dir> [<vault_dir> ...]", file=sys.stderr)
        sys.exit(1)
    for v in sys.argv[1:]:
        path = Path(v)
        print(f"==> {path}")
        moved, skipped, resolved = reorganize(path)
        print(f"   moved: {moved}, kept: {skipped}, resolved-via-fs: {resolved}")


if __name__ == '__main__':
    main()
