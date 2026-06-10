from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from knowledge_graph import KnowledgeGraph
from centrality import CentralityAnalyzer


@dataclass
class ConceptState:
    concept_id: str
    mastery: float = 0.0
    uncertainty: float = 1.0
    attempts: int = 0
    correct: int = 0
    confidence: float = 0.0
    last_seen: Optional[datetime] = None
    review_due: bool = False


class StudentGraph:

    def __init__(self, knowledge_graph: KnowledgeGraph,
                 centrality: CentralityAnalyzer):
        self._kg = knowledge_graph
        self._centrality = centrality
        self._states: dict[str, ConceptState] = {}

        for node in self._kg.graph.nodes:
            self._states[node] = ConceptState(concept_id=node)

    @property
    def states(self) -> dict[str, ConceptState]:
        return self._states

    def get_state(self, concept_id: str) -> Optional[ConceptState]:
        return self._states.get(concept_id, None)

    def load_from_db(self, tag_stats: dict = None):
        if tag_stats is None:
            from analytics import get_tag_stats
            tag_stats = get_tag_stats()
        for tag, data in tag_stats.items():
            if tag in self._states:
                s = self._states[tag]
                s.mastery = data.get("mastery_prob") or 0.15
                s.attempts = data.get("total") or 0
                s.correct = data.get("correct") or 0

    def update_concept(self, concept_id: str, mastery: Optional[float] = None,
                       uncertainty: Optional[float] = None,
                       confidence: Optional[float] = None,
                       review_due: Optional[bool] = None):
        state = self._states.get(concept_id)
        if state is None:
            return
        if mastery is not None:
            state.mastery = mastery
        if uncertainty is not None:
            state.uncertainty = uncertainty
        if confidence is not None:
            state.confidence = confidence
        if review_due is not None:
            state.review_due = review_due
        state.last_seen = datetime.now()

    def get_concept_snapshot(self, concept_id: str) -> Optional[dict]:
        if concept_id not in self._states:
            return None
        state = self._states[concept_id]
        return {
            "concept": concept_id,
            "mastery": state.mastery,
            "uncertainty": state.uncertainty,
            "confidence": state.confidence,
            "degree": self._centrality.degree(concept_id),
            "pagerank": self._centrality.pagerank(concept_id),
            "betweenness": self._centrality.betweenness(concept_id),
            "descendants": self._kg.descendants_count(concept_id),
            "depth": self._kg.max_descendant_depth(concept_id),
            "review_due": state.review_due,
        }

    def student_summary(self) -> dict:
        total = len(self._states)
        mastered = sum(1 for s in self._states.values() if s.mastery >= 0.80)
        weak = sum(1 for s in self._states.values() if s.mastery < 0.40)
        due_reviews = sum(1 for s in self._states.values() if s.review_due)
        avg = (sum(s.mastery for s in self._states.values()) / total
               if total > 0 else 0.0)

        return {
            "total_concepts": total,
            "mastered": mastered,
            "weak": weak,
            "due_reviews": due_reviews,
            "average_mastery": round(avg, 4),
        }

    def export_student_snapshot_csv(self, path: str):
        nodes = list(self._states.keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                "concept", "mastery", "uncertainty", "confidence",
                "degree", "pagerank", "betweenness",
                "descendants", "depth", "review_due",
            ])
            for node in nodes:
                snap = self.get_concept_snapshot(node)
                w.writerow([
                    snap["concept"],
                    round(snap["mastery"], 6),
                    round(snap["uncertainty"], 6),
                    round(snap["confidence"], 6),
                    round(snap["degree"], 6),
                    round(snap["pagerank"], 6),
                    round(snap["betweenness"], 6),
                    snap["descendants"],
                    snap["depth"],
                    snap["review_due"],
                ])
