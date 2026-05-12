"""Tests for scripts/init/install_plugins.py — idempotency, v-prefix fallback, staging."""

import json
import tempfile
import unittest
import urllib.error
from io import BytesIO
from pathlib import Path
from unittest import mock

from tests._helpers import load_module

install_plugins = load_module("install_plugins", "install_plugins")


PLUGIN = {
    "id": "fakeplugin",
    "folder": "fakeplugin",
    "repo": "owner/repo",
    "version": "1.2.3",
    "assets": ["main.js", "manifest.json"],
    "required": True,
    "config_example": None,
}


def _http_resp(payload: bytes):
    """Return a context manager that mimics urlopen()."""
    m = mock.MagicMock()
    m.read.return_value = payload
    m.__enter__ = mock.MagicMock(return_value=m)
    m.__exit__ = mock.MagicMock(return_value=False)
    return m


class TestUrlBuilding(unittest.TestCase):
    def test_url_format(self):
        url = install_plugins.gh_release_url("owner/repo", "1.2.3", "main.js")
        self.assertEqual(url, "https://github.com/owner/repo/releases/download/1.2.3/main.js")


class TestVPrefixFallback(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dest = Path(self.tmp.name) / "main.js"

    def tearDown(self):
        self.tmp.cleanup()

    @mock.patch.object(install_plugins, "fetch")
    def test_uses_bare_version_when_ok(self, fake_fetch):
        fake_fetch.return_value = (True, b"content", 200)
        ok, msg = install_plugins.download_asset("o/r", "1.2.3", "main.js", self.dest, dry_run=False)
        self.assertTrue(ok)
        self.assertEqual(self.dest.read_bytes(), b"content")
        # Should have tried bare version only
        self.assertEqual(fake_fetch.call_count, 1)
        self.assertIn("/1.2.3/", fake_fetch.call_args[0][0])

    @mock.patch.object(install_plugins, "fetch")
    def test_falls_back_to_v_prefix_on_404(self, fake_fetch):
        fake_fetch.side_effect = [
            (False, "HTTP 404 for x", 404),  # bare
            (True, b"vcontent", 200),  # v-prefixed
        ]
        ok, msg = install_plugins.download_asset("o/r", "1.2.3", "main.js", self.dest, dry_run=False)
        self.assertTrue(ok)
        self.assertEqual(self.dest.read_bytes(), b"vcontent")
        self.assertEqual(fake_fetch.call_count, 2)
        self.assertIn("/v1.2.3/", fake_fetch.call_args_list[1][0][0])

    @mock.patch.object(install_plugins, "fetch")
    def test_both_404_fails(self, fake_fetch):
        fake_fetch.side_effect = [
            (False, "HTTP 404", 404),
            (False, "HTTP 404", 404),
        ]
        ok, msg = install_plugins.download_asset("o/r", "1.2.3", "main.js", self.dest, dry_run=False)
        self.assertFalse(ok)
        self.assertIn("404", msg)
        self.assertFalse(self.dest.exists())

    @mock.patch.object(install_plugins, "fetch")
    def test_non_404_failure_does_not_retry_v(self, fake_fetch):
        fake_fetch.return_value = (False, "timeout", None)
        ok, msg = install_plugins.download_asset("o/r", "1.2.3", "main.js", self.dest, dry_run=False)
        self.assertFalse(ok)
        # Only one attempt — no fallback on non-404
        self.assertEqual(fake_fetch.call_count, 1)


class TestInstallPluginStaging(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    @mock.patch.object(install_plugins, "fetch")
    def test_install_skips_if_version_matches(self, fake_fetch):
        folder = self.vault / ".obsidian" / "plugins" / "fakeplugin"
        folder.mkdir(parents=True)
        (folder / "manifest.json").write_text(json.dumps({"id": "fakeplugin", "version": "1.2.3"}))
        result = install_plugins.install_plugin(PLUGIN, self.vault, dry_run=False)
        self.assertEqual(result["action"], "skip")
        fake_fetch.assert_not_called()

    @mock.patch.object(install_plugins, "fetch")
    def test_install_promotes_partial_on_success(self, fake_fetch):
        fake_fetch.return_value = (True, b"x", 200)
        result = install_plugins.install_plugin(PLUGIN, self.vault, dry_run=False)
        self.assertEqual(result["action"], "install")
        folder = self.vault / ".obsidian" / "plugins" / "fakeplugin"
        partial = self.vault / ".obsidian" / "plugins" / "fakeplugin.partial"
        self.assertTrue(folder.exists())
        self.assertFalse(partial.exists())
        self.assertTrue((folder / "main.js").exists())
        self.assertTrue((folder / "manifest.json").exists())

    @mock.patch.object(install_plugins, "fetch")
    def test_install_keeps_partial_on_failure(self, fake_fetch):
        # First asset succeeds, second fails (and 404 retry also fails)
        fake_fetch.side_effect = [
            (True, b"main", 200),
            (False, "HTTP 404", 404),
            (False, "HTTP 404", 404),
        ]
        result = install_plugins.install_plugin(PLUGIN, self.vault, dry_run=False)
        self.assertEqual(result["action"], "fail")
        folder = self.vault / ".obsidian" / "plugins" / "fakeplugin"
        partial = self.vault / ".obsidian" / "plugins" / "fakeplugin.partial"
        # Real folder must NOT exist (we never promoted)
        self.assertFalse(folder.exists())
        # Partial must remain for debugging
        self.assertTrue(partial.exists())

    @mock.patch.object(install_plugins, "fetch")
    def test_install_overwrites_old_version(self, fake_fetch):
        fake_fetch.return_value = (True, b"new", 200)
        folder = self.vault / ".obsidian" / "plugins" / "fakeplugin"
        folder.mkdir(parents=True)
        (folder / "manifest.json").write_text(json.dumps({"id": "fakeplugin", "version": "0.9.0"}))
        (folder / "old-file.txt").write_text("garbage from previous version")

        result = install_plugins.install_plugin(PLUGIN, self.vault, dry_run=False)
        self.assertEqual(result["action"], "install")
        # Old garbage file should be gone (folder replaced atomically)
        self.assertFalse((folder / "old-file.txt").exists())
        self.assertTrue((folder / "main.js").exists())


class TestRealLock(unittest.TestCase):
    def test_real_plugins_lock_parses(self):
        """The shipped plugins.lock.json must load and have well-formed entries."""
        from tests._helpers import REPO_ROOT
        lock = json.loads((REPO_ROOT / "plugins.lock.json").read_text())
        self.assertIn("plugins", lock)
        for p in lock["plugins"]:
            self.assertIsInstance(p["assets"], list)
            self.assertGreater(len(p["assets"]), 0)
            self.assertIn("main.js", p["assets"])
            self.assertIn("manifest.json", p["assets"])


if __name__ == "__main__":
    unittest.main()
