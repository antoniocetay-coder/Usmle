from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from knowledge_graph import KnowledgeGraph
from student_graph import StudentGraph
from decision_engine import DecisionEngine


@dataclass
class MissionRecord:
    day: int
    hub: str
    concept: Optional[str]
    mastery_before: float
    mastery_after: float
    review_due: bool


class SimulationEngine:

    def __init__(self, knowledge_graph: KnowledgeGraph,
                 student_graph: StudentGraph,
                 decision_engine: DecisionEngine):
        self._kg = knowledge_graph
        self._sg = student_graph
        self._engine = decision_engine
        self._history: list[MissionRecord] = []
        self._day = 0

    # ── Histórico ─────────────────────────────────────────────────────
    def history(self) -> list[dict]:
        return [
            {
                "day": r.day,
                "hub": r.hub,
                "concept": r.concept,
                "mastery_before": r.mastery_before,
                "mastery_after": r.mastery_after,
                "review_due": r.review_due,
            }
            for r in self._history
        ]

    # ── Aprendizado sintético ─────────────────────────────────────────
    def simulate_learning(self, concept_id: str):
        state = self._sg.get_state(concept_id)
        if state is None:
            return
        state.mastery = min(1.0, state.mastery + 0.20)
        state.uncertainty = max(0.0, state.uncertainty - 0.05)
        state.review_due = False

    # ── Decaimento (esquecimento) ─────────────────────────────────────
    def _apply_forgetting(self):
        for node in self._kg.graph.nodes:
            state = self._sg.get_state(node)
            if state is None:
                continue
            if state.mastery > 0:
                old = state.mastery
                state.mastery = max(0.0, state.mastery - 0.003)
                if old >= 0.70 and state.mastery < 0.70:
                    state.review_due = True

    def _record_and_forget(self, hub, concept, mastery_before, mastery_after):
        state_conc = self._sg.get_state(concept) if concept else None
        review_due = state_conc.review_due if state_conc else False
        self._history.append(MissionRecord(
            day=self._day,
            hub=hub,
            concept=concept,
            mastery_before=mastery_before,
            mastery_after=mastery_after,
            review_due=review_due,
        ))
        self._apply_forgetting()

    # ── Dia único ─────────────────────────────────────────────────────
    def simulate_day(self) -> dict:
        self._day += 1
        mission = self._engine.generate_study_mission()
        hub = mission["focus_hub"]
        concept = mission.get("study_concept")

        mastery_before = 0.0
        if concept:
            state = self._sg.get_state(concept)
            mastery_before = state.mastery if state else 0.0
            self.simulate_learning(concept)
            mastery_after = state.mastery if state else 0.0
        else:
            mastery_after = 0.0

        self._record_and_forget(hub, concept, mastery_before, mastery_after)

        return {
            "hub": hub,
            "concept": concept,
            "mastery_before": mastery_before,
            "mastery_after": mastery_after,
        }

    # ── Dia único diversificado ───────────────────────────────────────
    def simulate_day_diversified(self, policy) -> dict:
        self._day += 1
        mission = self._engine.generate_diversified_mission(policy)
        hub = mission["focus_hub"]
        concept = mission.get("study_concept")

        mastery_before = 0.0
        if concept:
            state = self._sg.get_state(concept)
            mastery_before = state.mastery if state else 0.0
            self.simulate_learning(concept)
            mastery_after = state.mastery if state else 0.0
        else:
            mastery_after = 0.0

        self._record_and_forget(hub, concept, mastery_before, mastery_after)

        return {
            "hub": hub,
            "concept": concept,
            "mastery_before": mastery_before,
            "mastery_after": mastery_after,
        }

    # ── Múltiplos dias ────────────────────────────────────────────────
    def simulate_days(self, n_days: int) -> list[dict]:
        results = []
        for _ in range(n_days):
            results.append(self.simulate_day())
        return results

    def simulate_days_diversified(self, n_days: int, policy) -> list[dict]:
        results = []
        for _ in range(n_days):
            results.append(self.simulate_day_diversified(policy))
        return results

    # ── Métricas de cobertura ─────────────────────────────────────────
    def coverage_metrics(self) -> dict:
        hubs_seen = set()
        concepts_seen = set()
        hub_dist = {}
        concept_dist = {}

        for r in self._history:
            hubs_seen.add(r.hub)
            hub_dist[r.hub] = hub_dist.get(r.hub, 0) + 1
            if r.concept:
                concepts_seen.add(r.concept)
                concept_dist[r.concept] = concept_dist.get(r.concept, 0) + 1

        return {
            "unique_hubs": len(hubs_seen),
            "unique_concepts": len(concepts_seen),
            "hub_distribution": hub_dist,
            "concept_distribution": concept_dist,
        }

    # ── Frequência de hubs ────────────────────────────────────────────
    def hub_frequency(self) -> dict:
        freq = {}
        for r in self._history:
            freq[r.hub] = freq.get(r.hub, 0) + 1
        return freq

    # ── Frequência de conceitos ───────────────────────────────────────
    def concept_frequency(self) -> dict:
        freq = {}
        for r in self._history:
            if r.concept:
                freq[r.concept] = freq.get(r.concept, 0) + 1
        return freq

    # ── Progresso de aprendizado ──────────────────────────────────────
    def learning_progress(self) -> dict:
        total = 0
        mastery_sum = 0.0
        mastered = 0
        weak = 0

        for node in self._kg.graph.nodes:
            state = self._sg.get_state(node)
            if state is None:
                continue
            total += 1
            mastery_sum += state.mastery
            if state.mastery >= 0.80:
                mastered += 1
            elif state.mastery < 0.40:
                weak += 1

        return {
            "average_mastery": round(mastery_sum / total, 4) if total > 0 else 0.0,
            "mastered_concepts": mastered,
            "weak_concepts": weak,
        }

    # ── Relatório de validação ────────────────────────────────────────
    def generate_validation_report(self) -> dict:
        cov = self.coverage_metrics()
        prog = self.learning_progress()
        hub_freq = self.hub_frequency()
        conc_freq = self.concept_frequency()

        top_hubs = sorted(hub_freq.items(), key=lambda x: -x[1])[:5]
        top_concepts = sorted(conc_freq.items(), key=lambda x: -x[1])[:5]

        return {
            "days_simulated": self._day,
            "unique_hubs": cov["unique_hubs"],
            "unique_concepts": cov["unique_concepts"],
            "top_hubs": top_hubs,
            "top_concepts": top_concepts,
            "average_mastery": prog["average_mastery"],
            "mastered_concepts": prog["mastered_concepts"],
            "weak_concepts": prog["weak_concepts"],
        }

    # ── Exportação CSV ────────────────────────────────────────────────
    def export_simulation_csv(self, path: str):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["day", "hub", "concept", "mastery_before", "mastery_after"])
            for r in self._history:
                w.writerow([r.day, r.hub, r.concept or "",
                            round(r.mastery_before, 6),
                            round(r.mastery_after, 6)])
