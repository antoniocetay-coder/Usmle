import unittest
import os
import json
import tempfile
import math
from datetime import datetime, timezone, timedelta

from confusion_engine import (
    ConfusionEdge, ConfusionGraph, ConfusionTracker,
    BASE_DELTA, CONFIDENCE_MULTIPLIER,
)


def _seed_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS confusion_edges (
            concept_a TEXT NOT NULL, concept_b TEXT NOT NULL,
            weight REAL DEFAULT 0.0, evidence_count INTEGER DEFAULT 0,
            source TEXT DEFAULT 'response',
            first_seen TEXT NOT NULL, last_seen TEXT NOT NULL,
            PRIMARY KEY (concept_a, concept_b)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS confusion_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            concept_a TEXT NOT NULL, concept_b TEXT NOT NULL,
            weight REAL, confidence_label TEXT, question_id TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()


class TestConfusionEdge(unittest.TestCase):

    def test_normalized_orders_alphabetically(self):
        e1 = ConfusionEdge(concept_a="Zebra", concept_b="Alpha")
        self.assertEqual(e1.normalized, ("Alpha", "Zebra"))

    def test_to_dict_has_all_keys(self):
        e = ConfusionEdge(concept_a="Crohn", concept_b="UC", weight=0.82,
                          evidence_count=5, source="response",
                          first_seen=datetime(2026, 1, 1, tzinfo=timezone.utc),
                          last_seen=datetime(2026, 6, 1, tzinfo=timezone.utc))
        d = e.to_dict()
        self.assertEqual(d["concept_a"], "Crohn")
        self.assertEqual(d["concept_b"], "UC")
        self.assertEqual(d["weight"], 0.82)
        self.assertEqual(d["evidence_count"], 5)
        self.assertIn("2026-06-01", d["last_seen"])


class TestConfusionGraph(unittest.TestCase):

    def setUp(self):
        import config
        self.orig_db_path = config.DB_PATH
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        config.DB_PATH = self.tmp.name
        from database import get_conn
        _seed_db(get_conn())

    def tearDown(self):
        import config
        config.DB_PATH = self.orig_db_path
        os.unlink(self.tmp.name)

    def test_empty_graph(self):
        g = ConfusionGraph()
        self.assertEqual(g.edge_count(), 0)
        self.assertEqual(g.get_weight("A", "B"), 0.0)

    def test_upsert_edge_creates(self):
        g = ConfusionGraph()
        g.upsert_edge("Crohn", "UC", 0.82, 5, "response")
        self.assertEqual(g.edge_count(), 1)
        self.assertAlmostEqual(g.get_weight("Crohn", "UC"), 0.82)

    def test_upsert_edge_is_bidirectional(self):
        g = ConfusionGraph()
        g.upsert_edge("Crohn", "UC", 0.82, 5, "response")
        self.assertAlmostEqual(g.get_weight("Crohn", "UC"), 0.82)
        self.assertAlmostEqual(g.get_weight("UC", "Crohn"), 0.82)

    def test_upsert_edge_updates(self):
        g = ConfusionGraph()
        g.upsert_edge("A", "B", 0.5, 1, "response")
        g.upsert_edge("A", "B", 0.9, 5, "response")
        self.assertAlmostEqual(g.get_weight("A", "B"), 0.9)
        self.assertEqual(g.top_confusions_for("A")[0]["evidence_count"], 5)

    def test_upsert_self_edge_ignored(self):
        g = ConfusionGraph()
        g.upsert_edge("Self", "Self", 1.0, 1, "response")
        self.assertEqual(g.edge_count(), 0)

    def test_top_confusions_for(self):
        g = ConfusionGraph()
        g.upsert_edge("Crohn", "UC", 0.82, 5, "response")
        g.upsert_edge("Crohn", "Celiac", 0.45, 2, "response")
        g.upsert_edge("AS", "Crohn", 0.3, 1, "structural")
        top = g.top_confusions_for("Crohn")
        self.assertEqual(len(top), 3)
        # Should be sorted by weight descending
        self.assertEqual(top[0]["concept"], "UC")
        self.assertEqual(top[1]["concept"], "Celiac")
        self.assertEqual(top[2]["concept"], "AS")

    def test_global_top_confusions(self):
        g = ConfusionGraph()
        g.upsert_edge("A", "B", 0.9, 5, "response")
        g.upsert_edge("C", "D", 0.3, 1, "structural")
        top = g.global_top_confusions(n=1)
        self.assertEqual(len(top), 1)
        self.assertAlmostEqual(top[0]["weight"], 0.9)

    def test_save_and_load_from_db(self):
        g = ConfusionGraph()
        g.upsert_edge("Crohn", "UC", 0.82, 5, "response")
        g.save_to_db()

        g2 = ConfusionGraph()
        g2.load_from_db()
        self.assertEqual(g2.edge_count(), 1)
        self.assertAlmostEqual(g2.get_weight("Crohn", "UC"), 0.82)

    def test_normalize_prevents_duplicates_on_load(self):
        g = ConfusionGraph()
        g.upsert_edge("UC", "Crohn", 0.5, 1, "response")
        g.upsert_edge("Crohn", "UC", 0.9, 5, "response")
        self.assertEqual(g.edge_count(), 1)
        self.assertAlmostEqual(g.get_weight("Crohn", "UC"), 0.9)


class TestConfusionTracker(unittest.TestCase):

    def setUp(self):
        import config
        self.orig_db_path = config.DB_PATH
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        config.DB_PATH = self.tmp.name
        from database import get_conn
        _seed_db(get_conn())

    def tearDown(self):
        import config
        config.DB_PATH = self.orig_db_path
        os.unlink(self.tmp.name)

    def test_record_event_creates_edge(self):
        g = ConfusionGraph()
        t = ConfusionTracker(g)
        result = t.record_event(
            correct_tag="Ulcerative Colitis",
            chosen_tag="Crohn Disease",
            confidence_label="Certeza Absoluta",
            question_id="q1",
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["correct"], "Ulcerative Colitis")
        self.assertEqual(result["chosen"], "Crohn Disease")
        self.assertGreater(result["new_weight"], 0.0)
        self.assertGreater(result["evidence_count"], 0)

    def test_record_event_same_edge(self):
        g = ConfusionGraph()
        t = ConfusionTracker(g)
        t.record_event("A", "B", "Certeza Absoluta")
        w1 = g.get_weight("A", "B")
        t.record_event("A", "B", "Dúvida entre 2")
        w2 = g.get_weight("A", "B")
        self.assertGreater(w2, w1)

    def test_identical_concepts_ignored(self):
        g = ConfusionGraph()
        t = ConfusionTracker(g)
        result = t.record_event("Same", "Same")
        self.assertIsNone(result)

    def test_weight_delta_formula_confident_wrong(self):
        """Certeza Absoluta deberia ter delta maior que Chute Cego."""
        g = ConfusionGraph()
        t = ConfusionTracker(g)
        delta_confident = t._compute_weight_delta(0.0, 1, "Certeza Absoluta", 0)
        delta_guess = t._compute_weight_delta(0.0, 1, "Chute Cego", 0)
        self.assertGreater(delta_confident, delta_guess)

    def test_weight_delta_formula_frequency_growth(self):
        """More evidence = higher weight multiplier (log growth up to cap).
        First event: log2(2)/5 = 0.20
        Tenth event: log2(11)/5 = 0.69
        Each new event adds more evidence = pattern is more certain."""
        g = ConfusionGraph()
        t = ConfusionTracker(g)
        delta_first = t._compute_weight_delta(0.0, 1, "Dúvida entre 2", 0)
        delta_tenth = t._compute_weight_delta(0.5, 10, "Dúvida entre 2", 0)
        # More evidence = higher frequency_mult = larger delta
        self.assertGreater(delta_tenth, delta_first)

    def test_weight_delta_formula_recency_decay(self):
        """More days since last = smaller delta."""
        g = ConfusionGraph()
        t = ConfusionTracker(g)
        delta_recent = t._compute_weight_delta(0.0, 2, "Dúvida entre 2", 1)
        delta_old = t._compute_weight_delta(0.0, 2, "Dúvida entre 2", 90)
        self.assertGreater(delta_recent, delta_old)

    def test_student_confusions_after_event(self):
        g = ConfusionGraph()
        t = ConfusionTracker(g)
        t.record_event("AS", "HCM", "Certeza Absoluta", "q1")
        confusions = t.get_student_confusions("AS")
        self.assertEqual(len(confusions), 1)
        self.assertEqual(confusions[0]["concept"], "HCM")
        self.assertGreater(confusions[0]["weight"], 0.0)

    def test_global_confusions(self):
        g = ConfusionGraph()
        t = ConfusionTracker(g)
        t.record_event("AS", "HCM", "Certeza Absoluta")
        t.record_event("Crohn", "UC", "Dúvida entre 2")
        top = t.get_student_confusions(n=10)
        self.assertEqual(len(top), 2)

    def test_confusion_heatmap(self):
        g = ConfusionGraph()
        t = ConfusionTracker(g)
        t.record_event("A", "B", "Certeza Absoluta")
        t.record_event("C", "D", "Dúvida entre 2")
        heat = t.confusion_heatmap(threshold=0.01)
        self.assertGreaterEqual(len(heat), 2)

    def test_heatmap_filters_by_threshold(self):
        g = ConfusionGraph()
        t = ConfusionTracker(g)
        t.record_event("A", "B", "Chute Cego")
        weight = g.get_weight("A", "B")
        heat = t.confusion_heatmap(threshold=weight + 0.01)
        self.assertEqual(len(heat), 0)


class TestWeightFormulaExplicit(unittest.TestCase):
    """Explicit formula test: delta = BASE_DELTA × frequency_mult × recency_mult × confidence_mult."""

    def setUp(self):
        import config
        self.orig_db_path = config.DB_PATH
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        config.DB_PATH = self.tmp.name
        from database import get_conn
        _seed_db(get_conn())

    def tearDown(self):
        import config
        config.DB_PATH = self.orig_db_path
        os.unlink(self.tmp.name)

    def test_formula_first_event_confident(self):
        """First event, confident, today: delta = 0.15 * log2(2)/5 * e^0 * 1.0"""
        g = ConfusionGraph()
        t = ConfusionTracker(g)
        delta = t._compute_weight_delta(0.0, 1, "Certeza Absoluta", 0)
        expected = BASE_DELTA * (math.log2(2) / 5.0) * math.exp(0) * 1.0
        self.assertAlmostEqual(delta, expected, places=6)

    def test_formula_fifth_event_guess(self):
        """Fifth event, guess, 30 days: delta = 0.15 * log2(6)/5 * e^(-1) * 0.2"""
        g = ConfusionGraph()
        t = ConfusionTracker(g)
        delta = t._compute_weight_delta(0.3, 5, "Chute Cego", 30)
        expected = BASE_DELTA * (math.log2(6) / 5.0) * math.exp(-1) * 0.2
        self.assertAlmostEqual(delta, expected, places=6)

    def test_weight_clamped_at_one(self):
        """Repeated confident events should not exceed 1.0."""
        g = ConfusionGraph()
        t = ConfusionTracker(g)
        for i in range(20):
            t.record_event("A", "B", "Certeza Absoluta")
        self.assertAlmostEqual(g.get_weight("A", "B"), 1.0, places=4)


if __name__ == "__main__":
    unittest.main()
