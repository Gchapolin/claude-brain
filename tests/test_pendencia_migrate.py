"""Tests for scripts/pendencia/migrate.py — convert legacy .md to folder/spec.md."""

import tempfile
import unittest
from pathlib import Path

from tests._helpers import load_pendencia_module

migrate = load_pendencia_module("migrate", "migrate")


class TestMigrate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pendencias = Path(self.tmp.name) / "Pendencias"
        self.pendencias.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_plan_lists_legado_files(self):
        (self.pendencias / "login-google.md").write_text("conteudo")
        (self.pendencias / "fix-bug.md").write_text("outro")
        plan = migrate.plan_migration(self.pendencias, project="HMA")
        slugs = sorted(item["slug"] for item in plan)
        self.assertEqual(slugs, ["fix-bug", "login-google"])

    def test_plan_normalizes_slug(self):
        (self.pendencias / "Login Google.md").write_text("x")
        plan = migrate.plan_migration(self.pendencias, project="HMA")
        self.assertEqual(plan[0]["slug"], "login-google")

    def test_plan_ignores_existing_folders(self):
        (self.pendencias / "already-migrated").mkdir()
        (self.pendencias / "already-migrated" / "spec.md").write_text("x")
        (self.pendencias / "loose.md").write_text("y")
        plan = migrate.plan_migration(self.pendencias, project="HMA")
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["slug"], "loose")

    def test_plan_resolves_conflicts(self):
        (self.pendencias / "dup").mkdir()
        (self.pendencias / "dup.md").write_text("x")
        plan = migrate.plan_migration(self.pendencias, project="HMA")
        self.assertEqual(plan[0]["slug"], "dup-2")

    def test_apply_moves_content_into_spec(self):
        (self.pendencias / "fix.md").write_text("conteudo original\n")
        plan = migrate.plan_migration(self.pendencias, project="HMA")
        migrate.apply(plan, self.pendencias)
        spec_path = self.pendencias / "fix" / "spec.md"
        self.assertTrue(spec_path.is_file())
        content = spec_path.read_text()
        self.assertIn("conteudo original", content)
        self.assertIn("type: pendencia-spec", content)
        self.assertIn("project: HMA", content)
        self.assertIn("slug: fix", content)

    def test_apply_removes_original_after_move(self):
        (self.pendencias / "fix.md").write_text("x")
        plan = migrate.plan_migration(self.pendencias, project="HMA")
        migrate.apply(plan, self.pendencias)
        self.assertFalse((self.pendencias / "fix.md").exists())

    def test_apply_preserves_existing_frontmatter_body(self):
        original = "---\nstatus: pendente\ntags: [old]\n---\n\n# Old title\n\nbody text\n"
        (self.pendencias / "old.md").write_text(original)
        plan = migrate.plan_migration(self.pendencias, project="HMA")
        migrate.apply(plan, self.pendencias)
        spec = (self.pendencias / "old" / "spec.md").read_text()
        self.assertIn("type: pendencia-spec", spec)
        self.assertIn("# Old title", spec)
        self.assertIn("body text", spec)
        self.assertNotIn("status: pendente", spec)

    def test_apply_is_idempotent_skipping_existing(self):
        (self.pendencias / "a.md").write_text("x")
        plan1 = migrate.plan_migration(self.pendencias, project="HMA")
        migrate.apply(plan1, self.pendencias)
        plan2 = migrate.plan_migration(self.pendencias, project="HMA")
        self.assertEqual(plan2, [])

    def test_apply_dry_run_writes_nothing(self):
        (self.pendencias / "x.md").write_text("body")
        plan = migrate.plan_migration(self.pendencias, project="HMA")
        migrate.apply(plan, self.pendencias, dry_run=True)
        self.assertTrue((self.pendencias / "x.md").exists())
        self.assertFalse((self.pendencias / "x").exists())


if __name__ == "__main__":
    unittest.main()
