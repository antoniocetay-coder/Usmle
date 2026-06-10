import unittest
import json
import tempfile
import os
import csv

from knowledge_graph import KnowledgeGraph
from centrality import CentralityAnalyzer
from student_graph import StudentGraph, ConceptState

SAMPLE = {
    "STEMI": ["Coronary Circulation", "Cardiac Action Potential"],
    "WPW Syndrome": ["Cardiac Action Potential", "AV Node"],
    "RareConcept": [],
    "ECG": ["Cardiac Action Potential"],
    "Arrhythmias": ["ECG"],
    "Antiarrhythmics": ["Arrhythmias"],
}


class TestConceptState(unittest.TestCase):

    def test_default_mastery(self):
        s = ConceptState(concept_id="foo")
        self.assertEqual(s.mastery, 0.0)

    def test_default_uncertainty(self):
        s = ConceptState(concept_id="foo")
        self.assertEqual(s.uncertainty, 1.0)

    def test_default_review_due(self):
        s = ConceptState(concept_id="foo")
        self.assertFalse(s.review_due)

    def test_custom_values(self):
        from datetime import datetime
        dt = datetime(2025, 6, 1)
        s = ConceptState(concept_id="bar", mastery=0.85, uncertainty=0.3,
                         attempts=10, correct=8, confidence=0.9,
                         last_seen=dt, review_due=True)
        self.assertEqual(s.mastery, 0.85)
        self.assertEqual(s.uncertainty, 0.3)
        self.assertEqual(s.attempts, 10)
        self.assertEqual(s.correct, 8)
        self.assertEqual(s.confidence, 0.9)
        self.assertEqual(s.last_seen, dt)
        self.assertTrue(s.review_due)


class TestStudentGraphInit(unittest.TestCase):

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

    def setUp(self):
        self.sg = StudentGraph(self.kg, self.analyzer)

    def test_all_concepts_have_states(self):
        self.assertEqual(len(self.sg.states), len(self.kg.graph.nodes))

    def test_every_node_has_state(self):
        for node in self.kg.graph.nodes:
            self.assertIn(node, self.sg.states)

    def test_get_state_returns_concept_state(self):
        s = self.sg.get_state("Cardiac Action Potential")
        self.assertIsInstance(s, ConceptState)
        self.assertEqual(s.concept_id, "Cardiac Action Potential")

    def test_get_state_nonexistent_returns_none(self):
        self.assertIsNone(self.sg.get_state("NonexistentConcept"))

    def test_initial_mastery_zero(self):
        for s in self.sg.states.values():
            self.assertEqual(s.mastery, 0.0)


class TestStudentGraphUpdate(unittest.TestCase):

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

    def setUp(self):
        self.sg = StudentGraph(self.kg, self.analyzer)

    def test_update_mastery(self):
        self.sg.update_concept("Cardiac Action Potential", mastery=0.75)
        self.assertEqual(self.sg.get_state("Cardiac Action Potential").mastery, 0.75)

    def test_update_uncertainty(self):
        self.sg.update_concept("ECG", uncertainty=0.2)
        self.assertEqual(self.sg.get_state("ECG").uncertainty, 0.2)

    def test_update_confidence(self):
        self.sg.update_concept("STEMI", confidence=0.85)
        self.assertEqual(self.sg.get_state("STEMI").confidence, 0.85)

    def test_update_review_due(self):
        self.sg.update_concept("Arrhythmias", review_due=True)
        self.assertTrue(self.sg.get_state("Arrhythmias").review_due)

    def test_update_partial_unchanged(self):
        self.sg.update_concept("AV Node", mastery=0.5)
        state = self.sg.get_state("AV Node")
        self.assertEqual(state.mastery, 0.5)
        self.assertEqual(state.uncertainty, 1.0)

    def test_update_nonexistent_no_error(self):
        self.sg.update_concept("GhostConcept", mastery=0.9)
        self.assertIsNone(self.sg.get_state("GhostConcept"))

    def test_update_sets_last_seen(self):
        self.sg.update_concept("WPW Syndrome", mastery=0.3)
        self.assertIsNotNone(self.sg.get_state("WPW Syndrome").last_seen)

    def test_multiple_updates(self):
        self.sg.update_concept("Antiarrhythmics", mastery=0.4)
        self.sg.update_concept("Antiarrhythmics", mastery=0.6)
        self.sg.update_concept("Antiarrhythmics", mastery=0.8)
        self.assertEqual(self.sg.get_state("Antiarrhythmics").mastery, 0.8)


