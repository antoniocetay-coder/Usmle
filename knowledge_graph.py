import json
import networkx as nx
from functools import lru_cache


class KnowledgeGraph:

    def __init__(self, json_path="prerequisite.json"):
        self.graph = nx.DiGraph()
        self._load(json_path)
        self._validate()

    # ── 1. Carga ────────────────────────────────────────────────────────
    def _load(self, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for concept, prereqs in data.items():
            self.graph.add_node(concept)
            for prereq in prereqs:
                self.graph.add_node(prereq)
                self.graph.add_edge(prereq, concept)

    # ── 2. Validação DAG (auto-resolve ciclos) ─────────────────────────
    def _validate(self):
        removidas = []
        while not nx.is_directed_acyclic_graph(self.graph):
            try:
                cycle = nx.find_cycle(self.graph)
            except nx.NetworkXNoCycle:
                break
            melhor = None
            menor = float("inf")
            for source, target in cycle:
                qtd = len(nx.descendants(self.graph, source))
                if qtd < menor:
                    menor = qtd
                    melhor = (source, target)
            self.graph.remove_edge(*melhor)
            removidas.append(melhor)
        if removidas:
            import warnings
            warnings.warn(
                f"Removed {len(removidas)} cycle edge(s) to enforce DAG: "
                + "; ".join(f"{s} → {t}" for s, t in removidas)
            )

    # ── 3. Utilidades ──────────────────────────────────────────────────
    def has_concept(self, concept_id):
        return self.graph.has_node(concept_id)

    # ── 4. Consultas (com proteção) ────────────────────────────────────
    def get_parents(self, concept_id):
        if not self.has_concept(concept_id):
            return []
        return list(self.graph.predecessors(concept_id))

    def get_children(self, concept_id):
        if not self.has_concept(concept_id):
            return []
        return list(self.graph.successors(concept_id))

    @lru_cache(maxsize=None)
    def _get_ancestors_set(self, concept_id):
        if not self.has_concept(concept_id):
            return frozenset()
        try:
            return frozenset(nx.ancestors(self.graph, concept_id))
        except nx.NetworkXError:
            return frozenset()

    @lru_cache(maxsize=None)
    def _get_descendants_set(self, concept_id):
        if not self.has_concept(concept_id):
            return frozenset()
        try:
            return frozenset(nx.descendants(self.graph, concept_id))
        except nx.NetworkXError:
            return frozenset()

    def get_ancestors(self, concept_id):
        return list(self._get_ancestors_set(concept_id))

    def get_descendants(self, concept_id):
        return list(self._get_descendants_set(concept_id))

    def ancestors_count(self, concept_id):
        return len(self._get_ancestors_set(concept_id))

    def descendants_count(self, concept_id):
        return len(self._get_descendants_set(concept_id))

    # ── 5. Profundidade máxima ─────────────────────────────────────────
    @lru_cache(maxsize=None)
    def max_descendant_depth(self, concept_id):
        if not self.has_concept(concept_id):
            return -1
        children = self.get_children(concept_id)
        if not children:
            return 0
        return 1 + max(self.max_descendant_depth(c) for c in children)

    # ── 6. Top N por descendentes ──────────────────────────────────────
    def top_concepts_by_descendants(self, n=20):
        counts = [(node, self.descendants_count(node))
                  for node in self.graph.nodes]
        counts.sort(key=lambda x: -x[1])
        return counts[:n]
