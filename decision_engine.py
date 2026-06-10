from knowledge_graph import KnowledgeGraph
from student_graph import StudentGraph
from centrality import CentralityAnalyzer
from candidate_generator import CandidateGenerator


class DecisionEngine:

    def __init__(self, knowledge_graph: KnowledgeGraph,
                 student_graph: StudentGraph,
                 centrality_analyzer: CentralityAnalyzer,
                 candidate_generator: CandidateGenerator):
        self._kg = knowledge_graph
        self._sg = student_graph
        self._centrality = centrality_analyzer
        self._cg = candidate_generator

    # ── Parte A — Focus Hub Selection ──────────────────────────────────
    def _student_density(self, concept_id: str) -> float:
        if not self._kg.has_concept(concept_id):
            return 0.0
        nodes = [concept_id] + self._kg.get_descendants(concept_id)
        if not nodes:
            return 0.0
        filled = 0
        for n in nodes:
            state = self._sg.get_state(n)
            if state is not None and (state.attempts > 0 or state.mastery > 0):
                filled += 1
        return filled / len(nodes)

    def _hub_score(self, concept_id: str) -> float:
        if not self._kg.has_concept(concept_id):
            return 0.0
        desc_count = self._kg.descendants_count(concept_id)
        depth = self._kg.max_descendant_depth(concept_id)
        degree = self._centrality.degree(concept_id)
        betweenness = self._centrality.betweenness(concept_id)

        n = self._kg.graph.number_of_nodes()
        max_desc = max((self._kg.descendants_count(c) for c in self._kg.graph.nodes), default=1)
        max_depth = max((self._kg.max_descendant_depth(c) for c in self._kg.graph.nodes), default=1)

        norm_desc = desc_count / max_desc if max_desc > 0 else 0.0
        norm_depth = depth / max_depth if max_depth > 0 else 0.0

        if desc_count > 0:
            descendants = self._kg.get_descendants(concept_id)
            masteries = []
            for d in descendants:
                state = self._sg.get_state(d)
                if state is not None:
                    masteries.append(state.mastery)
            avg_mastery = sum(masteries) / len(masteries) if masteries else 0.0
            region_weakness = 1.0 - avg_mastery
        else:
            region_weakness = 0.0

        student_density = self._student_density(concept_id)

        score = (degree + betweenness + norm_desc + norm_depth + region_weakness + student_density * 2) / 6.0
        return round(score, 6)

    def select_focus_hub(self) -> dict:
        best_hub = None
        best_score = -1.0
        for node in self._kg.graph.nodes:
            score = self._hub_score(node)
            if score > best_score:
                best_score = score
                best_hub = node
        return {"hub": best_hub, "score": best_score}

    # ── Parte F — Diversified Hub Score ────────────────────────────────
    def hub_score_with_diversification(self, hub_id, policy=None):
        base = self._hub_score(hub_id)
        if policy is not None:
            base *= policy.diversification_factor(hub_id)
        return round(base, 6)

    def select_focus_hub_diversified(self, policy):
        best_hub = None
        best_score = -1.0
        for node in self._kg.graph.nodes:
            score = self.hub_score_with_diversification(node, policy)
            if score > best_score:
                best_score = score
                best_hub = node
        return {"hub": best_hub, "score": best_score}

    def generate_diversified_mission(self, policy):
        hub_result = self.select_focus_hub_diversified(policy)
        hub_id = hub_result["hub"]
        study = self.select_study_concept(hub_id)
        if study is None:
            return {"focus_hub": hub_id, "study_concept": None, "reason": {}}
        concept_id = study["concept"]
        state = self._sg.get_state(concept_id)
        return {
            "focus_hub": hub_id,
            "study_concept": concept_id,
            "reason": {
                "hub_importance": hub_result["score"],
                "mastery": state.mastery if state else 0.0,
                "uncertainty": state.uncertainty if state else 1.0,
            },
        }

    # ── Parte B — Hub Cluster Expansion ────────────────────────────────
    def hub_cluster(self, concept_id: str) -> list[str]:
        if not self._kg.has_concept(concept_id):
            return []
        children = self._kg.get_children(concept_id)
        descendants = self._kg.get_descendants(concept_id)
        seen = set()
        result = []
        for c in children + descendants:
            if c not in seen:
                seen.add(c)
                result.append(c)
        return result

    # ── Parte C — Study Concept Selection ──────────────────────────────
    def _study_concept_score(self, concept_id: str) -> float:
        state = self._sg.get_state(concept_id)
        if state is None:
            return -1.0
        boost = 0.5 if state.review_due else 0.0
        return -state.mastery + state.uncertainty + boost

    def select_study_concept(self, hub_id: str) -> dict | None:
        cluster = self.hub_cluster(hub_id)
        eligible = set(self._cg.eligible_concepts())
        candidates = [hub_id] + [c for c in cluster if c != hub_id]
        candidates = [c for c in candidates if c in eligible]
        if not candidates:
            return None
        best = max(candidates, key=lambda c: self._study_concept_score(c))
        return {"hub": hub_id, "concept": best}

    # ── Parte D — Study Mission ────────────────────────────────────────
    def generate_study_mission(self) -> dict:
        hub_result = self.select_focus_hub()
        hub_id = hub_result["hub"]
        study = self.select_study_concept(hub_id)
        if study is None:
            return {"focus_hub": hub_id, "study_concept": None, "reason": {}}
        concept_id = study["concept"]
        state = self._sg.get_state(concept_id)
        return {
            "focus_hub": hub_id,
            "study_concept": concept_id,
            "reason": {
                "hub_importance": hub_result["score"],
                "mastery": state.mastery if state else 0.0,
                "uncertainty": state.uncertainty if state else 1.0,
            },
        }

    # ── Parte E — Explicabilidade ──────────────────────────────────────
    def explain_mission(self) -> dict:
        hub_result = self.select_focus_hub()
        hub_id = hub_result["hub"]
        study = self.select_study_concept(hub_id)

        why_hub = []
        betweenness = self._centrality.betweenness(hub_id)
        desc_count = self._kg.descendants_count(hub_id)
        depth = self._kg.max_descendant_depth(hub_id)
        if betweenness > 0:
            why_hub.append("high betweenness")
        if desc_count > 0:
            why_hub.append(f"{desc_count} descendants")
        if depth > 0:
            why_hub.append(f"depth {depth} in knowledge graph")
        if not why_hub:
            why_hub.append("structural concept")

        result = {
            "focus_hub": hub_id,
            "why_hub": why_hub,
        }

        if study and study.get("concept"):
            concept_id = study["concept"]
            state = self._sg.get_state(concept_id)
            why_concept = []
            if state:
                if state.mastery < 0.4:
                    why_concept.append("low mastery")
                if state.uncertainty > 0.6:
                    why_concept.append("high uncertainty")
                if state.review_due:
                    why_concept.append("review due")
            if not why_concept:
                why_concept.append("eligible for study")
            result["study_concept"] = concept_id
            result["why_concept"] = why_concept
        else:
            result["study_concept"] = None
            result["why_concept"] = ["no eligible concept in hub cluster"]

        return result
