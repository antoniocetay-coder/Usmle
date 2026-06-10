import unittest
import json
import tempfile
import os
import csv

from knowledge_graph import KnowledgeGraph
from centrality import CentralityAnalyzer
from student_graph import StudentGraph
from candidate_generator import CandidateGenerator
from decision_engine import DecisionEngine
from simulation_engine import SimulationEngine, MissionRecord

SAMPLE = {
    "STEMI": ["Coronary Circulation", "Cardiac Action Potential"],
    "WPW Syndrome": ["Cardiac Action Potential", "AV Node"],
    "RareConcept": [],
    "ECG": ["Cardiac Action Potential"],
    "Arrhythmias": ["ECG"],
    "Antiarrhythmics": ["Arrhythmias"],
}


def _make_engine():
    tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json")
    json.dump(SAMPLE, tmp)
    tmp.close()
    kg = KnowledgeGraph(tmp.name)
    analyzer = CentralityAnalyzer(kg)
    sg = StudentGraph(kg, analyzer)
    cg = CandidateGenerator(kg, sg, analyzer)
    de = DecisionEngine(kg, sg, analyzer, cg)
    sim = SimulationEngine(kg, sg, de)
    os.unlink(tmp.name)
    return sim, sg, tmp.name


class TestMissionRecord(unittest.TestCase):

    def test_mission_record_fields(self):
        r = MissionRecord(day=1, hub="Inflammation", concept="IL-1",
                          mastery_before=0.3, mastery_after=0.4, review_due=False)
        self.assertEqual(r.day, 1)
        self.assertEqual(r.hub, "Inflammation")
        self.assertEqual(r.concept, "IL-1")
        self.assertEqual(r.mastery_before, 0.3)
        self.assertEqual(r.mastery_after, 0.4)


class TestSimulationInit(unittest.TestCase):

    def test_history_starts_empty(self):
        sim, _, _ = _make_engine()
        self.assertEqual(len(sim.history()), 0)


class TestSimulateLearning(unittest.TestCase):

    def test_learning_increases_mastery(self):
        sim, sg, _ = _make_engine()
        sg.update_concept("Cardiac Action Potential", mastery=0.5)
        sim.simulate_learning("Cardiac Action Potential")
        self.assertGreater(sg.get_state("Cardiac Action Potential").mastery, 0.5)

    def test_learning_decreases_uncertainty(self):
        sim, sg, _ = _make_engine()
        sg.update_concept("ECG", uncertainty=0.8)
        sim.simulate_learning("ECG")
        self.assertLess(sg.get_state("ECG").uncertainty, 0.8)

    def test_learning_clamps_mastery_at_one(self):
        sim, sg, _ = _make_engine()
        sg.update_concept("RareConcept", mastery=0.95)
        sim.simulate_learning("RareConcept")
        self.assertEqual(sg.get_state("RareConcept").mastery, 1.0)

    def test_learning_clamps_uncertainty_at_zero(self):
        sim, sg, _ = _make_engine()
        sg.update_concept("RareConcept", uncertainty=0.03)
        sim.simulate_learning("RareConcept")
        self.assertEqual(sg.get_state("RareConcept").uncertainty, 0.0)

    def test_learning_sets_review_due_false(self):
        sim, sg, _ = _make_engine()
        sg.update_concept("AV Node", review_due=True)
        sim.simulate_learning("AV Node")
        self.assertFalse(sg.get_state("AV Node").review_due)

    def test_learning_nonexistent_no_error(self):
        sim, _, _ = _make_engine()
        sim.simulate_learning("GhostConcept")


