import unittest
import json
import tempfile
import os

from knowledge_graph import KnowledgeGraph
from centrality import CentralityAnalyzer
from student_graph import StudentGraph
from candidate_generator import CandidateGenerator
from decision_engine import DecisionEngine

SAMPLE = {
    "STEMI": ["Coronary Circulation", "Cardiac Action Potential"],
    "WPW Syndrome": ["Cardiac Action Potential", "AV Node"],
    "RareConcept": [],
    "ECG": ["Cardiac Action Potential"],
    "Arrhythmias": ["ECG"],
    "Antiarrhythmics": ["Arrhythmias"],
}


class TestDecisionEngineHubSelection(unittest.TestCase):

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
        self.engine = DecisionEngine(self.kg, self.sg, self.analyzer, self.cg)

    def test_select_focus_hub_returns_dict(self):
        result = self.engine.select_focus_hub()
        self.assertIsInstance(result, dict)

    def test_select_focus_hub_has_hub_key(self):
        result = self.engine.select_focus_hub()
        self.assertIn("hub", result)

    def test_select_focus_hub_has_score_key(self):
        result = self.engine.select_focus_hub()
        self.assertIn("score", result)

    def test_hub_is_in_graph(self):
        result = self.engine.select_focus_hub()
        self.assertTrue(self.kg.has_concept(result["hub"]))

    def test_hub_score_between_zero_and_one(self):
        result = self.engine.select_focus_hub()
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 1)

    def test_cardiac_is_top_hub(self):
        result = self.engine.select_focus_hub()
        self.assertEqual(result["hub"], "Cardiac Action Potential")

    def test_hub_score_reflects_region_weakness(self):
        self.sg.update_concept("Cardiac Action Potential", mastery=0.9)
        self.sg.update_concept("Coronary Circulation", mastery=0.9)
        self.sg.update_concept("AV Node", mastery=0.9)
        result = self.engine.select_focus_hub()
        hub_before = self.engine._hub_score("Cardiac Action Potential")
        self.assertGreater(hub_before, 0)


class TestDecisionEngineHubCluster(unittest.TestCase):

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
        self.engine = DecisionEngine(self.kg, self.sg, self.analyzer, self.cg)

    def test_hub_cluster_returns_list(self):
        cluster = self.engine.hub_cluster("Cardiac Action Potential")
        self.assertIsInstance(cluster, list)

    def test_hub_cluster_includes_children(self):
        cluster = self.engine.hub_cluster("Cardiac Action Potential")
        for c in ["STEMI", "WPW Syndrome", "ECG"]:
            self.assertIn(c, cluster)

    def test_hub_cluster_includes_descendants(self):
        cluster = self.engine.hub_cluster("Cardiac Action Potential")
        for c in ["Arrhythmias", "Antiarrhythmics"]:
            self.assertIn(c, cluster)

    def test_hub_cluster_leaf_returns_empty(self):
        cluster = self.engine.hub_cluster("Antiarrhythmics")
        self.assertEqual(len(cluster), 0)

    def test_hub_cluster_isolated_returns_empty(self):
        cluster = self.engine.hub_cluster("RareConcept")
        self.assertEqual(len(cluster), 0)

    def test_hub_cluster_nonexistent_returns_empty(self):
        cluster = self.engine.hub_cluster("GhostConcept")
        self.assertEqual(len(cluster), 0)

    def test_hub_cluster_no_duplicates(self):
        cluster = self.engine.hub_cluster("Cardiac Action Potential")
        self.assertEqual(len(cluster), len(set(cluster)))

    def test_hub_cluster_all_valid(self):
        cluster = self.engine.hub_cluster("Cardiac Action Potential")
        for c in cluster:
            self.assertTrue(self.kg.has_concept(c))


class TestDecisionEngineStudyConcept(unittest.TestCase):

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
        self.engine = DecisionEngine(self.kg, self.sg, self.analyzer, self.cg)
        self.sg.update_concept("Cardiac Action Potential", mastery=0.85)

    def test_select_study_concept_returns_dict(self):
        result = self.engine.select_study_concept("Cardiac Action Potential")
        self.assertIsInstance(result, dict)

    def test_select_study_concept_has_hub(self):
        result = self.engine.select_study_concept("Cardiac Action Potential")
        self.assertEqual(result["hub"], "Cardiac Action Potential")

    def test_select_study_concept_is_eligible(self):
        result = self.engine.select_study_concept("Cardiac Action Potential")
        eligible = self.cg.eligible_concepts()
        self.assertIn(result["concept"], eligible)

    def test_select_study_concept_in_cluster(self):
        result = self.engine.select_study_concept("Cardiac Action Potential")
        cluster = self.engine.hub_cluster("Cardiac Action Potential")
        self.assertIn(result["concept"], cluster)

    def test_select_study_concept_low_mastery_preferred(self):
        self.sg.update_concept("ECG", mastery=0.1)
        self.sg.update_concept("STEMI", mastery=0.8)
        result = self.engine.select_study_concept("Cardiac Action Potential")
        self.assertEqual(result["concept"], "ECG")

    def test_select_study_concept_review_due_preferred(self):
        self.sg.update_concept("ECG", mastery=0.1)
        self.sg.update_concept("Arrhythmias", mastery=0.1, review_due=True)
        result = self.engine.select_study_concept("Cardiac Action Potential")
        self.assertEqual(result["concept"], "Arrhythmias")

    def test_select_study_concept_hub_itself_when_cluster_empty(self):
        result = self.engine.select_study_concept("RareConcept")
        self.assertEqual(result, {"hub": "RareConcept", "concept": "RareConcept"})

    def test_study_concept_score_higher_for_review_due(self):
        self.sg.update_concept("ECG", mastery=0.3)
        self.sg.update_concept("Arrhythmias", mastery=0.3, review_due=True)
        score_ecg = self.engine._study_concept_score("ECG")
        score_arr = self.engine._study_concept_score("Arrhythmias")
        self.assertGreater(score_arr, score_ecg)


