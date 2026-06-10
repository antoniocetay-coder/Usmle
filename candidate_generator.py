from knowledge_graph import KnowledgeGraph
from student_graph import StudentGraph
from centrality import CentralityAnalyzer


class CandidateGenerator:

    def __init__(self, knowledge_graph: KnowledgeGraph,
                 student_graph: StudentGraph,
                 centrality_analyzer: CentralityAnalyzer):
        self._kg = knowledge_graph
        self._sg = student_graph
        self._centrality = centrality_analyzer

    # ── Regra 2 — Pré-requisitos ──────────────────────────────────────
    def prerequisites_satisfied(self, concept_id: str) -> bool:
        if not self._kg.has_concept(concept_id):
            return False
        parents = self._kg.get_parents(concept_id)
        if not parents:
            return True
        for prereq in parents:
            state = self._sg.get_state(prereq)
            if state is None or state.mastery < 0.80:
                return False
        return True

    # ── Regra 3 — Bloqueados ──────────────────────────────────────────
    def blocked_concepts(self) -> list[str]:
        blocked = []
        for node in self._kg.graph.nodes:
            if not self.prerequisites_satisfied(node):
                blocked.append(node)
        return blocked

    # ── Regra 4 — Elegíveis ───────────────────────────────────────────
    def eligible_concepts(self) -> list[str]:
        eligible = []
        for node in self._kg.graph.nodes:
            state = self._sg.get_state(node)
            if state is None:
                continue
            if state.review_due:
                eligible.append(node)
            elif self.prerequisites_satisfied(node):
                eligible.append(node)
        return eligible

    # ── Regra 5 — Snapshot ────────────────────────────────────────────
    def candidate_snapshot(self, concept_id: str) -> dict | None:
        if not self._kg.has_concept(concept_id):
            return None
        state = self._sg.get_state(concept_id)
        if state is None:
            return None
        return {
            "concept": concept_id,
            "mastery": state.mastery,
            "review_due": state.review_due,
            "pagerank": self._centrality.pagerank(concept_id),
            "betweenness": self._centrality.betweenness(concept_id),
            "descendants": self._kg.descendants_count(concept_id),
            "depth": self._kg.max_descendant_depth(concept_id),
            "prerequisites_satisfied": self.prerequisites_satisfied(concept_id),
        }

    # ── Regra 6 — Estatísticas ────────────────────────────────────────
    def candidate_summary(self) -> dict:
        eligible = self.eligible_concepts()
        blocked = self.blocked_concepts()
        due = 0
        new_avail = 0
        for node in eligible:
            state = self._sg.get_state(node)
            if state is None:
                continue
            if state.review_due:
                due += 1
            else:
                new_avail += 1
        return {
            "eligible": len(eligible),
            "blocked": len(blocked),
            "due_reviews": due,
            "new_available": new_avail,
        }
