"""Tests for scripts/update_hub_frontmatter.py — auto-detect logic."""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from tests._helpers import REPO_ROOT

# This script is at scripts/ root (not scripts/init/), load explicitly
SPEC = importlib.util.spec_from_file_location(
    "update_hub_frontmatter", REPO_ROOT / "scripts" / "update_hub_frontmatter.py"
)
upd = importlib.util.module_from_spec(SPEC)
sys.modules["update_hub_frontmatter"] = upd
SPEC.loader.exec_module(upd)


class TestDetectStack(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _file(self, rel: str):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("dummy")

    def test_empty_dir_returns_empty(self):
        self.assertEqual(upd.detect_stack(self.root), [])

    def test_missing_dir_returns_empty(self):
        self.assertEqual(upd.detect_stack(self.root / "nonexistent"), [])

    def test_python_project(self):
        for i in range(5):
            self._file(f"src/m{i}.py")
        self.assertEqual(upd.detect_stack(self.root), ["PY"])

    def test_top_n_by_count(self):
        for i in range(10):
            self._file(f"a{i}.swift")
        for i in range(3):
            self._file(f"b{i}.kt")
        for i in range(1):
            self._file(f"c{i}.html")
        result = upd.detect_stack(self.root, top_n=2)
        self.assertEqual(result, ["SW", "KT"])

    def test_excludes_node_modules(self):
        # 10 JS files inside node_modules — should be ignored
        for i in range(10):
            self._file(f"node_modules/pkg/m{i}.js")
        # 1 file outside — should be counted
        self._file("src/index.js")
        result = upd.detect_stack(self.root)
        self.assertEqual(result, ["JS"])
        # only counted the 1 outside; if counts mattered we'd verify

    def test_excludes_git_dir(self):
        for i in range(10):
            self._file(f".git/objects/x{i}.py")
        self.assertEqual(upd.detect_stack(self.root), [])

    def test_tsx_recognized_as_ts(self):
        self._file("a.tsx")
        self._file("b.ts")
        self.assertIn("TS", upd.detect_stack(self.root))


class TestDetectDescription(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_readme(self):
        self.assertEqual(upd.detect_description(self.root), "")

    def test_simple_readme(self):
        (self.root / "README.md").write_text("# Title\n\nA cool project for X. More details.\n")
        result = upd.detect_description(self.root)
        self.assertEqual(result, "A cool project for X")

    def test_readme_with_frontmatter(self):
        (self.root / "README.md").write_text(
            "---\nfoo: bar\n---\n\n# Title\n\nReal description here.\n"
        )
        self.assertEqual(upd.detect_description(self.root), "Real description here")

    def test_readme_only_headings(self):
        (self.root / "README.md").write_text("# Title\n\n## Subtitle\n\n### More\n")
        self.assertEqual(upd.detect_description(self.root), "")

    def test_truncates_long(self):
        long = "X" * 200
        (self.root / "README.md").write_text(f"# T\n\n{long}\n")
        result = upd.detect_description(self.root, max_len=50)
        self.assertEqual(len(result), 50)

    def test_strips_markdown_emphasis(self):
        (self.root / "README.md").write_text("# T\n\n**Bold** and `code` and [link](http://x).\n")
        result = upd.detect_description(self.root)
        # Asterisks and backticks gone; link text preserved
        self.assertNotIn("*", result)
        self.assertNotIn("`", result)
        self.assertIn("link", result)
        self.assertNotIn("http", result)

    def test_lowercase_readme(self):
        (self.root / "readme.md").write_text("# T\n\nLowercase readme works.\n")
        self.assertEqual(upd.detect_description(self.root), "Lowercase readme works")


class TestDetectColor(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(upd.detect_color("foo"), upd.detect_color("foo"))

    def test_returns_valid_color(self):
        for name in ("CV", "Housi", "claude-brain", "x", ""):
            self.assertIn(upd.detect_color(name), upd.COLOR_PALETTE)

    def test_different_names_can_differ(self):
        # Not guaranteed but extremely likely across 20 random names
        colors = {upd.detect_color(f"proj{i}") for i in range(20)}
        self.assertGreater(len(colors), 1)


class TestAutodetect(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.projetos = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_full_detection(self):
        proj = self.projetos / "MyProj"
        proj.mkdir()
        (proj / "main.py").write_text("x=1")
        (proj / "helper.py").write_text("y=2")
        (proj / "README.md").write_text("# Foo\n\nDoes X for Y.\n")
        result = upd.autodetect("MyProj", self.projetos)
        self.assertEqual(result["stack"], ["PY"])
        self.assertEqual(result["description"], "Does X for Y")
        self.assertIn(result["color"], upd.COLOR_PALETTE)

    def test_empty_project_safe_defaults(self):
        proj = self.projetos / "Empty"
        proj.mkdir()
        result = upd.autodetect("Empty", self.projetos)
        self.assertEqual(result["stack"], [])
        self.assertEqual(result["description"], "(sem descricao)")
        self.assertIn(result["color"], upd.COLOR_PALETTE)


class TestYamlScalar(unittest.TestCase):
    """yaml_scalar e usado pra escapar values no frontmatter — testa edge cases."""

    def test_basic_string(self):
        self.assertEqual(upd.yaml_scalar("foo"), '"foo"')

    def test_string_with_quotes(self):
        # Must produce valid YAML (JSON-encoded strings are valid YAML)
        self.assertEqual(upd.yaml_scalar('he said "hi"'), '"he said \\"hi\\""')

    def test_list(self):
        self.assertEqual(upd.yaml_scalar(["PY", "JS"]), '["PY", "JS"]')

    def test_empty_list(self):
        self.assertEqual(upd.yaml_scalar([]), "[]")


if __name__ == "__main__":
    unittest.main()
