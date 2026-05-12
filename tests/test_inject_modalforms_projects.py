"""Tests for scripts/init/inject_modalforms_projects.py — replace and add modes."""

import json
import tempfile
import unittest
from pathlib import Path

from tests._helpers import load_module

inject = load_module("inject_modalforms_projects", "inject_modalforms_projects")

BASE_FORM = {
    "formDefinitions": [
        {
            "name": "capturar-nota",
            "fields": [
                {
                    "name": "projeto",
                    "input": {
                        "type": "select",
                        "source": "fixed",
                        "options": [
                            {"value": "Old1", "label": "Old1"},
                            {"value": "geral", "label": "(geral, sem projeto)"},
                        ],
                    },
                }
            ],
        }
    ]
}


class TestReplaceMode(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self.tmp.name)
        self.data_json = self.vault / ".obsidian" / "plugins" / "modalforms" / "data.json"
        self.data_json.parent.mkdir(parents=True)
        self.data_json.write_text(json.dumps(BASE_FORM))

    def tearDown(self):
        self.tmp.cleanup()

    def test_replace_overwrites_existing_options(self):
        data, field = inject.find_field(self.data_json)
        inject.apply_replace(field, ["CV", "Housi"])
        self.data_json.write_text(json.dumps(data))
        result = json.loads(self.data_json.read_text())
        opts = result["formDefinitions"][0]["fields"][0]["input"]["options"]
        values = [o["value"] for o in opts]
        self.assertEqual(values, ["CV", "Housi", "geral"])

    def test_replace_is_idempotent(self):
        data, field = inject.find_field(self.data_json)
        changed1, _ = inject.apply_replace(field, ["CV", "Housi"])
        self.assertTrue(changed1)
        changed2, _ = inject.apply_replace(field, ["CV", "Housi"])
        self.assertFalse(changed2)


class TestAddMode(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self.tmp.name)
        self.data_json = self.vault / ".obsidian" / "plugins" / "modalforms" / "data.json"
        self.data_json.parent.mkdir(parents=True)
        self.data_json.write_text(json.dumps(BASE_FORM))

    def tearDown(self):
        self.tmp.cleanup()

    def test_add_preserves_existing(self):
        data, field = inject.find_field(self.data_json)
        inject.apply_add(field, ["New1"])
        values = [o["value"] for o in field["input"]["options"]]
        self.assertEqual(values, ["Old1", "New1", "geral"])

    def test_add_skips_duplicates(self):
        data, field = inject.find_field(self.data_json)
        changed1, _ = inject.apply_add(field, ["New1"])
        self.assertTrue(changed1)
        changed2, _ = inject.apply_add(field, ["New1"])
        self.assertFalse(changed2)

    def test_add_handles_names_with_spaces(self):
        data, field = inject.find_field(self.data_json)
        inject.apply_add(field, ["Trade Agent", "KPI Tree"])
        values = [o["value"] for o in field["input"]["options"]]
        self.assertIn("Trade Agent", values)
        self.assertIn("KPI Tree", values)
        # geral remains last
        self.assertEqual(values[-1], "geral")

    def test_add_keeps_geral_at_end(self):
        data, field = inject.find_field(self.data_json)
        inject.apply_add(field, ["A", "B", "C"])
        values = [o["value"] for o in field["input"]["options"]]
        self.assertEqual(values[-1], "geral")


class TestParseProjects(unittest.TestCase):
    def test_comma_separated(self):
        import argparse
        ns = argparse.Namespace(projects="CV, Housi ,SmartScore", projects_json=None)
        self.assertEqual(inject.parse_projects(ns), ["CV", "Housi", "SmartScore"])

    def test_json_list(self):
        import argparse
        ns = argparse.Namespace(projects=None, projects_json='["Trade Agent","KPI Tree"]')
        self.assertEqual(inject.parse_projects(ns), ["Trade Agent", "KPI Tree"])

    def test_json_rejects_non_list(self):
        import argparse
        ns = argparse.Namespace(projects=None, projects_json='{"not":"list"}')
        with self.assertRaises(ValueError):
            inject.parse_projects(ns)


class TestFindFieldErrors(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "data.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_form_name(self):
        self.path.write_text(json.dumps({"formDefinitions": [{"name": "other", "fields": []}]}))
        with self.assertRaises(ValueError):
            inject.find_field(self.path)

    def test_missing_field_name(self):
        self.path.write_text(
            json.dumps(
                {"formDefinitions": [{"name": "capturar-nota", "fields": [{"name": "outro"}]}]}
            )
        )
        with self.assertRaises(ValueError):
            inject.find_field(self.path)


if __name__ == "__main__":
    unittest.main()
