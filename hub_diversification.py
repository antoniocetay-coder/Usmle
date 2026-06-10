from __future__ import annotations

import math
import copy

from knowledge_graph import KnowledgeGraph
from centrality import CentralityAnalyzer
from student_graph import StudentGraph
from candidate_generator import CandidateGenerator
from decision_engine import DecisionEngine
from simulation_engine import SimulationEngine


class HubDiversificationPolicy:

    def __init__(self, decision_engine: DecisionEngine,
                 simulation_engine: SimulationEngine):
        self._engine = decision_engine
        self._sim = simulation_engine

    # ── Parte A — Hub History ──────────────────────────────────────────
    def hub_history(self) -> list[str]:
        return [r["hub"] for r in self._sim.history()]

    # ── Parte B — Hub Frequency ────────────────────────────────────────
    def hub_frequency(self) -> dict:
        return self._sim.hub_frequency()

    # ── Parte C — Recency Penalty ──────────────────────────────────────
    def hub_recency_penalty(self, hub_id: str) -> float:
        history = self.hub_history()
        if not history:
            return 1.0
        last_idx = None
        for i in range(len(history) - 1, -1, -1):
            if history[i] == hub_id:
                last_idx = i
                break
        if last_idx is None:
            return 1.0
        days_ago = len(history) - last_idx
        if days_ago <= 1:
            return 0.50
        elif days_ago <= 3:
            return 0.65
        elif days_ago <= 6:
            return 0.80
        elif days_ago <= 12:
            return 0.90
        else:
            return 1.0

    # ── Parte D — Frequency Penalty ────────────────────────────────────
    def hub_frequency_penalty(self, hub_id: str) -> float:
        freq = self.hub_frequency()
        if not freq:
            return 1.0
        max_freq = max(freq.values())
        if max_freq == 0:
            return 1.0
        this_freq = freq.get(hub_id, 0)
        ratio = this_freq / max_freq
        penalty = 0.50 + 0.50 * (1.0 - ratio)
        return round(max(0.25, min(1.0, penalty)), 6)

    # ── Parte E — Diversification Factor ───────────────────────────────
    def diversification_factor(self, hub_id: str) -> float:
        return round(
            self.hub_recency_penalty(hub_id)
            * self.hub_frequency_penalty(hub_id),
            6,
        )

    # ── Parte G — Hub Entropy ──────────────────────────────────────────
    def hub_entropy(self) -> float:
        freq = self.hub_frequency()
        if not freq:
            return 0.0
        total = sum(freq.values())
        entropy = 0.0
        for count in freq.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)
        n = len(freq)
        if n <= 1:
            return 0.0
        max_entropy = math.log2(n)
        return round(entropy / max_entropy if max_entropy > 0 else 0.0, 6)

    # ── Parte H — Gini Index ───────────────────────────────────────────
    def hub_gini(self) -> float:
        freq = self.hub_frequency()
        if not freq:
            return 0.0
        values = sorted(freq.values())
        n = len(values)
        if n == 0:
            return 0.0
        cumulative = 0
        numerator = 0
        for i, v in enumerate(values):
            cumulative += v
            numerator += (i + 1) * v
        if cumulative == 0:
            return 0.0
        gini = (2 * numerator) / (n * cumulative) - (n + 1) / n
        return round(gini, 6)

    # ── Parte I — Coverage Rate ────────────────────────────────────────
    def coverage_rate(self) -> float:
        total = self._sim._kg.graph.number_of_nodes()
        if total == 0:
            return 0.0
        concepts = set()
        for r in self._sim.history():
            if r["concept"]:
                concepts.add(r["concept"])
        return round(len(concepts) / total, 6)

    # ── Parte J — A/B Comparison ───────────────────────────────────────
    def compare_policies(self, days: int = 60) -> dict:
        kg = self._sim._kg
        nodes = list(kg.graph.nodes)

        def setup_student_state(sg):
            for node in nodes:
                state = sg.get_state(node)
                orig = self._sim._sg.get_state(node)
                if state is None or orig is None:
                    continue
                state.mastery = orig.mastery
                state.uncertainty = orig.uncertainty
                state.review_due = orig.review_due
                state.confidence = orig.confidence

        # Baseline
        ana_base = CentralityAnalyzer(kg)
        sg_base = StudentGraph(kg, ana_base)
        setup_student_state(sg_base)
        cg_base = CandidateGenerator(kg, sg_base, ana_base)
        de_base = DecisionEngine(kg, sg_base, ana_base, cg_base)
        sim_base = SimulationEngine(kg, sg_base, de_base)

        # Diversified
        ana_div = CentralityAnalyzer(kg)
        sg_div = StudentGraph(kg, ana_div)
        setup_student_state(sg_div)
        cg_div = CandidateGenerator(kg, sg_div, ana_div)
        de_div = DecisionEngine(kg, sg_div, ana_div, cg_div)
        sim_div = SimulationEngine(kg, sg_div, de_div)
        policy_div = HubDiversificationPolicy(de_div, sim_div)

        sim_base.simulate_days(days)
        sim_div.simulate_days_diversified(days, policy_div)

        return {
            "baseline": self._metrics_dict(sim_base, None),
            "diversified": self._metrics_dict(sim_div, policy_div),
        }

    def _metrics_dict(self, sim, policy):
        report = sim.generate_validation_report()
        entropy = policy.hub_entropy() if policy else self._calc_entropy(sim)
        gini = policy.hub_gini() if policy else self._calc_gini(sim)
        cov = sim.coverage_metrics()
        total = sim._kg.graph.number_of_nodes()
        coverage = round(cov["unique_concepts"] / total, 4) if total > 0 else 0.0
        return {
            "days_simulated": report["days_simulated"],
            "unique_hubs": report["unique_hubs"],
            "unique_concepts": report["unique_concepts"],
            "top_hubs": report["top_hubs"],
            "entropy": entropy,
            "gini": gini,
            "coverage": coverage,
            "average_mastery": report["average_mastery"],
            "mastered_concepts": report["mastered_concepts"],
            "weak_concepts": report["weak_concepts"],
        }

    @staticmethod
    def _calc_entropy(sim):
        freq = sim.hub_frequency()
        if not freq:
            return 0.0
        total = sum(freq.values())
        entropy = 0.0
        for count in freq.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)
        n = len(freq)
        if n <= 1:
            return 0.0
        max_entropy = math.log2(n)
        return round(entropy / max_entropy if max_entropy > 0 else 0.0, 6)

    @staticmethod
    def _calc_gini(sim):
        freq = sim.hub_frequency()
        if not freq:
            return 0.0
        values = sorted(freq.values())
        n = len(values)
        if n == 0:
            return 0.0
        cumulative = 0
        numerator = 0
        for i, v in enumerate(values):
            cumulative += v
            numerator += (i + 1) * v
        if cumulative == 0:
            return 0.0
        gini = (2 * numerator) / (n * cumulative) - (n + 1) / n
        return round(gini, 6)

    # ── Parte K — Report ───────────────────────────────────────────────
    def generate_diversification_report(self) -> dict:
        freq = self.hub_frequency()
        hub_entropy = self.hub_entropy()
        hub_gini = self.hub_gini()
        coverage = self.coverage_rate()

        top_hubs = sorted(freq.items(), key=lambda x: -x[1])[:5]

        if hub_gini < 0.3:
            recommendation = "distribuicao saudavel"
        elif hub_gini < 0.5:
            recommendation = "concentracao moderada"
        else:
            recommendation = "alta concentracao — aplicar diversification"

        return {
            "top_hubs": top_hubs,
            "entropy": hub_entropy,
            "gini": hub_gini,
            "coverage": coverage,
            "recommendation": recommendation,
        }
