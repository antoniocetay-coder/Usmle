import unittest
import json
import os
import tempfile

from knowledge_graph import KnowledgeGraph

SAMPLE = {
    "STEMI": ["Coronary Circulation", "Cardiac Action Potential"],
    "WPW Syndrome": ["Cardiac Action Potential", "AV Node"],
    "RareConcept": [],
    "ECG": ["Cardiac Action Potential"],
    "Arrhythmias": ["ECG"],
    "Antiarrhythmics": ["Arrhythmias"],
}


class TestKnowledgeGraph(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json")
        json.dump(SAMPLE, cls.tmp)
        cls.tmp.close()
        cls.kg = KnowledgeGraph(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.tmp.name)

    # ── DAG ─────────────────────────────────────────────────────────────
    def test_is_dag(self):
        import networkx as nx
        self.assertTrue(nx.is_directed_acyclic_graph(self.kg.graph))

    # ── has_concept ────────────────────────────────────────────────────
    def test_has_concept_true(self):
        self.assertTrue(self.kg.has_concept("STEMI"))

    def test_has_concept_false(self):
        self.assertFalse(self.kg.has_concept("DoesNotExist"))

    # ── Isolado ─────────────────────────────────────────────────────────
    def test_isolated_exists(self):
        self.assertTrue(self.kg.has_concept("RareConcept"))

    def test_isolated_no_parents(self):
        self.assertEqual(self.kg.get_parents("RareConcept"), [])

    def test_isolated_no_children(self):
        self.assertEqual(self.kg.get_children("RareConcept"), [])

    # ── Inexistente ─────────────────────────────────────────────────────
    def test_nonexistent_parents(self):
        self.assertEqual(self.kg.get_parents("X"), [])

    def test_nonexistent_children(self):
        self.assertEqual(self.kg.get_children("X"), [])

    def test_nonexistent_ancestors(self):
        self.assertEqual(self.kg.get_ancestors("X"), [])

    def test_nonexistent_descendants(self):
        self.assertEqual(self.kg.get_descendants("X"), [])

    # ── Parents / Children ──────────────────────────────────────────────
    def test_get_parents_stemi(self):
        p = self.kg.get_parents("STEMI")
        self.assertIn("Cardiac Action Potential", p)
        self.assertIn("Coronary Circulation", p)
        self.assertEqual(len(p), 2)

    def test_get_children_cardiac(self):
        c = self.kg.get_children("Cardiac Action Potential")
        self.assertIn("STEMI", c)
        self.assertIn("WPW Syndrome", c)
        self.assertIn("ECG", c)
        self.assertEqual(len(c), 3)

    # ── Ancestors / Descendants ─────────────────────────────────────────
    def test_ancestors_stemi(self):
        self.assertEqual(self.kg.ancestors_count("STEMI"), 2)

    def test_descendants_cardiac(self):
        self.assertEqual(self.kg.descendants_count("Cardiac Action Potential"), 5)

    def test_descendants_count_antiarrhythmics(self):
        self.assertEqual(self.kg.descendants_count("Antiarrhythmics"), 0)

    def test_ancestors_count_isolated(self):
        self.assertEqual(self.kg.ancestors_count("RareConcept"), 0)

    def test_descendants_count_isolated(self):
        self.assertEqual(self.kg.descendants_count("RareConcept"), 0)

    def test_ancestors_count_nonexistent(self):
        self.assertEqual(self.kg.ancestors_count("X"), 0)

    # ── Profundidade ────────────────────────────────────────────────────
    def test_max_depth_cardiac(self):
        self.assertEqual(self.kg.max_descendant_depth("Cardiac Action Potential"), 3)

    def test_max_depth_leaf(self):
        self.assertEqual(self.kg.max_descendant_depth("Antiarrhythmics"), 0)

    def test_max_depth_isolated(self):
        self.assertEqual(self.kg.max_descendant_depth("RareConcept"), 0)

    def test_max_depth_nonexistent(self):
        self.assertEqual(self.kg.max_descendant_depth("X"), -1)

    # ── Top ─────────────────────────────────────────────────────────────
    def test_top_concepts(self):
        top = self.kg.top_concepts_by_descendants(5)
        names = [t[0] for t in top]
        self.assertIn("Cardiac Action Potential", names)
        self.assertGreaterEqual(top[0][1], top[-1][1])

    # ── Ciclo (auto-resolvido com warning) ─────────────────────────────
    def test_cycle_auto_resolved(self):
        cyclic = {"A": ["B"], "B": ["C"], "C": ["A"]}
        tmp2 = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json")
        json.dump(cyclic, tmp2)
        tmp2.close()
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            kg = KnowledgeGraph(tmp2.name)
            self.assertTrue(len(w) >= 1)
            self.assertIn("cycle", str(w[0].message).lower())
        import networkx as nx
        self.assertTrue(nx.is_directed_acyclic_graph(kg.graph))
        os.unlink(tmp2.name)

    # ── Cache miss não quebra ───────────────────────────────────────────
    def test_cache_rebuild_on_new_instance(self):
        kg2 = KnowledgeGraph(self.tmp.name)
        self.assertEqual(kg2.descendants_count("Cardiac Action Potential"), 5)


if __name__ == "__main__":
    unittest.main()
