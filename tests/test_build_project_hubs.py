"""Tests for scripts/build_project_hubs.py — hub por projeto + contagem real de nodes do grafo."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tests._helpers import load_script_module

hubs = load_script_module("build_project_hubs", "build_project_hubs")


class TestCountGraphNodes(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.project = Path(self.tmp.name) / "MeuProjeto"
        (self.project / "graphify-out").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def write_graph(self, payload):
        path = self.project / "graphify-out" / "graph.json"
        path.write_text(json.dumps(payload) if not isinstance(payload, str) else payload)

    def test_counts_nodes_from_graph_json(self):
        self.write_graph({"nodes": [{"id": "a"}, {"id": "b"}, {"id": "c"}], "links": []})
        self.assertEqual(hubs.count_graph_nodes(self.project), 3)

    def test_empty_graph_counts_zero(self):
        self.write_graph({"nodes": [], "links": []})
        self.assertEqual(hubs.count_graph_nodes(self.project), 0)

    def test_missing_graph_json_returns_none(self):
        self.assertIsNone(hubs.count_graph_nodes(self.project))

    def test_malformed_json_returns_none(self):
        self.write_graph("{nao e json valido")
        self.assertIsNone(hubs.count_graph_nodes(self.project))

    def test_missing_nodes_key_returns_none(self):
        self.write_graph({"links": []})
        self.assertIsNone(hubs.count_graph_nodes(self.project))

    def test_nodes_not_a_list_returns_none(self):
        self.write_graph({"nodes": 42})
        self.assertIsNone(hubs.count_graph_nodes(self.project))

    def test_truncated_json_returns_none(self):
        """graph.json corrompido pelo graphify (visto em Trade Agent: string nao
        terminada no meio do arquivo) nao pode derrubar a geracao do hub."""
        self.write_graph('{"nodes": [{"id": "a"}, {"id": "b,\n  ,\n  "community": 1}]}')
        self.assertIsNone(hubs.count_graph_nodes(self.project))


class TestBuildHubContent(unittest.TestCase):
    def test_includes_graph_nodes_when_known(self):
        content = hubs.build_hub_content("MeuProjeto", [Path("a.md")], graph_nodes=673)
        self.assertIn("graph_nodes: 673", content)
        self.assertIn("notes_count: 1", content)

    def test_omits_graph_nodes_when_unknown(self):
        content = hubs.build_hub_content("MeuProjeto", [Path("a.md")], graph_nodes=None)
        self.assertNotIn("graph_nodes", content)
        self.assertIn("notes_count: 1", content)

    def test_zero_graph_nodes_is_written(self):
        content = hubs.build_hub_content("MeuProjeto", [], graph_nodes=0)
        self.assertIn("graph_nodes: 0", content)


class TestMakeProjectHub(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.project = self.base / "MeuProjeto"
        self.vault = self.project / "graphify-out" / "obsidian"
        self.vault.mkdir(parents=True)
        (self.vault / "nota-um.md").write_text("# um")
        (self.vault / "nota-dois.md").write_text("# dois")

    def tearDown(self):
        self.tmp.cleanup()

    def hub_text(self):
        return (self.project / "notes" / "MeuProjeto-hub.md").read_text()

    def test_hub_carries_real_node_count(self):
        (self.project / "graphify-out" / "graph.json").write_text(
            json.dumps({"nodes": [{"id": str(i)} for i in range(7)], "links": []})
        )
        self.assertTrue(hubs.make_project_hub("MeuProjeto", self.base))
        text = self.hub_text()
        self.assertIn("graph_nodes: 7", text)
        self.assertIn("notes_count: 2", text)

    def test_hub_without_graph_json_has_no_graph_nodes(self):
        self.assertTrue(hubs.make_project_hub("MeuProjeto", self.base))
        self.assertNotIn("graph_nodes", self.hub_text())


if __name__ == "__main__":
    unittest.main()
