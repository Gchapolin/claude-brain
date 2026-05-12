#!/usr/bin/env python3
"""Phase 2 of /claudebrain-init: install Obsidian community plugins.

For each plugin in plugins.lock.json:
  - skip if already installed at the pinned version (idempotent)
  - otherwise: download release assets from GitHub release tag, write to
    <vault>/.obsidian/plugins/<folder>/

Also:
  - writes <vault>/.obsidian/community-plugins.json with the enabled IDs
  - copies <repo>/vault/.obsidian/plugins-config/*.example to the matching
    live locations (data.json files for plugins, app.json/graph.json/types.json
    for Obsidian core)

Caveat: on first vault open, Obsidian prompts "Trust author?". One click,
vault-wide. That step is NOT automated by design — it is a security UI step.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path


def gh_release_url(repo: str, tag: str, asset: str) -> str:
    return f"https://github.com/{repo}/releases/download/{tag}/{asset}"


def fetch(url: str) -> tuple[bool, bytes | str, int | None]:
    """Returns (ok, payload_or_error_msg, http_status_if_known)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "claudebrain-init"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return True, resp.read(), 200
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code} for {url}", e.code
    except (urllib.error.URLError, OSError) as e:
        return False, f"error: {e}", None


def download_asset(repo: str, version: str, asset: str, dest: Path, dry_run: bool) -> tuple[bool, str]:
    """Try downloading asset using the pinned tag; fall back to 'v<version>' on 404.

    Some Obsidian plugins tag releases as bare semver ('1.2.3'), others prefix
    with 'v' ('v1.2.3'). plugins.lock.json stores the bare version; we try both.
    """
    if dry_run:
        return True, f"DRY-RUN would download {gh_release_url(repo, version, asset)}"

    url_bare = gh_release_url(repo, version, asset)
    ok, payload, status = fetch(url_bare)
    if not ok and status == 404:
        url_v = gh_release_url(repo, f"v{version}", asset)
        ok2, payload2, _ = fetch(url_v)
        if ok2:
            payload = payload2
            ok = True
        else:
            return False, f"HTTP 404 for both {url_bare} and {url_v}"
    if not ok:
        return False, str(payload)

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(payload)
    return True, f"downloaded {dest.name} ({len(payload)} bytes)"


def installed_version(folder: Path) -> str | None:
    manifest = folder / "manifest.json"
    if not manifest.exists():
        return None
    try:
        return json.loads(manifest.read_text()).get("version")
    except (json.JSONDecodeError, OSError):
        return None


def install_plugin(plugin: dict, vault: Path, dry_run: bool) -> dict:
    folder = vault / ".obsidian" / "plugins" / plugin["folder"]
    current = installed_version(folder)
    if current == plugin["version"]:
        return {"id": plugin["id"], "action": "skip", "reason": f"already at {current}"}

    # Stage downloads under <folder>.partial/ so a failure mid-install never leaves
    # an inconsistent <folder>/ that Obsidian would try to load.
    staging = folder.parent / f"{plugin['folder']}.partial"
    if staging.exists():
        shutil.rmtree(staging)

    result_lines = []
    all_ok = True
    for asset in plugin["assets"]:
        ok, msg = download_asset(plugin["repo"], plugin["version"], asset, staging / asset, dry_run)
        # styles.css is optional for some plugins — don't fail the whole install on it
        if not ok and asset == "styles.css":
            result_lines.append(f"  WARN {asset}: {msg} (optional asset)")
            continue
        if not ok:
            all_ok = False
        result_lines.append(f"  {asset}: {msg}")

    if dry_run:
        return {"id": plugin["id"], "action": "install", "version": plugin["version"], "lines": result_lines}

    if not all_ok:
        # Keep the partial dir for debugging; do NOT promote it
        return {
            "id": plugin["id"],
            "action": "fail",
            "version": plugin["version"],
            "lines": result_lines + [f"  (parcial preservado em {staging} pra debug)"],
        }

    # Atomic promote: remove old folder, rename partial -> folder
    if folder.exists():
        shutil.rmtree(folder)
    staging.rename(folder)
    return {
        "id": plugin["id"],
        "action": "install",
        "version": plugin["version"],
        "lines": result_lines,
    }


