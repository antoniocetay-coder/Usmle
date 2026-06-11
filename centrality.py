import networkx as nx
import csv

from knowledge_graph import KnowledgeGraph


# ── 1. Degree Centrality ──────────────────────────────────────────────
def calculate_degree_centrality(graph):
    return nx.degree_centrality(graph)


# ── 2. PageRank (pure Python, no scipy) ────────────────────────────────
def calculate_pagerank(graph, alpha=0.85, max_iter=100, tol=1e-6):
    n = graph.number_of_nodes()
    if n == 0:
        return {}
    nodes = list(graph.nodes)
    idx = {n: i for i, n in enumerate(nodes)}
    pr = [1.0 / n] * n
    out_degree = [len(list(graph.successors(nodes[i]))) for i in range(n)]
    for _ in range(max_iter):
        new_pr = [(1.0 - alpha) / n] * n
        for i in range(n):
            if out_degree[i] == 0:
                continue
            for succ in graph.successors(nodes[i]):
                j = idx[succ]
                new_pr[j] += alpha * pr[i] / out_degree[i]
        diff = sum(abs(new_pr[i] - pr[i]) for i in range(n))
        pr = new_pr
        if diff < tol:
            break
    return {nodes[i]: pr[i] for i in range(n)}


# ── 3. Betweenness Centrality ─────────────────────────────────────────
def calculate_betweenness(graph):
    return nx.betweenness_centrality(graph)


# ── 4. CentralityAnalyzer ─────────────────────────────────────────────
class CentralityAnalyzer:

    def __init__(self, knowledge_graph):
        self.kg = knowledge_graph
        self.graph = knowledge_graph.graph
        self._degree = calculate_degree_centrality(self.graph)
        self._pagerank = calculate_pagerank(self.graph)
        self._betweenness = calculate_betweenness(self.graph)

    # ── Rankings ───────────────────────────────────────────────────────
    def _sorted(self, scores, n):
        items = sorted(scores.items(), key=lambda x: -x[1])
        return items[:n]

    def top_by_degree(self, n=25):
        return self._sorted(self._degree, n)

    def top_by_pagerank(self, n=25):
        return self._sorted(self._pagerank, n)

    def top_by_betweenness(self, n=25):
        return self._sorted(self._betweenness, n)

    # ── Acesso bruto ───────────────────────────────────────────────────
    def degree(self, concept):
        return self._degree.get(concept, 0.0)

    def pagerank(self, concept):
        return self._pagerank.get(concept, 0.0)

    def betweenness(self, concept):
        return self._betweenness.get(concept, 0.0)

    # ── Export CSV ─────────────────────────────────────────────────────
    def export_metrics_csv(self, path):
        nodes = list(self.graph.nodes)
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["concept", "degree", "pagerank", "betweenness",
                         "descendants", "depth"])
            for node in nodes:
                w.writerow([
                    node,
                    round(self._degree.get(node, 0), 6),
                    round(self._pagerank.get(node, 0), 6),
                    round(self._betweenness.get(node, 0), 6),
                    self.kg.descendants_count(node),
                    self.kg.max_descendant_depth(node),
                ])

    # ── Summary ─────────────────────────────────────────────────────────
    def generate_summary(self):
        return {
            "graph_nodes": self.graph.number_of_nodes(),
            "graph_edges": self.graph.number_of_edges(),
            "highest_degree": self.top_by_degree(10),
            "highest_pagerank": self.top_by_pagerank(10),
            "highest_betweenness": self.top_by_betweenness(10),
        }
