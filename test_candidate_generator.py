import unittest
import json
import tempfile
import os

from knowledge_graph import KnowledgeGraph
from centrality import CentralityAnalyzer
from student_graph import StudentGraph
from candidate_generator import CandidateGenerator

SAMPLE = {
    "STEMI": ["Coronary Circulation", "Cardiac Action Potential"],
    "WPW Syndrome": ["Cardiac Action Potential", "AV Node"],
    "RareConcept": [],
    "ECG": ["Cardiac Action Potential"],
    "Arrhythmias": ["ECG"],
    "Antiarrhythmics": ["Arrhythmias"],
}

# Roots (no prereqs): RareConcept, Coronary Circulation, Cardiac Action Potential, AV Node


class TestCandidateGeneratorPrereqs(unittest.TestCase):

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
        self.cg = CandidateGenerator(self.kg, self.sg, self.analyzer)

    def test_root_concept_satisfied(self):
        self.assertTrue(self.cg.prerequisites_satisfied("Coronary Circulation"))

    def test_root_concept_rare_satisfied(self):
        self.assertTrue(self.cg.prerequisites_satisfied("RareConcept"))

    def test_all_prereqs_mastered(self):
        self.sg.update_concept("Cardiac Action Potential", mastery=0.85)
        self.sg.update_concept("Coronary Circulation", mastery=0.90)
        self.assertTrue(self.cg.prerequisites_satisfied("STEMI"))

    def test_one_prereq_not_mastered(self):
        self.sg.update_concept("Cardiac Action Potential", mastery=0.85)
        self.sg.update_concept("Coronary Circulation", mastery=0.50)
        self.assertFalse(self.cg.prerequisites_satisfied("STEMI"))

    def test_multiple_prereqs_one_fails(self):
        self.sg.update_concept("Cardiac Action Potential", mastery=0.30)
        self.sg.update_concept("AV Node", mastery=0.90)
        self.assertFalse(self.cg.prerequisites_satisfied("WPW Syndrome"))

    def test_nonexistent_concept_false(self):
        self.assertFalse(self.cg.prerequisites_satisfied("GhostConcept"))

    def test_all_prereqs_at_boundary(self):
        self.sg.update_concept("Cardiac Action Potential", mastery=0.80)
        self.assertTrue(self.cg.prerequisites_satisfied("ECG"))


class TestCandidateGeneratorBlocked(unittest.TestCase):

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
        self.cg = CandidateGenerator(self.kg, self.sg, self.analyzer)

    def test_blocked_includes_nonroots(self):
        blocked = self.cg.blocked_concepts()
        for c in ["STEMI", "WPW Syndrome", "ECG", "Arrhythmias", "Antiarrhythmics"]:
            self.assertIn(c, blocked)

    def test_blocked_excludes_roots(self):
        blocked = self.cg.blocked_concepts()
        for c in ["RareConcept", "Coronary Circulation", "Cardiac Action Potential", "AV Node"]:
            self.assertNotIn(c, blocked)

    def test_blocked_after_mastering_prereqs(self):
        self.sg.update_concept("Cardiac Action Potential", mastery=0.85)
        blocked = self.cg.blocked_concepts()
        self.assertNotIn("ECG", blocked)
        self.assertIn("Arrhythmias", blocked)

    def test_blocked_empty_when_all_mastered(self):
        for node in self.kg.graph.nodes:
            self.sg.update_concept(node, mastery=0.85)
        blocked = self.cg.blocked_concepts()
        self.assertEqual(len(blocked), 0)


class TestCandidateGeneratorEligible(unittest.TestCase):

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
        self.cg = CandidateGenerator(self.kg, self.sg, self.analyzer)

    def test_roots_are_eligible_initially(self):
        eligible = self.cg.eligible_concepts()
        for c in ["RareConcept", "Coronary Circulation", "Cardiac Action Potential", "AV Node"]:
            self.assertIn(c, eligible)

    def test_new_concept_with_satisfied_prereqs_eligible(self):
        self.sg.update_concept("Cardiac Action Potential", mastery=0.85)
        self.sg.update_concept("Coronary Circulation", mastery=0.85)
        eligible = self.cg.eligible_concepts()
        self.assertIn("STEMI", eligible)

    def test_new_concept_without_satisfied_prereqs_excluded(self):
        self.sg.update_concept("Cardiac Action Potential", mastery=0.50)
        eligible = self.cg.eligible_concepts()
        self.assertNotIn("ECG", eligible)

    def test_review_due_always_eligible(self):
        self.sg.update_concept("Arrhythmias", review_due=True)
        eligible = self.cg.eligible_concepts()
        self.assertIn("Arrhythmias", eligible)

    def test_review_due_eligible_even_if_blocked(self):
        self.sg.update_concept("Antiarrhythmics", review_due=True)
        eligible = self.cg.eligible_concepts()
        self.assertIn("Antiarrhythmics", eligible)

    def test_all_eligible_when_all_mastered(self):
        for node in self.kg.graph.nodes:
            self.sg.update_concept(node, mastery=0.85)
        eligible = self.cg.eligible_concepts()
        self.assertEqual(len(eligible), len(self.kg.graph.nodes))

    def test_no_duplicates(self):
        self.sg.update_concept("Cardiac Action Potential", mastery=0.85)
        eligible = self.cg.eligible_concepts()
        self.assertEqual(len(eligible), len(set(eligible)))

    def test_eligible_is_list(self):
        eligible = self.cg.eligible_concepts()
        self.assertIsInstance(eligible, list)


