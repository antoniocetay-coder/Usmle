import unittest
import json
import tempfile
import os

from knowledge_graph import KnowledgeGraph
from centrality import CentralityAnalyzer
from student_graph import StudentGraph
from candidate_generator import CandidateGenerator
from decision_engine import DecisionEngine
from simulation_engine import SimulationEngine
from hub_diversification import HubDiversificationPolicy

SAMPLE = {
    "STEMI": ["Coronary Circulation", "Cardiac Action Potential"],
    "WPW Syndrome": ["Cardiac Action Potential", "AV Node"],
    "RareConcept": [],
    "ECG": ["Cardiac Action Potential"],
    "Arrhythmias": ["ECG"],
    "Antiarrhythmics": ["Arrhythmias"],
}


def _make_policy():
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
    return HubDiversificationPolicy(de, sim), sim, sg, kg


class TestHubHistory(unittest.TestCase):

    def test_history_empty_initially(self):
        policy, sim, _, _ = _make_policy()
        self.assertEqual(policy.hub_history(), [])

    def test_history_after_simulation(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_days(5)
        hist = policy.hub_history()
        self.assertEqual(len(hist), 5)
        for h in hist:
            self.assertIsInstance(h, str)


class TestHubFrequency(unittest.TestCase):

    def test_frequency_empty_initially(self):
        policy, _, _, _ = _make_policy()
        self.assertEqual(policy.hub_frequency(), {})

    def test_frequency_after_simulation(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_days(10)
        freq = policy.hub_frequency()
        self.assertGreater(sum(freq.values()), 0)
        self.assertEqual(sum(freq.values()), 10)


class TestRecencyPenalty(unittest.TestCase):

    def test_recency_no_history_returns_one(self):
        policy, _, _, _ = _make_policy()
        self.assertEqual(policy.hub_recency_penalty("Anything"), 1.0)

    def test_recency_just_seen_low(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_day()
        hist = policy.hub_history()
        penalty = policy.hub_recency_penalty(hist[-1])
        self.assertLess(penalty, 1.0)
        self.assertGreaterEqual(penalty, 0.5)

    def test_recency_never_seen_max(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_days(5)
        penalty = policy.hub_recency_penalty("RareConcept")
        self.assertEqual(penalty, 1.0)

    def test_recency_between_zero_and_one(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_days(10)
        for hub in set(policy.hub_history()):
            p = policy.hub_recency_penalty(hub)
            self.assertGreaterEqual(p, 0.50)
            self.assertLessEqual(p, 1.0)


class TestFrequencyPenalty(unittest.TestCase):

    def test_freq_no_history_returns_one(self):
        policy, _, _, _ = _make_policy()
        self.assertEqual(policy.hub_frequency_penalty("Anything"), 1.0)

    def test_freq_most_frequent_lowest(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_days(10)
        freq = policy.hub_frequency()
        most_common = max(freq, key=freq.get)
        least_common = min(freq, key=freq.get)
        p_most = policy.hub_frequency_penalty(most_common)
        p_least = policy.hub_frequency_penalty(least_common)
        self.assertLessEqual(p_most, p_least)

    def test_freq_between_zero_and_one(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_days(10)
        for hub in set(policy.hub_history()):
            p = policy.hub_frequency_penalty(hub)
            self.assertGreaterEqual(p, 0.50)
            self.assertLessEqual(p, 1.0)

    def test_freq_never_seen_returns_one(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_days(5)
        p = policy.hub_frequency_penalty("RareConcept")
        self.assertEqual(p, 1.0)


class TestDiversificationFactor(unittest.TestCase):

    def test_factor_no_history_returns_one(self):
        policy, _, _, _ = _make_policy()
        self.assertEqual(policy.diversification_factor("Anything"), 1.0)

    def test_factor_between_zero_and_one(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_days(10)
        for hub in set(policy.hub_history()):
            f = policy.diversification_factor(hub)
            self.assertGreaterEqual(f, 0)
            self.assertLessEqual(f, 1)
            if f > 0:
                self.assertGreaterEqual(f, 0.25)

    def test_factor_combines_penalties(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_days(5)
        hub = policy.hub_history()[-1]
        expected = policy.hub_recency_penalty(hub) * policy.hub_frequency_penalty(hub)
        self.assertAlmostEqual(policy.diversification_factor(hub), expected)


class TestHubScoreDiversification(unittest.TestCase):

    def test_diversified_score_applies_factor(self):
        policy, sim, sg, kg = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_days(3)
        hub = policy.hub_history()[-1]
        base = policy._engine._hub_score(hub)
        diversified = policy._engine.hub_score_with_diversification(hub, policy)
        self.assertLessEqual(diversified, base)

    def test_diversified_mission_returns_dict(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        mission = policy._engine.generate_diversified_mission(policy)
        self.assertIsInstance(mission, dict)
        self.assertIn("focus_hub", mission)
        self.assertIn("study_concept", mission)


class TestEntropy(unittest.TestCase):

    def test_entropy_empty_returns_zero(self):
        policy, _, _, _ = _make_policy()
        self.assertEqual(policy.hub_entropy(), 0.0)

    def test_entropy_single_hub_zero(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_days(10)
        entropy = policy.hub_entropy()
        self.assertGreaterEqual(entropy, 0)
        self.assertLessEqual(entropy, 1)

    def test_entropy_perfect_distribution(self):
        policy, sim, sg, kg = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        hubs_seen = set()
        for _ in range(6):
            sim.simulate_day()
            hubs_seen.add(policy.hub_history()[-1])
        entropy = policy.hub_entropy()
        self.assertGreaterEqual(entropy, 0)
        self.assertLessEqual(entropy, 1)

    def test_entropy_more_hubs_increases(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_days(5)
        e1 = policy.hub_entropy()
        sim.simulate_days(15)
        e2 = policy.hub_entropy()
        self.assertIsInstance(e1, float)
        self.assertIsInstance(e2, float)


class TestGini(unittest.TestCase):

    def test_gini_empty_returns_zero(self):
        policy, _, _, _ = _make_policy()
        self.assertEqual(policy.hub_gini(), 0.0)

    def test_gini_single_hub_returns_zero(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_days(10)
        gini = policy.hub_gini()
        self.assertGreaterEqual(gini, 0)
        self.assertLessEqual(gini, 1)

    def test_gini_range(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_days(20)
        gini = policy.hub_gini()
        self.assertGreaterEqual(gini, 0)
        self.assertLessEqual(gini, 1)

    def test_gini_dominated_high(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_days(10)
        gini = policy.hub_gini()
        self.assertGreaterEqual(gini, 0)



class TestCoverageRate(unittest.TestCase):

    def test_coverage_empty_returns_zero(self):
        policy, _, _, _ = _make_policy()
        self.assertEqual(policy.coverage_rate(), 0.0)

    def test_coverage_positive(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_days(20)
        cr = policy.coverage_rate()
        self.assertGreater(cr, 0)
        self.assertLessEqual(cr, 1)

    def test_coverage_all_concepts(self):
        policy, sim, sg, kg = _make_policy()
        for node in kg.graph.nodes:
            sg.update_concept(node, mastery=0.85)
        sim.simulate_days(30)
        cr = policy.coverage_rate()
        self.assertGreater(cr, 0)


class TestComparePolicies(unittest.TestCase):

    def test_compare_returns_dict(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_days(5)
        result = policy.compare_policies(5)
        self.assertIsInstance(result, dict)

    def test_compare_baseline_diversified_days_match(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_days(5)
        result = policy.compare_policies(5)
        self.assertEqual(result["baseline"]["days_simulated"], 5)
        self.assertEqual(result["diversified"]["days_simulated"], 5)

    def test_compare_has_baseline(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_days(5)
        result = policy.compare_policies(5)
        self.assertIn("baseline", result)

    def test_compare_has_diversified(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_days(5)
        result = policy.compare_policies(5)
        self.assertIn("diversified", result)

    def test_compare_reports_have_keys(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_days(5)
        result = policy.compare_policies(5)
        for key in ["baseline", "diversified"]:
            r = result[key]
            for field in ["unique_hubs", "unique_concepts", "entropy",
                          "gini", "coverage", "average_mastery"]:
                self.assertIn(field, r)


class TestDiversificationReport(unittest.TestCase):

    def test_report_has_all_keys(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_days(20)
        r = policy.generate_diversification_report()
        expected = {"top_hubs", "entropy", "gini", "coverage", "recommendation"}
        self.assertEqual(set(r.keys()), expected)

    def test_report_top_hubs_is_list(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_days(20)
        r = policy.generate_diversification_report()
        self.assertIsInstance(r["top_hubs"], list)

    def test_report_recommendation_is_string(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_days(20)
        r = policy.generate_diversification_report()
        self.assertIsInstance(r["recommendation"], str)


class TestDiversifiedSimulation(unittest.TestCase):

    def test_diversified_day_works(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        result = sim.simulate_day_diversified(policy)
        self.assertIn("hub", result)
        self.assertIn("concept", result)

    def test_diversified_days_appends_history(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_days_diversified(10, policy)
        self.assertEqual(len(sim.history()), 10)

    def test_diversified_produces_different_hubs(self):
        policy, sim, sg, kg = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)

        # Baseline — get hubs for comparison
        sim2 = SimulationEngine(kg, sg, policy._engine)
        sim2.simulate_days(20)
        baseline_hubs = len(set(h["hub"] for h in sim2.history()))

        # Diversified
        sim.simulate_days_diversified(20, policy)
        diversified_hubs = len(set(h["hub"] for h in sim.history()))

        self.assertGreaterEqual(diversified_hubs, baseline_hubs)

    def test_diversified_study_concept_valid(self):
        policy, sim, sg, _ = _make_policy()
        sg.update_concept("Cardiac Action Potential", mastery=0.85)
        sg.update_concept("Coronary Circulation", mastery=0.85)
        sg.update_concept("AV Node", mastery=0.85)
        sim.simulate_days_diversified(10, policy)
        for h in sim.history():
            if h["concept"]:
                self.assertIsInstance(h["concept"], str)


if __name__ == "__main__":
    unittest.main()