class TestSimulateDay(unittest.TestCase):

    def setUp(self):
        self.sim, self.sg, _ = _make_engine()
        # Unlock the hub cluster by mastering root prereqs
        self.sg.update_concept("Cardiac Action Potential", mastery=0.85)
        self.sg.update_concept("Coronary Circulation", mastery=0.85)
        self.sg.update_concept("AV Node", mastery=0.85)

    def test_simulate_day_returns_dict(self):
        result = self.sim.simulate_day()
        self.assertIsInstance(result, dict)

    def test_simulate_day_has_hub(self):
        result = self.sim.simulate_day()
        self.assertIn("hub", result)

    def test_simulate_day_has_concept(self):
        result = self.sim.simulate_day()
        self.assertIn("concept", result)

    def test_simulate_day_has_mastery_before(self):
        result = self.sim.simulate_day()
        self.assertIn("mastery_before", result)

    def test_simulate_day_has_mastery_after(self):
        result = self.sim.simulate_day()
        self.assertIn("mastery_after", result)

    def test_simulate_day_increases_mastery(self):
        result = self.sim.simulate_day()
        if result["concept"]:
            self.assertGreater(result["mastery_after"], result["mastery_before"])

    def test_simulate_day_appends_history(self):
        before = len(self.sim.history())
        self.sim.simulate_day()
        self.assertEqual(len(self.sim.history()), before + 1)

    def test_simulate_day_no_concept_returns_zero(self):
        sim, _, _ = _make_engine()
        result = sim.simulate_day()
        self.assertEqual(result["mastery_before"], 0.0)
        self.assertEqual(result["mastery_after"], 0.2)


class TestSimulateDays(unittest.TestCase):

    def setUp(self):
        self.sim, self.sg, _ = _make_engine()
        self.sg.update_concept("Cardiac Action Potential", mastery=0.85)
        self.sg.update_concept("Coronary Circulation", mastery=0.85)
        self.sg.update_concept("AV Node", mastery=0.85)

    def test_simulate_days_returns_list(self):
        results = self.sim.simulate_days(5)
        self.assertIsInstance(results, list)

    def test_simulate_days_count(self):
        results = self.sim.simulate_days(10)
        self.assertEqual(len(results), 10)

    def test_simulate_days_zero(self):
        results = self.sim.simulate_days(0)
        self.assertEqual(len(results), 0)

    def test_simulate_days_history_length(self):
        self.sim.simulate_days(7)
        self.assertEqual(len(self.sim.history()), 7)

    def test_simulate_days_mastery_grows(self):
        self.sim.simulate_days(20)
        prog = self.sim.learning_progress()
        self.assertGreater(prog["average_mastery"], 0)


class TestCoverageMetrics(unittest.TestCase):

    def setUp(self):
        self.sim, self.sg, _ = _make_engine()
        self.sg.update_concept("Cardiac Action Potential", mastery=0.85)
        self.sg.update_concept("Coronary Circulation", mastery=0.85)
        self.sg.update_concept("AV Node", mastery=0.85)
        self.sim.simulate_days(15)

    def test_coverage_has_all_keys(self):
        cov = self.sim.coverage_metrics()
        expected = {"unique_hubs", "unique_concepts",
                    "hub_distribution", "concept_distribution"}
        self.assertEqual(set(cov.keys()), expected)

    def test_coverage_unique_hubs_positive(self):
        cov = self.sim.coverage_metrics()
        self.assertGreater(cov["unique_hubs"], 0)

    def test_coverage_unique_concepts_positive(self):
        cov = self.sim.coverage_metrics()
        self.assertGreater(cov["unique_concepts"], 0)

    def test_coverage_hub_distribution_is_dict(self):
        cov = self.sim.coverage_metrics()
        self.assertIsInstance(cov["hub_distribution"], dict)

    def test_coverage_concept_distribution_is_dict(self):
        cov = self.sim.coverage_metrics()
        self.assertIsInstance(cov["concept_distribution"], dict)


class TestFrequencies(unittest.TestCase):

    def setUp(self):
        self.sim, self.sg, _ = _make_engine()
        self.sg.update_concept("Cardiac Action Potential", mastery=0.85)
        self.sg.update_concept("Coronary Circulation", mastery=0.85)
        self.sg.update_concept("AV Node", mastery=0.85)
        self.sim.simulate_days(20)

    def test_hub_frequency_returns_dict(self):
        freq = self.sim.hub_frequency()
        self.assertIsInstance(freq, dict)

    def test_hub_frequency_positive(self):
        freq = self.sim.hub_frequency()
        self.assertGreater(sum(freq.values()), 0)

    def test_concept_frequency_returns_dict(self):
        freq = self.sim.concept_frequency()
        self.assertIsInstance(freq, dict)

    def test_concept_frequency_positive(self):
        freq = self.sim.concept_frequency()
        self.assertGreater(sum(freq.values()), 0)

    def test_hub_frequency_matches_days(self):
        freq = self.sim.hub_frequency()
        self.assertEqual(sum(freq.values()), 20)