class TestCandidateGeneratorSnapshot(unittest.TestCase):

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
        self.cg = CandidateGenerator(self.kg, self.sg, self.analyzer)
        self.sg.update_concept("Cardiac Action Potential", mastery=0.7)

    def test_snapshot_returns_all_keys(self):
        snap = self.cg.candidate_snapshot("Cardiac Action Potential")
        expected = {"concept", "mastery", "review_due", "pagerank",
                    "betweenness", "descendants", "depth",
                    "prerequisites_satisfied"}
        self.assertEqual(set(snap.keys()), expected)

    def test_snapshot_includes_prereq_status(self):
        snap = self.cg.candidate_snapshot("ECG")
        self.assertIn("prerequisites_satisfied", snap)

    def test_snapshot_root_prereq_true(self):
        snap = self.cg.candidate_snapshot("Cardiac Action Potential")
        self.assertTrue(snap["prerequisites_satisfied"])

    def test_snapshot_blocked_prereq_false(self):
        snap = self.cg.candidate_snapshot("Arrhythmias")
        self.assertFalse(snap["prerequisites_satisfied"])

    def test_snapshot_includes_mastery(self):
        snap = self.cg.candidate_snapshot("Cardiac Action Potential")
        self.assertEqual(snap["mastery"], 0.7)

    def test_snapshot_nonexistent_returns_none(self):
        self.assertIsNone(self.cg.candidate_snapshot("GhostConcept"))

    def test_snapshot_includes_centrality(self):
        snap = self.cg.candidate_snapshot("Cardiac Action Potential")
        self.assertGreaterEqual(snap["pagerank"], 0)
        self.assertGreaterEqual(snap["betweenness"], 0)

    def test_snapshot_includes_graph_metrics(self):
        snap = self.cg.candidate_snapshot("Cardiac Action Potential")
        self.assertGreaterEqual(snap["descendants"], 0)
        self.assertGreaterEqual(snap["depth"], 0)


class TestCandidateGeneratorSummary(unittest.TestCase):

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
        self.cg = CandidateGenerator(self.kg, self.sg, self.analyzer)

    def test_summary_has_all_keys(self):
        s = self.cg.candidate_summary()
        expected = {"eligible", "blocked", "due_reviews", "new_available"}
        self.assertEqual(set(s.keys()), expected)

    def test_summary_eligible_initially(self):
        s = self.cg.candidate_summary()
        self.assertEqual(s["eligible"], 4)

    def test_summary_blocked_initially(self):
        s = self.cg.candidate_summary()
        self.assertEqual(s["blocked"], 5)

    def test_summary_due_reviews(self):
        self.sg.update_concept("ECG", review_due=True)
        self.sg.update_concept("STEMI", review_due=True)
        s = self.cg.candidate_summary()
        self.assertEqual(s["due_reviews"], 2)

    def test_summary_new_available(self):
        self.sg.update_concept("Cardiac Action Potential", mastery=0.85)
        self.sg.update_concept("Coronary Circulation", mastery=0.85)
        s = self.cg.candidate_summary()
        self.assertEqual(s["new_available"], 6)

    def test_summary_all_mastered(self):
        for node in self.kg.graph.nodes:
            self.sg.update_concept(node, mastery=0.85)
        s = self.cg.candidate_summary()
        self.assertEqual(s["eligible"], 9)
        self.assertEqual(s["blocked"], 0)

    def test_summary_no_overlap_due_and_new(self):
        self.sg.update_concept("Cardiac Action Potential", mastery=0.85)
        self.sg.update_concept("Coronary Circulation", mastery=0.85)
        self.sg.update_concept("STEMI", review_due=True)
        s = self.cg.candidate_summary()
        self.assertEqual(s["due_reviews"] + s["new_available"], s["eligible"])


if __name__ == "__main__":
    unittest.main()
