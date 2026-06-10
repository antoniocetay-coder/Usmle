"""
Confusion Engine — Cognitive Confusion Modeling System

Architecture:
    Global (population-level):
        ConfusionEdge / ConfusionGraph
    
    Per-student (individual cognitive map):
        StudentConfusionEdge / StudentConfusionGraph
    
    Orchestrator:
        ConfusionTracker — records events, updates both layers simultaneously
    
    Resolution:
        StudentConfusionGraph tracks correct streaks and computes confusion_mastery
        resolved_score ∈ [0, 1] — how much a specific confusion has been overcome
        confusion_mastery ∈ [0, 1] — 1.0 = no confusion, 0.0 = extreme confusion

Relations:
    CONFUSED_WITH (bidirectional, weight ∈ [0, 1], dynamic, per-student)

Formulas:
    delta          = BASE_DELTA × frequency_mult × recency_mult × confidence_mult
    new_weight     = min(1.0, old_weight + delta)
    resolved_score = 1.0 - (1.0 - resolved_score) × exp(-correct_streak / RESOLUTION_DECAY)
    confusion_mastery = 1.0 - weight × (1.0 - resolved_score)
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import networkx as nx

# ── Constants ──────────────────────────────────────────────────────────

BASE_DELTA = 0.15
RESOLUTION_DECAY = 5.0

CONFIDENCE_MULTIPLIER = {
    "Certeza Absoluta": 1.0,
    "Dúvida entre 2": 0.6,
    "Chute Cego": 0.2,
}

DISCOVERY_WEIGHTS = {
    "taxonomy": 0.4,
    "graph": 0.3,
    "ancestor": 0.3,
}

DEFAULT_STUDENT_ID = "default"


# ═══════════════════════════════════════════════════════════════════════
# GLOBAL LAYER
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class ConfusionEdge:
    """A single global confusion relationship between two concepts."""
    concept_a: str
    concept_b: str
    weight: float = 0.0
    evidence_count: int = 0
    source: str = "response"
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

    @property
    def normalized(self) -> tuple[str, str]:
        a, b = (self.concept_a, self.concept_b) if self.concept_a <= self.concept_b else (self.concept_b, self.concept_a)
        return a, b

    def to_dict(self) -> dict:
        return {
            "concept_a": self.concept_a,
            "concept_b": self.concept_b,
            "weight": round(self.weight, 4),
            "evidence_count": self.evidence_count,
            "source": self.source,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }


class ConfusionGraph:
    """Bidirectional weighted confusion graph (global / population-level)."""

    def __init__(self, knowledge_graph=None):
        self._edges: dict[tuple[str, str], ConfusionEdge] = {}
        self._kg = knowledge_graph

    # ── Loading ────────────────────────────────────────────────────────

    def load_from_db(self):
        from database import get_conn
        conn = get_conn()
        rows = conn.execute("""
            SELECT concept_a, concept_b, weight, evidence_count, source, first_seen, last_seen
            FROM confusion_edges
        """).fetchall()
        for r in rows:
            key = self._normalize(r["concept_a"], r["concept_b"])
            self._edges[key] = ConfusionEdge(
                concept_a=r["concept_a"], concept_b=r["concept_b"],
                weight=r["weight"], evidence_count=r["evidence_count"],
                source=r["source"],
                first_seen=self._parse_dt(r["first_seen"]),
                last_seen=self._parse_dt(r["last_seen"]),
            )

    def load_from_legacy_confusion_pairs(self):
        from database import get_conn
        conn = get_conn()
        rows = conn.execute("""
            SELECT tag_correct, tag_confused, count, last_seen
            FROM confusion_pairs
        """).fetchall()
        for r in rows:
            key = self._normalize(r["tag_correct"], r["tag_confused"])
            if key not in self._edges:
                self._edges[key] = ConfusionEdge(
                    concept_a=key[0], concept_b=key[1],
                    weight=min(1.0, r["count"] * 0.1),
                    evidence_count=r["count"], source="legacy",
                    first_seen=self._parse_dt(r["last_seen"]),
                    last_seen=self._parse_dt(r["last_seen"]),
                )

    # ── Access ─────────────────────────────────────────────────────────

    def get_weight(self, concept_a: str, concept_b: str) -> float:
        key = self._normalize(concept_a, concept_b)
        edge = self._edges.get(key)
        if edge:
            return edge.weight
        if self._kg and self._kg.has_concept(concept_a) and self._kg.has_concept(concept_b):
            try:
                dist = len(self._kg.get_ancestors(concept_a)) + len(self._kg.get_ancestors(concept_b))
            except Exception:
                dist = 0
            return max(0.0, 0.15 - dist * 0.005)
        return 0.0

    def get_edge(self, concept_a: str, concept_b: str) -> Optional[ConfusionEdge]:
        key = self._normalize(concept_a, concept_b)
        return self._edges.get(key)

    def top_confusions_for(self, concept: str, n: int = 10) -> list[dict]:
        candidates = []
        for (a, b), edge in self._edges.items():
            if a == concept:
                candidates.append((b, edge.weight, edge.evidence_count))
            elif b == concept:
                candidates.append((a, edge.weight, edge.evidence_count))
        candidates.sort(key=lambda x: -x[1])
        return [
            {"concept": c, "weight": w, "evidence_count": e}
            for c, w, e in candidates[:n]
        ]

    def global_top_confusions(self, n: int = 20) -> list[dict]:
        sorted_edges = sorted(self._edges.values(), key=lambda e: -e.weight)
        return [e.to_dict() for e in sorted_edges[:n]]

    def all_edges(self) -> list[ConfusionEdge]:
        return list(self._edges.values())

    def edge_count(self) -> int:
        return len(self._edges)

    # ── Mutation ───────────────────────────────────────────────────────

    def upsert_edge(self, concept_a: str, concept_b: str, weight: float,
                    evidence_count: int, source: str = "response"):
        if concept_a == concept_b:
            return
        now = datetime.now(timezone.utc)
        key = self._normalize(concept_a, concept_b)
        if key in self._edges:
            edge = self._edges[key]
            edge.weight = weight
            edge.evidence_count = evidence_count
            edge.source = source
            edge.last_seen = now
        else:
            self._edges[key] = ConfusionEdge(
                concept_a=key[0], concept_b=key[1],
                weight=weight, evidence_count=evidence_count,
                source=source, first_seen=now, last_seen=now,
            )

    # ── Discovery ──────────────────────────────────────────────────────

    def discover_candidates(self, taxonomy: dict, n: int = 5) -> list[dict]:
        from database import get_conn
        existing = set(self._edges.keys())
        candidates = []
        concepts = list(self._kg.graph.nodes) if self._kg else []
        concept_to_sys = {}
        concept_to_disc = {}
        for sys_name, disciplines in taxonomy.items():
            for disc_name, tags in disciplines.items():
                if isinstance(tags, list):
                    for t in tags:
                        concept_to_sys[t] = sys_name
                        concept_to_disc[t] = disc_name
        for i, a in enumerate(concepts):
            for b in concepts[i + 1:]:
                key = (a, b)
                if key in existing:
                    continue
                tax_prox = self._taxonomy_proximity(a, b, concept_to_sys, concept_to_disc)
                graph_prox = self._graph_proximity(a, b)
                ancestor_prox = self._ancestor_overlap(a, b)
                score = (
                    DISCOVERY_WEIGHTS["taxonomy"] * tax_prox +
                    DISCOVERY_WEIGHTS["graph"] * graph_prox +
                    DISCOVERY_WEIGHTS["ancestor"] * ancestor_prox
                )
                if score >= 0.15:
                    candidates.append({
                        "concept_a": a, "concept_b": b, "score": round(score, 4),
                        "taxonomy_proximity": round(tax_prox, 4),
                        "graph_proximity": round(graph_prox, 4),
                        "ancestor_overlap": round(ancestor_prox, 4),
                    })
        candidates.sort(key=lambda x: -x["score"])
        return candidates[:n]

    def _taxonomy_proximity(self, a, b, concept_to_sys, concept_to_disc):
        sys_a, sys_b = concept_to_sys.get(a), concept_to_sys.get(b)
        disc_a, disc_b = concept_to_disc.get(a), concept_to_disc.get(b)
        if not sys_a or not sys_b:
            return 0.0
        if sys_a == sys_b and disc_a == disc_b:
            return 0.9
        if sys_a == sys_b:
            return 0.6
        return 0.1

    def _graph_proximity(self, a, b):
        if not self._kg or not self._kg.has_concept(a) or not self._kg.has_concept(b):
            return 0.0
        try:
            distance = len(nx.shortest_path(self._kg.graph, a, b)) - 1
        except Exception:
            try:
                distance = len(nx.shortest_path(self._kg.graph, b, a)) - 1
            except Exception:
                return 0.0
        if distance <= 1:
            return 0.8
        if distance == 2:
            return 0.5
        if distance == 3:
            return 0.2
        return 0.1

    def _ancestor_overlap(self, a, b):
        if not self._kg:
            return 0.0
        anc_a = set(self._kg.get_ancestors(a))
        anc_b = set(self._kg.get_ancestors(b))
        if not anc_a or not anc_b:
            return 0.0
        intersection = anc_a & anc_b
        union = anc_a | anc_b
        return len(intersection) / len(union) if union else 0.0

    # ── Persistence ────────────────────────────────────────────────────

    def save_to_db(self):
        from database import get_conn
        conn = get_conn()
        now = datetime.now(timezone.utc).isoformat()
        for edge in self._edges.values():
            conn.execute("""
                INSERT INTO confusion_edges (concept_a, concept_b, weight, evidence_count, source, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(concept_a, concept_b) DO UPDATE SET
                    weight = excluded.weight,
                    evidence_count = excluded.evidence_count,
                    source = excluded.source,
                    last_seen = excluded.last_seen
            """, (edge.concept_a, edge.concept_b, edge.weight, edge.evidence_count,
                  edge.source,
                  edge.first_seen.isoformat() if edge.first_seen else now,
                  edge.last_seen.isoformat() if edge.last_seen else now))
        conn.commit()

    # ── Internals ──────────────────────────────────────────────────────

    @staticmethod
    def _normalize(a: str, b: str) -> tuple[str, str]:
        return (a, b) if a <= b else (b, a)

    @staticmethod
    def _parse_dt(s: Optional[str]) -> Optional[datetime]:
        if not s:
            return None
        try:
            return datetime.fromisoformat(s)
        except (ValueError, TypeError):
            return None


# ═══════════════════════════════════════════════════════════════════════
# STUDENT LAYER
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class StudentConfusionEdge:
    """
    A per-student confusion relationship.

    Fields:
        weight: current confusion weight [0, 1]
        evidence_count: total confusion events observed
        correct_streak: consecutive correct answers involving this pair
        resolved_score: how much the student has overcome this confusion [0, 1]
        first_seen / last_seen: event timestamps
    """
    student_id: str
    concept_a: str
    concept_b: str
    weight: float = 0.0
    evidence_count: int = 0
    correct_streak: int = 0
    resolved_score: float = 0.0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

    @property
    def normalized(self) -> tuple[str, str]:
        a, b = (self.concept_a, self.concept_b) if self.concept_a <= self.concept_b else (self.concept_b, self.concept_a)
        return a, b

    @property
    def confusion_mastery(self) -> float:
        """
        1.0 = no confusion (mastered)
        0.0 = extreme confusion
        """
        return 1.0 - self.weight * (1.0 - self.resolved_score)

    def to_dict(self) -> dict:
        return {
            "student_id": self.student_id,
            "concept_a": self.concept_a,
            "concept_b": self.concept_b,
            "weight": round(self.weight, 4),
            "evidence_count": self.evidence_count,
            "correct_streak": self.correct_streak,
            "resolved_score": round(self.resolved_score, 4),
            "confusion_mastery": round(self.confusion_mastery, 4),
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }


class StudentConfusionGraph:
    """
    Per-student confusion graph.
    Tracks individual confusion patterns, correct streaks, and resolution.
    """

    def __init__(self, knowledge_graph=None, student_id: str = DEFAULT_STUDENT_ID):
        self._student_id = student_id
        self._edges: dict[tuple[str, str], StudentConfusionEdge] = {}
        self._kg = knowledge_graph

    # ── Loading ────────────────────────────────────────────────────────

    def load_from_db(self):
        from database import get_conn
        conn = get_conn()
        rows = conn.execute("""
            SELECT student_id, concept_a, concept_b, weight, evidence_count,
                   correct_streak, resolved_score, first_seen, last_seen
            FROM student_confusions
            WHERE student_id = ?
        """, (self._student_id,)).fetchall()
        for r in rows:
            key = self._normalize(r["concept_a"], r["concept_b"])
            self._edges[key] = StudentConfusionEdge(
                student_id=r["student_id"],
                concept_a=r["concept_a"], concept_b=r["concept_b"],
                weight=r["weight"], evidence_count=r["evidence_count"],
                correct_streak=r["correct_streak"] or 0,
                resolved_score=r["resolved_score"] or 0.0,
                first_seen=self._parse_dt(r["first_seen"]),
                last_seen=self._parse_dt(r["last_seen"]),
            )

    # ── Access ─────────────────────────────────────────────────────────

    def get_edge(self, concept_a: str, concept_b: str) -> Optional[StudentConfusionEdge]:
        key = self._normalize(concept_a, concept_b)
        return self._edges.get(key)

    def get_weight(self, concept_a: str, concept_b: str) -> float:
        edge = self.get_edge(concept_a, concept_b)
        return edge.weight if edge else 0.0

    def get_confusion_mastery(self, concept_a: str, concept_b: str) -> float:
        edge = self.get_edge(concept_a, concept_b)
        return edge.confusion_mastery if edge else 1.0

    def top_confusions_for(self, concept: str, n: int = 10) -> list[dict]:
        candidates = []
        for (a, b), edge in self._edges.items():
            if a == concept:
                candidates.append((b, edge.weight, edge.evidence_count, edge.confusion_mastery))
            elif b == concept:
                candidates.append((a, edge.weight, edge.evidence_count, edge.confusion_mastery))
        candidates.sort(key=lambda x: -x[1])
        return [
            {"concept": c, "weight": w, "evidence_count": e, "confusion_mastery": m}
            for c, w, e, m in candidates[:n]
        ]

    def all_edges(self) -> list[StudentConfusionEdge]:
        return list(self._edges.values())

    def edge_count(self) -> int:
        return len(self._edges)

    def active_confusions(self, min_weight: float = 0.1) -> list[StudentConfusionEdge]:
        """Confusions that are still active (not resolved)."""
        return [e for e in self._edges.values() if e.weight >= min_weight and e.confusion_mastery < 0.85]

    def resolved_confusions(self, min_mastery: float = 0.85) -> list[StudentConfusionEdge]:
        return [e for e in self._edges.values() if e.confusion_mastery >= min_mastery]

    # ── Event Recording ────────────────────────────────────────────────

    def record_confusion_event(self, correct_tag: str, chosen_tag: str,
                                confidence_label: Optional[str] = None,
                                question_id: Optional[str] = None):
        """
        Record that the student confused chosen_tag with correct_tag.
        Increase weight, reset correct_streak.
        """
        if correct_tag == chosen_tag:
            return

        now = datetime.now(timezone.utc)
        key = self._normalize(correct_tag, chosen_tag)
        edge = self._edges.get(key)

        if edge:
            old_weight = edge.weight
            old_count = edge.evidence_count
            last_seen = edge.last_seen or now
            days_since = (now - last_seen).days
            delta = _compute_weight_delta(
                evidence_count=old_count + 1,
                confidence_label=confidence_label or "",
                days_since_last=days_since,
            )
            edge.weight = min(1.0, old_weight + delta)
            edge.evidence_count = old_count + 1
            edge.correct_streak = 0
            edge.resolved_score = max(0.0, edge.resolved_score * 0.5)
            edge.last_seen = now
        else:
            delta = _compute_weight_delta(
                evidence_count=1,
                confidence_label=confidence_label or "",
                days_since_last=0,
            )
            self._edges[key] = StudentConfusionEdge(
                student_id=self._student_id,
                concept_a=key[0], concept_b=key[1],
                weight=min(0.5, delta),
                evidence_count=1,
                correct_streak=0,
                resolved_score=0.0,
                first_seen=now, last_seen=now,
            )

    def record_correct_answer(self, concept_a: str, concept_b: Optional[str] = None):
        """
        Record that the student answered correctly about concept_a.
        If concept_b is given, it resolves a specific confusion pair.
        If only concept_a, resolve all edges involving that concept.
        """
        now = datetime.now(timezone.utc)

        if concept_b:
            key = self._normalize(concept_a, concept_b)
            self._apply_resolution(key, now)
        else:
            for key in list(self._edges.keys()):
                if key[0] == concept_a or key[1] == concept_a:
                    self._apply_resolution(key, now)

    def _apply_resolution(self, key: tuple[str, str], now: datetime):
        if key not in self._edges:
            return
        edge = self._edges[key]
        edge.correct_streak += 1
        edge.last_seen = now

        # resolved_score approaches 1.0 asymptotically with correct streaks
        edge.resolved_score = 1.0 - (1.0 - edge.resolved_score) * math.exp(-edge.correct_streak / RESOLUTION_DECAY)

        # weight decays when resolution is high
        if edge.resolved_score > 0.7:
            edge.weight *= max(0.5, 1.0 - edge.resolved_score * 0.3)

    # ── Ranking / Remediation ──────────────────────────────────────────

    def top_unresolved_confusions(self, n: int = 5) -> list[dict]:
        """Return the student's most impactful unresolved confusions."""
        active = self.active_confusions(min_weight=0.1)
        scored = []
        for e in active:
            impact = e.weight * (1.0 - e.resolved_score) * e.evidence_count
            scored.append((e, impact))
        scored.sort(key=lambda x: -x[1])
        return [
            {
                "concept_a": e.concept_a,
                "concept_b": e.concept_b,
                "weight": e.weight,
                "confusion_mastery": e.confusion_mastery,
                "impact": round(impact, 4),
                "evidence_count": e.evidence_count,
            }
            for e, impact in scored[:n]
        ]

    def confusion_remediation_score(self, concept_id: str) -> float:
        """
        How much value would studying this concept provide for resolving confusions?
        High if concept appears in many unresolved edges with high weight.
        """
        confusions = self.top_confusions_for(concept_id, n=5)
        if not confusions:
            return 0.0
        score = sum(
            (1.0 - c["confusion_mastery"]) * c["weight"]
            for c in confusions
        )
        return round(min(1.0, score / 3.0), 4)

    # ── Missions ───────────────────────────────────────────────────────

    def generate_remediation_missions(self, n: int = 3) -> list[dict]:
        """Generate 'Differentiate' / 'Compare' missions from top confusions."""
        top = self.top_unresolved_confusions(n=n)
        missions = []
        for i, c in enumerate(top):
            missions.append({
                "type": "Differentiate",
                "concept_a": c["concept_a"],
                "concept_b": c["concept_b"],
                "reason": (
                    f"confusion weight: {c['weight']:.0%}, "
                    f"mastery: {c['confusion_mastery']:.0%}, "
                    f"occurrences: {c['evidence_count']}"
                ),
                "priority": i + 1,
                "impact": c["impact"],
            })
        return missions

    # ── Persistence ────────────────────────────────────────────────────

    def save_to_db(self):
        from database import get_conn
        conn = get_conn()
        now = datetime.now(timezone.utc).isoformat()
        for edge in self._edges.values():
            conn.execute("""
                INSERT INTO student_confusions
                    (student_id, concept_a, concept_b, weight, evidence_count,
                     correct_streak, resolved_score, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(student_id, concept_a, concept_b) DO UPDATE SET
                    weight = excluded.weight,
                    evidence_count = excluded.evidence_count,
                    correct_streak = excluded.correct_streak,
                    resolved_score = excluded.resolved_score,
                    last_seen = excluded.last_seen
            """, (
                self._student_id,
                edge.concept_a, edge.concept_b, edge.weight,
                edge.evidence_count, edge.correct_streak,
                edge.resolved_score,
                edge.first_seen.isoformat() if edge.first_seen else now,
                edge.last_seen.isoformat() if edge.last_seen else now,
            ))
        conn.commit()

    # ── Analytics ──────────────────────────────────────────────────────

    def confusion_dashboard(self) -> dict:
        active = self.active_confusions()
        resolved = self.resolved_confusions()
        total = self.edge_count()
        avg_mastery = (
            sum(e.confusion_mastery for e in self._edges.values()) / total
            if total > 0 else 1.0
        )
        top_unresolved = self.top_unresolved_confusions(n=5)
        return {
            "total_edges": total,
            "active_confusions": len(active),
            "resolved_confusions": len(resolved),
            "average_confusion_mastery": round(avg_mastery, 4),
            "top_unresolved": top_unresolved,
        }

    # ── Internals ──────────────────────────────────────────────────────

    @staticmethod
    def _normalize(a: str, b: str) -> tuple[str, str]:
        return (a, b) if a <= b else (b, a)

    @staticmethod
    def _parse_dt(s: Optional[str]) -> Optional[datetime]:
        if not s:
            return None
        try:
            return datetime.fromisoformat(s)
        except (ValueError, TypeError):
            return None


# ═══════════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════

class ConfusionTracker:
    """
    Orchestrator that records confusion events and updates BOTH
    the global ConfusionGraph and the per-student StudentConfusionGraph.
    """

    def __init__(self, global_graph: ConfusionGraph,
                 student_graph: StudentConfusionGraph,
                 knowledge_graph=None):
        self.global_graph = global_graph
        self.student_graph = student_graph
        self._kg = knowledge_graph

    # ── Event Recording ────────────────────────────────────────────────

    def record_event(self, correct_tag: str, chosen_tag: str,
                     confidence_label: Optional[str] = None,
                     question_id: Optional[str] = None):
        """Record confusion event in BOTH global and student graphs."""
        if correct_tag == chosen_tag:
            return

        now = datetime.now(timezone.utc)

        # ── Update global ──
        global_existing = self.global_graph.get_edge(correct_tag, chosen_tag)
        old_w = global_existing.weight if global_existing else 0.0
        old_c = global_existing.evidence_count if global_existing else 0
        last_seen = global_existing.last_seen if global_existing else now
        days_since = (now - last_seen).days if last_seen else 0

        delta = _compute_weight_delta(
            evidence_count=old_c + 1,
            confidence_label=confidence_label or "",
            days_since_last=days_since,
        )
        new_weight = min(1.0, old_w + delta)
        new_count = old_c + 1

        self.global_graph.upsert_edge(
            concept_a=correct_tag, concept_b=chosen_tag,
            weight=new_weight, evidence_count=new_count, source="response",
        )

        # ── Update student ──
        self.student_graph.record_confusion_event(
            correct_tag=correct_tag, chosen_tag=chosen_tag,
            confidence_label=confidence_label, question_id=question_id,
        )

        # ── Log raw event ──
        self._log_event(correct_tag, chosen_tag, new_weight,
                        confidence_label, question_id)

        return {
            "correct": correct_tag,
            "chosen": chosen_tag,
            "global_weight": new_weight,
            "global_evidence": new_count,
        }

    def record_correct_answer(self, concept_tags: list[str]):
        """
        Record that the student answered correctly about these concepts.
        This triggers resolution in the student graph.
        """
        for tag in concept_tags:
            self.student_graph.record_correct_answer(tag)

    # ── Candidate Discovery ────────────────────────────────────────────

    def discover_and_persist(self, taxonomy: dict, n: int = 10) -> int:
        """Discover structural candidate confusions and persist to global."""
        candidates = self.global_graph.discover_candidates(taxonomy, n=n)
        inserted = 0
        for c in candidates:
            existing = self.global_graph.get_edge(c["concept_a"], c["concept_b"])
            if existing is None:
                self.global_graph.upsert_edge(
                    concept_a=c["concept_a"], concept_b=c["concept_b"],
                    weight=c["score"] * 0.5, evidence_count=0,
                    source="structural",
                )
                inserted += 1
        if inserted:
            self.global_graph.save_to_db()
        return inserted

    # ── Event Logging ──────────────────────────────────────────────────

    def _log_event(self, concept_a, concept_b, weight,
                   confidence_label=None, question_id=None):
        from database import get_conn
        conn = get_conn()
        conn.execute("""
            INSERT INTO confusion_events
                (concept_a, concept_b, weight, confidence_label, question_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (concept_a, concept_b, weight, confidence_label, question_id,
              datetime.now(timezone.utc).isoformat()))
        conn.commit()

    # ── Query ──────────────────────────────────────────────────────────

    def get_student_confusions(self, concept: Optional[str] = None,
                                n: int = 10) -> list[dict]:
        """Query student confusions (falls back to global)."""
        if concept:
            return self.student_graph.top_confusions_for(concept, n=n)
        top = self.student_graph.top_unresolved_confusions(n=n)
        return top if top else self.global_graph.global_top_confusions(n=n)

    def confusion_heatmap(self, threshold: float = 0.3) -> list[dict]:
        return [e.to_dict() for e in self.student_graph.all_edges()
                if e.weight >= threshold]

    # ── Analytics ──────────────────────────────────────────────────────

    def get_student_top_confusions(self, n: int = 10) -> list[dict]:
        return self.student_graph.top_unresolved_confusions(n=n)

    def get_confusion_mastery(self, concept_a: str, concept_b: str) -> float:
        return self.student_graph.get_confusion_mastery(concept_a, concept_b)

    def get_resolved_confusions(self) -> list[dict]:
        return [e.to_dict() for e in self.student_graph.resolved_confusions()]

    def get_active_confusions(self) -> list[dict]:
        return [e.to_dict() for e in self.student_graph.active_confusions()]

    def confusion_dashboard(self) -> dict:
        return self.student_graph.confusion_dashboard()

    def generate_remediation_missions(self, n: int = 3) -> list[dict]:
        return self.student_graph.generate_remediation_missions(n=n)

    def confusion_explain(self, concept_id: str) -> dict:
        """Explain why a concept is being recommended based on confusions."""
        confusions = self.student_graph.top_confusions_for(concept_id, n=3)
        if not confusions:
            return {"concept": concept_id, "confusion_driven": False}
        lines = []
        for c in confusions:
            mastery = c["confusion_mastery"]
            lines.append(
                f"confused with {c['concept']} "
                f"(mastery: {mastery:.0%}, weight: {c['weight']:.0%})"
            )
        return {
            "concept": concept_id,
            "confusion_driven": True,
            "details": lines,
            "severity": "high" if any(
                c["confusion_mastery"] < 0.5 for c in confusions
            ) else "medium",
        }


# ═══════════════════════════════════════════════════════════════════════
# SHARED FORMULAS
# ═══════════════════════════════════════════════════════════════════════

def _compute_weight_delta(evidence_count: int,
                           confidence_label: str,
                           days_since_last: int) -> float:
    """
    delta = BASE_DELTA × frequency_mult × recency_mult × confidence_mult
    """
    frequency_mult = min(1.0, math.log2(1 + evidence_count) / 5.0)
    recency_mult = math.exp(-days_since_last / 30.0)
    confidence_mult = CONFIDENCE_MULTIPLIER.get(confidence_label, 0.4)
    return BASE_DELTA * frequency_mult * recency_mult * confidence_mult
