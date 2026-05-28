"""Tests for scripts/pendencia/slug.py -- normalize slug + conflict resolution."""

import tempfile
import unittest
from pathlib import Path

from tests._helpers import load_pendencia_module

slug_mod = load_pendencia_module("slug", "slug")


class TestNormalize(unittest.TestCase):
    def test_lowercase(self):
        self.assertEqual(slug_mod.normalize("OauthApple"), "oauthapple")

    def test_spaces_become_dash(self):
        self.assertEqual(slug_mod.normalize("login google"), "login-google")

    def test_accents_stripped(self):
        self.assertEqual(slug_mod.normalize("integracao acores"), "integracao-acores")

    def test_special_chars_removed(self):
        self.assertEqual(slug_mod.normalize("fix bug #42!"), "fix-bug-42")

    def test_collapses_multiple_dashes(self):
        self.assertEqual(slug_mod.normalize("a -- b"), "a-b")

    def test_strips_leading_trailing_dash(self):
        self.assertEqual(slug_mod.normalize("- hello -"), "hello")

    def test_empty_input_raises(self):
        with self.assertRaises(ValueError):
            slug_mod.normalize("")

    def test_only_invalid_chars_raises(self):
        with self.assertRaises(ValueError):
            slug_mod.normalize("!!!")


class TestResolveConflict(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_conflict_returns_same(self):
        self.assertEqual(slug_mod.resolve_conflict(self.dir, "oauth"), "oauth")

    def test_one_conflict_returns_2(self):
        (self.dir / "oauth").mkdir()
        self.assertEqual(slug_mod.resolve_conflict(self.dir, "oauth"), "oauth-2")

    def test_multiple_conflicts_increments(self):
        (self.dir / "oauth").mkdir()
        (self.dir / "oauth-2").mkdir()
        (self.dir / "oauth-3").mkdir()
        self.assertEqual(slug_mod.resolve_conflict(self.dir, "oauth"), "oauth-4")


if __name__ == "__main__":
    unittest.main()