class TestLearningProgress(unittest.TestCase):

    def setUp(self):
        self.sim, self.sg, _ = _make_engine()

    def test_progress_has_all_keys(self):
        prog = self.sim.learning_progress()
        expected = {"average_mastery", "mastered_concepts", "weak_concepts"}
        self.assertEqual(set(prog.keys()), expected)

    def test_progress_initial(self):
        prog = self.sim.learning_progress()
        self.assertEqual(prog["average_mastery"], 0.0)

    def test_progress_after_learning(self):
        self.sg.update_concept("Cardiac Action Potential", mastery=0.85)
        self.sg.update_concept("Coronary Circulation", mastery=0.85)
        self.sg.update_concept("AV Node", mastery=0.85)
        self.sim.simulate_days(30)
        prog = self.sim.learning_progress()
        self.assertGreater(prog["average_mastery"], 0.01)
        self.assertIsInstance(prog["mastered_concepts"], int)


class TestValidationReport(unittest.TestCase):

    def setUp(self):
        self.sim, self.sg, _ = _make_engine()
        self.sg.update_concept("Cardiac Action Potential", mastery=0.85)
        self.sg.update_concept("Coronary Circulation", mastery=0.85)
        self.sg.update_concept("AV Node", mastery=0.85)
        self.sim.simulate_days(30)

    def test_report_has_all_keys(self):
        r = self.sim.generate_validation_report()
        expected = {"days_simulated", "unique_hubs", "unique_concepts",
                    "top_hubs", "top_concepts", "average_mastery",
                    "mastered_concepts", "weak_concepts"}
        self.assertEqual(set(r.keys()), expected)

    def test_report_days_correct(self):
        r = self.sim.generate_validation_report()
        self.assertEqual(r["days_simulated"], 30)

    def test_report_top_hubs_is_list(self):
        r = self.sim.generate_validation_report()
        self.assertIsInstance(r["top_hubs"], list)

    def test_report_top_concepts_is_list(self):
        r = self.sim.generate_validation_report()
        self.assertIsInstance(r["top_concepts"], list)

    def test_report_top_hubs_has_items(self):
        r = self.sim.generate_validation_report()
        self.assertGreater(len(r["top_hubs"]), 0)

    def test_report_average_mastery_positive(self):
        r = self.sim.generate_validation_report()
        self.assertGreater(r["average_mastery"], 0)


class TestExportCSV(unittest.TestCase):

    def setUp(self):
        self.sim, self.sg, _ = _make_engine()
        self.sg.update_concept("Cardiac Action Potential", mastery=0.85)
        self.sg.update_concept("Coronary Circulation", mastery=0.85)
        self.sg.update_concept("AV Node", mastery=0.85)
        self.sim.simulate_days(10)

    def test_csv_creates_file(self):
        path = tempfile.mktemp(suffix=".csv")
        self.sim.export_simulation_csv(path)
        self.assertTrue(os.path.exists(path))
        os.unlink(path)

    def test_csv_has_correct_rows(self):
        path = tempfile.mktemp(suffix=".csv")
        self.sim.export_simulation_csv(path)
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        os.unlink(path)
        self.assertEqual(len(rows), 10)

    def test_csv_has_all_columns(self):
        path = tempfile.mktemp(suffix=".csv")
        self.sim.export_simulation_csv(path)
        with open(path, newline="", encoding="utf-8") as f:
            row = next(csv.DictReader(f))
        os.unlink(path)
        for field in ["day", "hub", "concept", "mastery_before", "mastery_after"]:
            self.assertIn(field, row)

    def test_csv_content_matches_history(self):
        path = tempfile.mktemp(suffix=".csv")
        hist = self.sim.history()
        self.sim.export_simulation_csv(path)
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        os.unlink(path)
        for i, row in enumerate(rows):
            self.assertEqual(int(row["day"]), hist[i]["day"])


if __name__ == "__main__":
    unittest.main()
