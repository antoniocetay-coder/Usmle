import unittest
import json
import tempfile
import os
import csv

from knowledge_graph import KnowledgeGraph
from centrality import (
    calculate_degree_centrality,
    calculate_pagerank,
    calculate_betweenness,
    CentralityAnalyzer,
)

SAMPLE = {
    "STEMI": ["Coronary Circulation", "Cardiac Action Potential"],
    "WPW Syndrome": ["Cardiac Action Potential", "AV Node"],
    "RareConcept": [],
    "ECG": ["Cardiac Action Potential"],
    "Arrhythmias": ["ECG"],
    "Antiarrhythmics": ["Arrhythmias"],
}


class TestCentralityFunctions(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json")
        json.dump(SAMPLE, cls.tmp)
        cls.tmp.close()
        cls.kg = KnowledgeGraph(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.tmp.name)

    # ── Scores entre 0 e 1 ─────────────────────────────────────────────
    def test_degree_scores_in_range(self):
        scores = calculate_degree_centrality(self.kg.graph)
        for v in scores.values():
            self.assertGreaterEqual(v, 0)
            self.assertLessEqual(v, 1)

    def test_pagerank_scores_in_range(self):
        scores = calculate_pagerank(self.kg.graph)
        for v in scores.values():
            self.assertGreaterEqual(v, 0)
            self.assertLessEqual(v, 1)

    def test_betweenness_scores_in_range(self):
        scores = calculate_betweenness(self.kg.graph)
        for v in scores.values():
            self.assertGreaterEqual(v, 0)
            self.assertLessEqual(v, 1)

    # ── Todos os nós aparecem ──────────────────────────────────────────
    def test_all_nodes_in_degree(self):
        scores = calculate_degree_centrality(self.kg.graph)
        for node in self.kg.graph.nodes:
            self.assertIn(node, scores)

    def test_all_nodes_in_pagerank(self):
        scores = calculate_pagerank(self.kg.graph)
        for node in self.kg.graph.nodes:
            self.assertIn(node, scores)

    def test_all_nodes_in_betweenness(self):
        scores = calculate_betweenness(self.kg.graph)
        for node in self.kg.graph.nodes:
            self.assertIn(node, scores)

    # ── Cardio Action Potential é central (degree + pagerank) ──────────
    def test_cardiac_is_top_degree(self):
        scores = calculate_degree_centrality(self.kg.graph)
        cap = scores.get("Cardiac Action Potential", 0)
        avg = sum(scores.values()) / len(scores)
        self.assertGreater(cap, avg)

    def test_cardiac_is_top_pagerank(self):
        scores = calculate_pagerank(self.kg.graph)
        total = sum(scores.values())
        self.assertAlmostEqual(total, 1.0, places=2)

    # ── Nó isolado tem scores baixos ───────────────────────────────────
    def test_isolated_low_degree(self):
        scores = calculate_degree_centrality(self.kg.graph)
        self.assertLess(scores.get("RareConcept", 1), 0.1)

    def test_isolated_low_pagerank(self):
        scores = calculate_pagerank(self.kg.graph)
        self.assertLess(scores.get("RareConcept", 1), 0.1)

    def test_isolated_low_betweenness(self):
        scores = calculate_betweenness(self.kg.graph)
        self.assertEqual(scores.get("RareConcept", -1), 0)


class TestCentralityAnalyzer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json")
        json.dump(SAMPLE, cls.tmp)
        cls.tmp.close()
        cls.kg = KnowledgeGraph(cls.tmp.name)
        cls.analyzer = CentralityAnalyzer(cls.kg)

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.tmp.name)

    # ── Rankings ordenados ─────────────────────────────────────────────
    def test_top_by_degree_ordered(self):
        top = self.analyzer.top_by_degree(5)
        for i in range(len(top) - 1):
            self.assertGreaterEqual(top[i][1], top[i + 1][1])

    def test_top_by_pagerank_ordered(self):
        top = self.analyzer.top_by_pagerank(5)
        for i in range(len(top) - 1):
            self.assertGreaterEqual(top[i][1], top[i + 1][1])

    def test_top_by_betweenness_ordered(self):
        top = self.analyzer.top_by_betweenness(5)
        for i in range(len(top) - 1):
            self.assertGreaterEqual(top[i][1], top[i + 1][1])

    # ── Tamanho do ranking ─────────────────────────────────────────────
    def test_top_n_respected(self):
        self.assertEqual(len(self.analyzer.top_by_degree(3)), 3)
        self.assertLessEqual(len(self.analyzer.top_by_pagerank(10)), 10)
        self.assertEqual(len(self.analyzer.top_by_betweenness(3)), 3)

    # ── Acesso individual ──────────────────────────────────────────────
    def test_degree_individual(self):
        s = self.analyzer.degree("Cardiac Action Potential")
        self.assertGreater(s, 0)

    def test_pagerank_individual(self):
        s = self.analyzer.pagerank("Cardiac Action Potential")
        self.assertGreater(s, 0)

    def test_betweenness_individual(self):
        s = self.analyzer.betweenness("Cardiac Action Potential")
        self.assertGreaterEqual(s, 0)

    # ── CSV export ─────────────────────────────────────────────────────
    def test_csv_export(self):
        path = tempfile.mktemp(suffix=".csv")
        self.analyzer.export_metrics_csv(path)
        with open(path, newline="", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
        os.unlink(path)
        self.assertTrue(len(reader) > 0)
        row = reader[0]
        for field in ["concept", "degree", "pagerank", "betweenness",
                       "descendants", "depth"]:
            self.assertIn(field, row)

    # ── Summary ────────────────────────────────────────────────────────
    def test_summary_has_keys(self):
        s = self.analyzer.generate_summary()
        for key in ["graph_nodes", "graph_edges",
                     "highest_degree", "highest_pagerank",
                     "highest_betweenness"]:
            self.assertIn(key, s)

    def test_summary_counts(self):
        s = self.analyzer.generate_summary()
        self.assertEqual(s["graph_nodes"], self.kg.graph.number_of_nodes())

    def test_summary_top10(self):
        s = self.analyzer.generate_summary()
        for key in ["highest_degree", "highest_pagerank", "highest_betweenness"]:
            self.assertLessEqual(len(s[key]), 10)


if __name__ == "__main__":
    unittest.main()