class TestDecisionEngineMission(unittest.TestCase):

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
        self.engine = DecisionEngine(self.kg, self.sg, self.analyzer, self.cg)
        self.sg.update_concept("Cardiac Action Potential", mastery=0.85)

    def test_generate_study_mission_returns_dict(self):
        mission = self.engine.generate_study_mission()
        self.assertIsInstance(mission, dict)

    def test_mission_has_focus_hub(self):
        mission = self.engine.generate_study_mission()
        self.assertIn("focus_hub", mission)

    def test_mission_has_study_concept(self):
        mission = self.engine.generate_study_mission()
        self.assertIn("study_concept", mission)

    def test_mission_has_reason(self):
        mission = self.engine.generate_study_mission()
        self.assertIn("reason", mission)

    def test_mission_study_concept_is_valid(self):
        mission = self.engine.generate_study_mission()
        if mission["study_concept"]:
            self.assertTrue(self.kg.has_concept(mission["study_concept"]))

    def test_mission_reason_has_hub_importance(self):
        mission = self.engine.generate_study_mission()
        self.assertIn("hub_importance", mission["reason"])

    def test_mission_reason_has_mastery(self):
        mission = self.engine.generate_study_mission()
        self.assertIn("mastery", mission["reason"])

    def test_mission_reason_has_uncertainty(self):
        mission = self.engine.generate_study_mission()
        self.assertIn("uncertainty", mission["reason"])

    def test_mission_reason_values_are_floats(self):
        mission = self.engine.generate_study_mission()
        self.assertIsInstance(mission["reason"]["hub_importance"], float)
        self.assertIsInstance(mission["reason"]["mastery"], float)
        self.assertIsInstance(mission["reason"]["uncertainty"], float)

    def test_mission_study_concept_is_string(self):
        mission = self.engine.generate_study_mission()
        self.assertIsInstance(mission["study_concept"], str)


class TestDecisionEngineExplain(unittest.TestCase):

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
        self.engine = DecisionEngine(self.kg, self.sg, self.analyzer, self.cg)

    def test_explain_mission_returns_dict(self):
        expl = self.engine.explain_mission()
        self.assertIsInstance(expl, dict)

    def test_explain_has_focus_hub(self):
        expl = self.engine.explain_mission()
        self.assertIn("focus_hub", expl)

    def test_explain_has_why_hub(self):
        expl = self.engine.explain_mission()
        self.assertIn("why_hub", expl)

    def test_explain_why_hub_is_list(self):
        expl = self.engine.explain_mission()
        self.assertIsInstance(expl["why_hub"], list)

    def test_explain_why_hub_has_reasons(self):
        expl = self.engine.explain_mission()
        self.assertGreater(len(expl["why_hub"]), 0)

    def test_explain_has_study_concept(self):
        expl = self.engine.explain_mission()
        self.assertIn("study_concept", expl)

    def test_explain_has_why_concept(self):
        expl = self.engine.explain_mission()
        self.assertIn("why_concept", expl)

    def test_explain_why_concept_is_list(self):
        expl = self.engine.explain_mission()
        self.assertIsInstance(expl["why_concept"], list)

    def test_explain_why_concept_has_reasons(self):
        expl = self.engine.explain_mission()
        self.assertGreater(len(expl["why_concept"]), 0)

    def test_explain_concept_includes_low_mastery_when_applicable(self):
        self.sg.update_concept("Cardiac Action Potential", mastery=0.85)
        self.sg.update_concept("ECG", mastery=0.15)
        expl = self.engine.explain_mission()
        self.assertIn("low mastery", expl["why_concept"])

    def test_explain_concept_includes_review_due_when_applicable(self):
        self.sg.update_concept("Cardiac Action Potential", mastery=0.85)
        self.sg.update_concept("ECG", mastery=0.5, review_due=True)
        expl = self.engine.explain_mission()
        self.assertIn("review due", expl["why_concept"])

    def test_explain_hub_includes_descendants_count(self):
        expl = self.engine.explain_mission()
        has_desc = any("descendants" in r for r in expl["why_hub"])
        self.assertTrue(has_desc)


if __name__ == "__main__":
    unittest.main()
