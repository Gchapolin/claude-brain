"""Tests for scripts/init/link_claude_memory.sh — memoria do harness no iCloud via symlink."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests._helpers import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "init" / "link_claude_memory.sh"


class TestLinkClaudeMemory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.icloud = root / "ClaudeBrain-Mobile"
        self.icloud.mkdir()
        self.mem = self.icloud / "_claude-memory"
        self.projects = root / "projects"
        self.projects.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, *extra):
        return subprocess.run(
            ["bash", str(SCRIPT), str(self.icloud), str(self.projects), *extra],
            capture_output=True, text=True,
        )

    def _icloud_project(self, name, files):
        d = self.mem / name
        d.mkdir(parents=True)
        for fname, content in files.items():
            (d / fname).write_text(content)
        return d

    def _local_project(self, name, files):
        d = self.projects / name / "memory"
        d.mkdir(parents=True)
        for fname, content in files.items():
            (d / fname).write_text(content)
        return d

    def test_script_exists_and_is_executable(self):
        self.assertTrue(SCRIPT.is_file(), SCRIPT)
        self.assertTrue(os.access(SCRIPT, os.X_OK), "precisa ser executavel")

    def test_creates_symlink_for_icloud_dir_without_local(self):
        target = self._icloud_project("-Users-x-PROJETOS-A", {"MEMORY.md": "# A"})
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        link = self.projects / "-Users-x-PROJETOS-A" / "memory"
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.resolve(), target.resolve())
        self.assertEqual((link / "MEMORY.md").read_text(), "# A")

    def test_idempotent_second_run_changes_nothing(self):
        self._icloud_project("-Users-x-PROJETOS-A", {"MEMORY.md": "# A"})
        self.run_script()
        link = self.projects / "-Users-x-PROJETOS-A" / "memory"
        before = os.readlink(link)
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(os.readlink(link), before)
        self.assertNotIn("MIGRADO", r.stdout)

    def test_local_real_dir_is_merged_and_replaced_by_symlink(self):
        self._icloud_project("-Users-x-PROJETOS-A", {"MEMORY.md": "icloud", "so-icloud.md": "i"})
        self._local_project("-Users-x-PROJETOS-A", {"MEMORY.md": "local", "so-local.md": "l"})
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        link = self.projects / "-Users-x-PROJETOS-A" / "memory"
        self.assertTrue(link.is_symlink())
        # arquivo so local foi levado pro iCloud
        self.assertEqual((self.mem / "-Users-x-PROJETOS-A" / "so-local.md").read_text(), "l")
        # em conflito, a copia do iCloud vence
        self.assertEqual((self.mem / "-Users-x-PROJETOS-A" / "MEMORY.md").read_text(), "icloud")
        self.assertTrue((self.mem / "-Users-x-PROJETOS-A" / "so-icloud.md").exists())

    def test_local_dir_without_icloud_counterpart_is_migrated(self):
        self._local_project("-Users-x-PROJETOS-Novo", {"MEMORY.md": "novo"})
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((self.mem / "-Users-x-PROJETOS-Novo" / "MEMORY.md").read_text(), "novo")
        link = self.projects / "-Users-x-PROJETOS-Novo" / "memory"
        self.assertTrue(link.is_symlink())
        self.assertIn("MIGRADO", r.stdout)

    def test_dry_run_changes_nothing(self):
        self._icloud_project("-Users-x-PROJETOS-A", {"MEMORY.md": "# A"})
        self._local_project("-Users-x-PROJETOS-Novo", {"MEMORY.md": "novo"})
        r = self.run_script("--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.projects / "-Users-x-PROJETOS-A").exists())
        self.assertFalse((self.projects / "-Users-x-PROJETOS-Novo" / "memory").is_symlink())
        self.assertFalse((self.mem / "-Users-x-PROJETOS-Novo").exists())
        self.assertIn("DRY", r.stdout)

    def test_missing_memory_root_is_created(self):
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.mem.is_dir())

    def test_missing_icloud_dir_fails(self):
        r = subprocess.run(
            ["bash", str(SCRIPT), str(self.icloud / "nao-existe"), str(self.projects)],
            capture_output=True, text=True,
        )
        self.assertNotEqual(r.returncode, 0)

    def test_ignores_non_project_entries_in_memory_root(self):
        self.mem.mkdir()
        (self.mem / "README.md").write_text("doc")
        (self.mem / "pasta-sem-prefixo").mkdir()
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(list(self.projects.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
