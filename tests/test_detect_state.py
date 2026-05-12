"""Tests for scripts/init/detect_state.py — state detection of vault and projects."""

import json
import tempfile
import unittest
from pathlib import Path

from tests._helpers import REPO_ROOT, load_module

detect_state = load_module("detect_state", "detect_state")


class TestDetectProjects(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.projetos = self.root / "PROJETOS"
        self.vault = self.root / "vault"
        self.projetos.mkdir()
        self.vault.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _make_project(self, name: str, with_graphify: bool = False, linked: bool = False):
        p = self.projetos / name
        p.mkdir()
        if with_graphify:
            (p / "graphify-out" / "obsidian").mkdir(parents=True)
        if linked:
            target = (p / "graphify-out" / "obsidian") if with_graphify else p
            (self.vault / name).symlink_to(target)
        return p

    def test_empty_projetos_returns_empty(self):
        result = detect_state.detect_projects(self.projetos, self.vault, ())
        self.assertEqual(result, [])

    def test_skip_list_excludes_named_dirs(self):
        self._make_project("Obsidian")
        self._make_project("claude-brain")
        self._make_project("real-project", with_graphify=True)
        result = detect_state.detect_projects(self.projetos, self.vault, ("Obsidian", "claude-brain"))
        names = [p["name"] for p in result]
        self.assertEqual(names, ["real-project"])

    def test_detects_graphify_out(self):
        self._make_project("withgrap", with_graphify=True)
        self._make_project("nograph", with_graphify=False)
        result = {p["name"]: p for p in detect_state.detect_projects(self.projetos, self.vault, ())}
        self.assertTrue(result["withgrap"]["has_graphify_out"])
        self.assertFalse(result["nograph"]["has_graphify_out"])

    def test_detects_existing_symlink(self):
        self._make_project("linked", with_graphify=True, linked=True)
        result = {p["name"]: p for p in detect_state.detect_projects(self.projetos, self.vault, ())}
        self.assertTrue(result["linked"]["already_linked"])

    def test_ignores_hidden_dirs(self):
        (self.projetos / ".hidden").mkdir()
        result = detect_state.detect_projects(self.projetos, self.vault, ())
        self.assertEqual(result, [])

    def test_handles_project_names_with_spaces(self):
        self._make_project("Trade Agent", with_graphify=True)
        self._make_project("KPI Tree")
        result = detect_state.detect_projects(self.projetos, self.vault, ())
        names = [p["name"] for p in result]
        self.assertIn("Trade Agent", names)
        self.assertIn("KPI Tree", names)


class TestDetectPlugins(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self.tmp.name)
        self.lock = {
            "plugins": [
                {
                    "id": "fakeplugin",
                    "folder": "fakeplugin",
                    "repo": "x/y",
                    "version": "1.0.0",
                    "assets": ["main.js"],
                    "required": True,
                    "config_example": None,
                }
            ]
        }

    def tearDown(self):
        self.tmp.cleanup()

    def _write_manifest(self, folder: str, version: str):
        d = self.vault / ".obsidian" / "plugins" / folder
        d.mkdir(parents=True)
        (d / "manifest.json").write_text(json.dumps({"id": folder, "version": version}))

    def test_plugin_not_installed(self):
        result = detect_state.detect_plugins(self.vault, self.lock)
        self.assertEqual(result[0]["installed_version"], None)
        self.assertFalse(result[0]["matches"])

    def test_plugin_installed_matching_version(self):
        self._write_manifest("fakeplugin", "1.0.0")
        result = detect_state.detect_plugins(self.vault, self.lock)
        self.assertEqual(result[0]["installed_version"], "1.0.0")
        self.assertTrue(result[0]["matches"])

    def test_plugin_installed_wrong_version(self):
        self._write_manifest("fakeplugin", "0.9.0")
        result = detect_state.detect_plugins(self.vault, self.lock)
        self.assertEqual(result[0]["installed_version"], "0.9.0")
        self.assertFalse(result[0]["matches"])

    def test_real_lock_loads(self):
        """The actual plugins.lock.json shipped in the repo must be loadable."""
        lock = detect_state.load_lock(REPO_ROOT)
        self.assertGreater(len(lock["plugins"]), 0)
        for p in lock["plugins"]:
            self.assertIn("id", p)
            self.assertIn("folder", p)
            self.assertIn("repo", p)
            self.assertIn("version", p)


if __name__ == "__main__":
    unittest.main()