def write_community_plugins(vault: Path, ids: list[str], dry_run: bool) -> None:
    target = vault / ".obsidian" / "community-plugins.json"
    payload = json.dumps(ids, indent=2)
    if dry_run:
        print(f"DRY-RUN would write {target}:\n{payload}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload + "\n")


def apply_plugin_configs(repo_root: Path, vault: Path, lock: dict, dry_run: bool) -> list[str]:
    """Copy <repo>/vault/.obsidian/plugins-config/*.example to live locations."""
    src_dir = repo_root / "vault" / ".obsidian" / "plugins-config"
    if not src_dir.exists():
        return [f"WARN plugins-config dir not found: {src_dir}"]

    log = []
    for plugin in lock["plugins"]:
        if not plugin.get("config_example"):
            continue
        src = src_dir / plugin["config_example"]
        dst = vault / ".obsidian" / "plugins" / plugin["folder"] / "data.json"
        if not src.exists():
            log.append(f"  SKIP {plugin['id']}: example missing ({src.name})")
            continue
        if dst.exists():
            log.append(f"  SKIP {plugin['id']}: data.json already present")
            continue
        if dry_run:
            log.append(f"  DRY-RUN would copy {src.name} -> {dst}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        log.append(f"  COPY {plugin['id']}: {src.name} -> data.json")

    for cfg in lock.get("obsidian_core_configs", []):
        src = src_dir / cfg["example"]
        dst = vault / ".obsidian" / cfg["target"]
        if not src.exists():
            log.append(f"  SKIP core {cfg['target']}: example missing")
            continue
        if dst.exists():
            log.append(f"  SKIP core {cfg['target']}: already present")
            continue
        if dry_run:
            log.append(f"  DRY-RUN would copy {src.name} -> {dst}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        log.append(f"  COPY core {cfg['target']}")

    return log


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--include-optional", action="store_true",
                        help="include optional plugins (Meld Encrypt)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    lock_path = args.repo_root / "plugins.lock.json"
    if not lock_path.exists():
        print(f"ERRO: {lock_path} nao existe", file=sys.stderr)
        return 1
    lock = json.loads(lock_path.read_text())

    plugins = [p for p in lock["plugins"] if p["required"] or args.include_optional]

    print(f"Vault: {args.vault}")
    print(f"Plugins a processar: {len(plugins)}")
    if args.dry_run:
        print("MODO DRY-RUN — nada sera escrito.")
    print()

    enabled_ids = []
    fails = []
    for plugin in plugins:
        result = install_plugin(plugin, args.vault, args.dry_run)
        if result["action"] == "skip":
            print(f"OK  {result['id']:25s} {result['reason']}")
            enabled_ids.append(plugin["id"])
        elif result["action"] == "install":
            print(f"NEW {result['id']:25s} -> {result['version']}")
            for line in result["lines"]:
                print(line)
            enabled_ids.append(plugin["id"])
        else:
            print(f"FAIL {result['id']:24s}")
            for line in result["lines"]:
                print(line)
            fails.append(plugin["id"])

    print()
    print("Aplicando configs (.example -> data.json / core configs):")
    for line in apply_plugin_configs(args.repo_root, args.vault, lock, args.dry_run):
        print(line)

    print()
    print(f"Habilitando plugins em community-plugins.json: {enabled_ids}")
    write_community_plugins(args.vault, enabled_ids, args.dry_run)

    if fails:
        print(f"\nERROS em: {fails}", file=sys.stderr)
        return 2

    print("\nProximo passo: abra o vault no Obsidian. Na primeira vez ele vai pedir")
    print("'Trust author' pros plugins da comunidade — clique 1x e pronto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