class TestStudentGraphSnapshot(unittest.TestCase):

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

    def setUp(self):
        self.sg = StudentGraph(self.kg, self.analyzer)
        self.sg.update_concept("Cardiac Action Potential", mastery=0.7, uncertainty=0.3)

    def test_snapshot_returns_all_keys(self):
        snap = self.sg.get_concept_snapshot("Cardiac Action Potential")
        expected_keys = {"concept", "mastery", "uncertainty", "confidence",
                         "degree", "pagerank", "betweenness",
                         "descendants", "depth", "review_due"}
        self.assertEqual(set(snap.keys()), expected_keys)

    def test_snapshot_includes_state(self):
        snap = self.sg.get_concept_snapshot("Cardiac Action Potential")
        self.assertEqual(snap["mastery"], 0.7)
        self.assertEqual(snap["uncertainty"], 0.3)

    def test_snapshot_includes_graph_metrics(self):
        snap = self.sg.get_concept_snapshot("Cardiac Action Potential")
        self.assertGreaterEqual(snap["degree"], 0)
        self.assertGreaterEqual(snap["pagerank"], 0)
        self.assertGreaterEqual(snap["betweenness"], 0)
        self.assertGreaterEqual(snap["descendants"], 0)
        self.assertGreaterEqual(snap["depth"], 0)

    def test_snapshot_nonexistent_returns_none(self):
        self.assertIsNone(self.sg.get_concept_snapshot("Ghost"))


class TestStudentGraphSummary(unittest.TestCase):

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

    def setUp(self):
        self.sg = StudentGraph(self.kg, self.analyzer)

    def test_summary_has_all_keys(self):
        summary = self.sg.student_summary()
        expected = {"total_concepts", "mastered", "weak",
                    "due_reviews", "average_mastery"}
        self.assertEqual(set(summary.keys()), expected)

    def test_summary_total_matches(self):
        summary = self.sg.student_summary()
        self.assertEqual(summary["total_concepts"], len(self.kg.graph.nodes))

    def test_summary_mastered_count(self):
        for node in self.kg.graph.nodes:
            self.sg.update_concept(node, mastery=0.5)
        self.sg.update_concept("Cardiac Action Potential", mastery=0.85)
        self.sg.update_concept("AV Node", mastery=0.90)
        summary = self.sg.student_summary()
        self.assertEqual(summary["mastered"], 2)

    def test_summary_weak_count(self):
        for node in self.kg.graph.nodes:
            self.sg.update_concept(node, mastery=0.5)
        self.sg.update_concept("RareConcept", mastery=0.1)
        self.sg.update_concept("Antiarrhythmics", mastery=0.2)
        summary = self.sg.student_summary()
        self.assertEqual(summary["weak"], 2)

    def test_summary_due_reviews(self):
        self.sg.update_concept("ECG", review_due=True)
        self.sg.update_concept("STEMI", review_due=True)
        summary = self.sg.student_summary()
        self.assertEqual(summary["due_reviews"], 2)

    def test_summary_average_mastery(self):
        self.sg.update_concept("RareConcept", mastery=0.5)
        self.sg.update_concept("Antiarrhythmics", mastery=0.5)
        self.sg.update_concept("Cardiac Action Potential", mastery=0.5)
        self.sg.update_concept("Coronary Circulation", mastery=0.5)
        self.sg.update_concept("AV Node", mastery=0.5)
        self.sg.update_concept("ECG", mastery=0.5)
        self.sg.update_concept("STEMI", mastery=0.5)
        self.sg.update_concept("WPW Syndrome", mastery=0.5)
        self.sg.update_concept("Arrhythmias", mastery=0.5)
        summary = self.sg.student_summary()
        self.assertAlmostEqual(summary["average_mastery"], 0.5, places=4)


class TestStudentGraphExport(unittest.TestCase):

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

    def setUp(self):
        self.sg = StudentGraph(self.kg, self.analyzer)
        self.sg.update_concept("Cardiac Action Potential", mastery=0.7)

    def test_csv_export_creates_file(self):
        path = tempfile.mktemp(suffix=".csv")
        self.sg.export_student_snapshot_csv(path)
        self.assertTrue(os.path.exists(path))
        os.unlink(path)

    def test_csv_has_all_rows(self):
        path = tempfile.mktemp(suffix=".csv")
        self.sg.export_student_snapshot_csv(path)
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        os.unlink(path)
        self.assertEqual(len(rows), len(self.kg.graph.nodes))

    def test_csv_has_all_columns(self):
        path = tempfile.mktemp(suffix=".csv")
        self.sg.export_student_snapshot_csv(path)
        with open(path, newline="", encoding="utf-8") as f:
            row = next(csv.DictReader(f))
        os.unlink(path)
        for field in ["concept", "mastery", "uncertainty", "confidence",
                       "degree", "pagerank", "betweenness",
                       "descendants", "depth", "review_due"]:
            self.assertIn(field, row)

    def test_csv_reflects_updates(self):
        path = tempfile.mktemp(suffix=".csv")
        self.sg.update_concept("RareConcept", mastery=0.99)
        self.sg.export_student_snapshot_csv(path)
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["concept"] == "RareConcept":
                    self.assertAlmostEqual(float(row["mastery"]), 0.99)
        os.unlink(path)

    def test_mastery_edge_cases(self):
        path = tempfile.mktemp(suffix=".csv")
        self.sg.update_concept("Cardiac Action Potential", mastery=1.0)
        self.sg.update_concept("RareConcept", mastery=0.0)
        self.sg.export_student_snapshot_csv(path)
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["concept"] == "Cardiac Action Potential":
                    self.assertAlmostEqual(float(row["mastery"]), 1.0)
                if row["concept"] == "RareConcept":
                    self.assertAlmostEqual(float(row["mastery"]), 0.0)
        os.unlink(path)


if __name__ == "__main__":
    unittest.main()
