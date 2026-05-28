"""Tests for scripts/pendencia/classify.py — classify by file presence."""

import tempfile
import unittest
from pathlib import Path

from tests._helpers import load_pendencia_module

classify = load_pendencia_module("classify", "classify")


class TestClassify(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _touch(self, *names):
        for n in names:
            (self.dir / n).write_text("")

    def test_empty_folder_is_invalid(self):
        self.assertEqual(classify.classify_pendencia(self.dir), "invalid")

    def test_only_spec_is_aberta(self):
        self._touch("spec.md")
        self.assertEqual(classify.classify_pendencia(self.dir), "aberta")

    def test_spec_and_task_is_planejamento(self):
        self._touch("spec.md", "task.md")
        self.assertEqual(classify.classify_pendencia(self.dir), "planejamento")

    def test_spec_task_tests_is_pronta(self):
        self._touch("spec.md", "task.md", "tests.md")
        self.assertEqual(classify.classify_pendencia(self.dir), "pronta")

    def test_all_four_is_realizada(self):
        self._touch("spec.md", "task.md", "tests.md", "resultado.md")
        self.assertEqual(classify.classify_pendencia(self.dir), "realizada")

    def test_task_without_spec_is_invalid(self):
        self._touch("task.md")
        self.assertEqual(classify.classify_pendencia(self.dir), "invalid")

    def test_resultado_without_tests_is_invalid(self):
        self._touch("spec.md", "task.md", "resultado.md")
        self.assertEqual(classify.classify_pendencia(self.dir), "invalid")

    def test_next_stage_aberta_returns_task(self):
        self._touch("spec.md")
        self.assertEqual(classify.next_stage(self.dir), "task")

    def test_next_stage_planejamento_returns_tests(self):
        self._touch("spec.md", "task.md")
        self.assertEqual(classify.next_stage(self.dir), "tests")

    def test_next_stage_pronta_returns_implement(self):
        self._touch("spec.md", "task.md", "tests.md")
        self.assertEqual(classify.next_stage(self.dir), "implement")

    def test_next_stage_realizada_returns_done(self):
        self._touch("spec.md", "task.md", "tests.md", "resultado.md")
        self.assertEqual(classify.next_stage(self.dir), "done")

    def test_next_stage_invalid_raises(self):
        with self.assertRaises(ValueError):
            classify.next_stage(self.dir)

    def test_classify_project_lists_all_pendencias(self):
        proj = self.dir / "Pendencias"
        proj.mkdir()
        (proj / "a").mkdir()
        (proj / "a" / "spec.md").write_text("")
        (proj / "b").mkdir()
        (proj / "b" / "spec.md").write_text("")
        (proj / "b" / "task.md").write_text("")
        (proj / "legado.md").write_text("")

        result = classify.classify_project_pendencias(proj)
        self.assertEqual(result, {
            "a": "aberta",
            "b": "planejamento",
        })

    def test_classify_project_counts_legado(self):
        proj = self.dir / "Pendencias"
        proj.mkdir()
        (proj / "legado1.md").write_text("")
        (proj / "legado2.md").write_text("")
        (proj / "a").mkdir()
        (proj / "a" / "spec.md").write_text("")

        self.assertEqual(classify.count_legado(proj), 2)


if __name__ == "__main__":
    unittest.main()
