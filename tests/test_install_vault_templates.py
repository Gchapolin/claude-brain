"""Tests for scripts/install-vault-templates.sh — deploy dos templates do repo pro vault vivo."""

import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tests._helpers import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "install-vault-templates.sh"

ICLOUD_FILES = ("Index.md", "Capturar.md", "Templates/Captura.md")
MAC_FILES = (".obsidian/snippets/brain-hub.css",)
ALL_FILES = ICLOUD_FILES + MAC_FILES


class TestInstallVaultTemplates(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        root = Path(self.tmp.name)
        self.icloud = root / "ClaudeBrain-Mobile"
        self.icloud.mkdir()
        self.mac_vault = root / "ClaudeBrain"
        self.mac_vault.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, *extra, icloud=None, mac_vault=None):
        env = {
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
            "HOME": self.tmp.name,
            "ICLOUD": str(icloud if icloud is not None else self.icloud),
            "MAC_VAULT": str(mac_vault if mac_vault is not None else self.mac_vault),
        }
        return subprocess.run(
            ["bash", str(SCRIPT), *extra],
            capture_output=True, text=True, env=env,
        )

    def dest_for(self, rel):
        base = self.mac_vault if rel in MAC_FILES else self.icloud
        return base / rel

    def source_for(self, rel):
        return REPO_ROOT / "vault" / rel

    def backups(self):
        found = []
        for base in (self.icloud, self.mac_vault):
            found.extend(p for p in base.rglob("*.bak-*"))
        return found

    def test_fresh_deploy_copies_all_files(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        for rel in ALL_FILES:
            dest = self.dest_for(rel)
            self.assertTrue(dest.exists(), f"{rel} nao foi copiado")
            self.assertEqual(
                dest.read_text(encoding="utf-8"),
                self.source_for(rel).read_text(encoding="utf-8"),
                f"{rel} difere da fonte",
            )
        self.assertIn("NOVO", result.stdout)

    def test_second_run_is_noop(self):
        self.run_script()
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("NOVO", result.stdout)
        self.assertNotIn("ATUALIZADO", result.stdout)
        self.assertEqual(result.stdout.count("OK"), len(ALL_FILES))
        self.assertEqual(self.backups(), [], "run idempotente nao deve criar backup")

    def test_divergent_file_is_backed_up_and_updated(self):
        self.run_script()
        dest = self.dest_for("Index.md")
        dest.write_text("conteudo antigo do vault\n", encoding="utf-8")

        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ATUALIZADO", result.stdout)
        self.assertEqual(
            dest.read_text(encoding="utf-8"),
            self.source_for("Index.md").read_text(encoding="utf-8"),
        )
        baks = self.backups()
        self.assertEqual(len(baks), 1, f"esperado 1 backup, veio {baks}")
        self.assertEqual(baks[0].read_text(encoding="utf-8"), "conteudo antigo do vault\n")

    def test_dry_run_writes_nothing(self):
        dest = self.dest_for("Index.md")
        dest.write_text("conteudo antigo do vault\n", encoding="utf-8")

        result = self.run_script("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DRY", result.stdout)
        self.assertEqual(dest.read_text(encoding="utf-8"), "conteudo antigo do vault\n")
        self.assertEqual(self.backups(), [])
        for rel in ALL_FILES:
            if rel == "Index.md":
                continue
            self.assertFalse(self.dest_for(rel).exists(), f"{rel} foi escrito em dry-run")

    def test_missing_destination_root_fails(self):
        result = self.run_script(icloud=Path(self.tmp.name) / "nao-existe")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ERRO", result.stderr)

    def test_dry_run_exit_code_signals_drift(self):
        """--dry-run --check sai 1 quando ha divergencia (pro drift check do update)."""
        self.run_script()
        self.dest_for("Index.md").write_text("divergente\n", encoding="utf-8")
        drifted = self.run_script("--dry-run", "--check")
        self.assertEqual(drifted.returncode, 1)

        self.run_script()
        clean = self.run_script("--dry-run", "--check")
        self.assertEqual(clean.returncode, 0, clean.stderr)


if __name__ == "__main__":
    unittest.main()
