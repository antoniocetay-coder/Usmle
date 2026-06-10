import unittest
import os
import json
import tempfile
from unittest.mock import patch


class TestEducationalObjectivesDB(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.tmp_db.close()
        cls.db_path = cls.tmp_db.name
        os.environ["USMLE_TEST_DB"] = cls.db_path

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.db_path)
        if "USMLE_TEST_DB" in os.environ:
            del os.environ["USMLE_TEST_DB"]

    def setUp(self):
        import config
        self.orig_db_path = config.DB_PATH
        config.DB_PATH = self.db_path

        from database import get_conn, init_db
        conn = get_conn()
        conn.execute("DROP TABLE IF EXISTS educational_objectives")
        conn.execute("DROP TABLE IF EXISTS srs_state")
        conn.execute("DROP TABLE IF EXISTS tag_stats")
        conn.execute("DROP TABLE IF EXISTS item_tags")
        conn.execute("DROP TABLE IF EXISTS questions")
        conn.commit()

        init_db()

        self.conn = get_conn()

    def tearDown(self):
        import config
        config.DB_PATH = self.orig_db_path

    # ─── EO CRUD ──────────────────────────────────────────────────────

    def test_save_and_get_eo(self):
        from database import save_educational_objective, get_eo_by_id
        eo_id = save_educational_objective(
            q_id="q1", eo_text="Recognize that diffuse ST elevation is pericarditis",
            source_explanation="PR depression is key", tags=["ECG", "Pericarditis"],
            sistema="Cardiovascular", dificuldade="Medium",
            cognitive_order="1st Order (Direct Recall / Diagnosis)"
        )
        self.assertEqual(eo_id, "q1")

        eo = get_eo_by_id(eo_id)
        self.assertIsNotNone(eo)
        self.assertEqual(eo["text"], "Recognize that diffuse ST elevation is pericarditis")
        self.assertEqual(eo["sistema"], "Cardiovascular")
        self.assertEqual(eo["source_explanation"], "PR depression is key")
        tags = json.loads(eo["tags_json"])
        self.assertIn("ECG", tags)
        self.assertIn("Pericarditis", tags)

    def test_save_eo_idempotent(self):
        from database import save_educational_objective
        eo_id = save_educational_objective(
            q_id="q_dup", eo_text="EO original",
            source_explanation="exp", tags=["tag1"],
            sistema="Cardio", dificuldade="Easy",
            cognitive_order="1st Order"
        )
        eo_id2 = save_educational_objective(
            q_id="q_dup", eo_text="EO original",
            source_explanation="exp", tags=["tag1"],
            sistema="Cardio", dificuldade="Easy",
            cognitive_order="1st Order"
        )
        self.assertEqual(eo_id, eo_id2)

    def test_get_eos_due(self):
        from database import save_educational_objective, get_eos_due
        save_educational_objective(
            q_id="q_due", eo_text="EO due for review",
            source_explanation="exp", tags=["tag1"],
            sistema="Cardio", dificuldade="Medium",
            cognitive_order="1st Order"
        )
        due = get_eos_due()
        ids = [e["id"] for e in due]
        self.assertIn("q_due", ids)

    def test_update_eo_srs_good(self):
        from database import save_educational_objective, get_eo_by_id, update_eo_srs
        eo_id = save_educational_objective(
            q_id="q_srs", eo_text="EO for SRS test",
            source_explanation="exp", tags=["tag1"],
            sistema="Cardio", dificuldade="Medium",
            cognitive_order="1st Order"
        )
        update_eo_srs(eo_id, "good")
        eo = get_eo_by_id(eo_id)
        self.assertIsNotNone(eo)
        self.assertGreater(eo["repetitions"], 0)
        self.assertIsNotNone(eo["due"])

    def test_update_eo_srs_again(self):
        from database import save_educational_objective, get_eo_by_id, update_eo_srs
        eo_id = save_educational_objective(
            q_id="q_srs2", eo_text="EO for again test",
            source_explanation="exp", tags=["tag1"],
            sistema="Cardio", dificuldade="Medium",
            cognitive_order="1st Order"
        )
        update_eo_srs(eo_id, "again")
        eo = get_eo_by_id(eo_id)
        self.assertGreater(eo["lapses"], 0)

    def test_search_eos_by_text(self):
        from database import save_educational_objective, search_eos
        save_educational_objective(
            q_id="q_search1", eo_text="Aortic stenosis pathophysiology",
            source_explanation="key: narrow pulse pressure", tags=["Cardio"],
            sistema="Cardiovascular", dificuldade="Hard",
            cognitive_order="2nd Order"
        )
        save_educational_objective(
            q_id="q_search2", eo_text="HCM vs AS differentiation",
            source_explanation="key: LVOT obstruction", tags=["Cardio"],
            sistema="Cardiovascular", dificuldade="Hard",
            cognitive_order="2nd Order"
        )
        results = search_eos(query="aortic")
        texts = [r["text"] for r in results]
        self.assertIn("Aortic stenosis pathophysiology", texts)

    def test_search_eos_by_system(self):
        from database import save_educational_objective, search_eos
        save_educational_objective(
            q_id="q_sys1", eo_text="Renal EO",
            source_explanation="exp", tags=["Renal"],
            sistema="Renal", dificuldade="Medium",
            cognitive_order="1st Order"
        )
        results = search_eos(sistema="Renal")
        self.assertTrue(any("Renal EO" in r["text"] for r in results))
        results_not = search_eos(sistema="Cardiovascular")
        self.assertFalse(any("Renal EO" in r["text"] for r in results_not))

    def test_get_eo_count_by_system(self):
        from database import save_educational_objective, get_eo_count_by_system
        save_educational_objective(
            q_id="q_cnt1", eo_text="Cardio EO",
            source_explanation="exp", tags=["Cardio"],
            sistema="Cardiovascular", dificuldade="Easy",
            cognitive_order="1st Order"
        )
        save_educational_objective(
            q_id="q_cnt2", eo_text="Another Cardio EO",
            source_explanation="exp", tags=["Cardio"],
            sistema="Cardiovascular", dificuldade="Easy",
            cognitive_order="1st Order"
        )
        counts = get_eo_count_by_system()
        self.assertEqual(counts.get("Cardiovascular"), 2)

    # ─── Missed Tag SRS ───────────────────────────────────────────────

    def test_mark_and_get_missed_tag(self):
        from database import mark_tag_for_review, get_missed_tags_due
        mark_tag_for_review("Aortic Stenosis")
        due = get_missed_tags_due()
        tags = [m["object_id"] for m in due]
        self.assertIn("Aortic Stenosis", tags)

    def test_mark_missed_tag_idempotent(self):
        from database import mark_tag_for_review, get_missed_tags_due
        mark_tag_for_review("HCM")
        mark_tag_for_review("HCM")
        due = get_missed_tags_due()
        hcm = [m for m in due if m["object_id"] == "HCM"]
        self.assertEqual(len(hcm), 1)

    def test_update_missed_tag_srs(self):
        from database import mark_tag_for_review, get_missed_tags_due, update_missed_tag_srs
        mark_tag_for_review("Pericarditis")
        update_missed_tag_srs("Pericarditis")
        due = get_missed_tags_due()
        p = [m for m in due if m["object_id"] == "Pericarditis"]
        self.assertEqual(len(p), 0)

    # ─── salvar_questao → auto-EO extraction ──────────────────────────

    def test_salvar_questao_creates_eo(self):
        from database import salvar_questao, get_eo_by_id
        questao = {
            "vignette": "A 45-year-old man presents with chest pain...",
            "options": ["A) MI", "B) Pericarditis", "C) PE", "D) Pneumonia", "E) Anxiety"],
            "correct": "B",
            "explanations": {"A": "A", "B": "PR depression is key", "C": "C", "D": "D", "E": "E"},
            "educational_objective": "Recognize diffuse ST elevation with PR depression as pericarditis",
            "content_tags": ["Pericarditis", "ECG"],
            "distractor_tags": {"A": "MI", "B": "Pericarditis", "C": "PE", "D": "Pneumonia", "E": "Anxiety"},
        }
        q_id = salvar_questao("Cardiovascular", "Medium", questao, False,
                              ["Pericarditis", "ECG"], status="pending",
                              cognitive_order="1st Order (Direct Recall / Diagnosis)")

        eo = get_eo_by_id(q_id)
        self.assertIsNotNone(eo)
        self.assertIn("pericarditis", eo["text"].lower())
        self.assertIn("PR depression", eo["source_explanation"])

    def test_salvar_questao_no_eo_skips(self):
        from database import salvar_questao, get_eo_by_id, search_eos
        questao_no_eo = {
            "vignette": "A 30-year-old woman...",
            "options": ["A) X", "B) Y", "C) Z", "D) W", "E) V"],
            "correct": "A",
            "explanations": {"A": "exp", "B": "exp", "C": "exp", "D": "exp", "E": "exp"},
            "educational_objective": "",
            "content_tags": ["Tag1"],
            "distractor_tags": {"A": "Tag1", "B": "Tag2", "C": "Tag3", "D": "Tag4", "E": "Tag5"},
        }
        q_id = salvar_questao("General", "Easy", questao_no_eo, True, ["Tag1"])
        eo = get_eo_by_id(q_id)
        self.assertIsNone(eo)

    # ─── salvar_resultado_pendente → missed_tag trigger ───────────────

    def test_salvar_resultado_errado_baixo_mastery_marca_missed(self):
        from database import salvar_questao, get_missed_tags_due
        from session_state import salvar_resultado_pendente

        questao = {
            "vignette": "test", "options": ["A) a", "B) b", "C) c", "D) d", "E) e"],
            "correct": "A",
            "explanations": {"A": "a", "B": "b", "C": "c", "D": "d", "E": "e"},
            "educational_objective": "test eo",
            "content_tags": ["WeakTag"],
            "distractor_tags": {"A": "WeakTag", "B": "Other", "C": "X", "D": "Y", "E": "Z"},
        }
        q_id = salvar_questao("General", "Medium", questao, False,
                              ["WeakTag"], status="pending",
                              cognitive_order="1st Order")

        self.conn.execute("INSERT OR REPLACE INTO tag_stats (tag, correct, total, mastery_prob) VALUES (?, ?, ?, ?)",
                          ("WeakTag", 0, 1, 0.15))
        self.conn.commit()

        salvar_resultado_pendente(q_id, "General", False, ["WeakTag"], 30, "Certeza Absoluta",
                                  dificuldade="Medium")

        due = get_missed_tags_due()
        tags = [m["object_id"] for m in due]
        self.assertIn("WeakTag", tags)

    def test_salvar_resultado_certo_nao_marca_missed(self):
        from database import salvar_questao, get_missed_tags_due
        from session_state import salvar_resultado_pendente

        questao = {
            "vignette": "test", "options": ["A) a", "B) b", "C) c", "D) d", "E) e"],
            "correct": "A",
            "explanations": {"A": "a", "B": "b", "C": "c", "D": "d", "E": "e"},
            "educational_objective": "test eo",
            "content_tags": ["GoodTag"],
            "distractor_tags": {"A": "GoodTag", "B": "Other", "C": "X", "D": "Y", "E": "Z"},
        }
        q_id = salvar_questao("General", "Medium", questao, False,
                              ["GoodTag"], status="pending",
                              cognitive_order="1st Order")

        self.conn.execute("INSERT OR REPLACE INTO tag_stats (tag, correct, total, mastery_prob) VALUES (?, ?, ?, ?)",
                          ("GoodTag", 0, 1, 0.15))
        self.conn.commit()

        salvar_resultado_pendente(q_id, "General", True, ["GoodTag"], 30, "Certeza Absoluta",
                                  dificuldade="Medium")

        due = get_missed_tags_due()
        tags = [m["object_id"] for m in due]
        self.assertNotIn("GoodTag", tags)


if __name__ == "__main__":
    unittest.main()
