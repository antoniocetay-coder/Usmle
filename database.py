import sqlite3
import json
import uuid
import streamlit as st
from enum import Enum
from datetime import datetime, timezone, timedelta
from config import *

class ItemType(Enum):
    FLASHCARD = "flashcard"
    QUESTION  = "question"
    EO        = "eo"

@st.cache_resource
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_db():
    conn = get_conn()

    conn.execute("CREATE TABLE IF NOT EXISTS erros_por_sistema (sistema TEXT PRIMARY KEY, total INTEGER DEFAULT 0)")
    conn.execute("CREATE TABLE IF NOT EXISTS tag_stats (tag TEXT PRIMARY KEY, correct INTEGER DEFAULT 0, total INTEGER DEFAULT 0)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS flashcards (
            id TEXT PRIMARY KEY, front TEXT NOT NULL, back TEXT NOT NULL, sistema TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS srs_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            object_id TEXT NOT NULL, object_type TEXT NOT NULL,
            stability REAL DEFAULT 0.0, difficulty REAL DEFAULT 0.0,
            due TEXT, repetitions INTEGER DEFAULT 0, lapses INTEGER DEFAULT 0, last_review TEXT,
            UNIQUE(object_id, object_type)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id TEXT PRIMARY KEY, sistema TEXT, dificuldade TEXT,
            question_json TEXT, correct_answer TEXT, answered_correctly INTEGER, created_at TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS item_tags (
            object_id TEXT NOT NULL, object_type TEXT NOT NULL, tag TEXT NOT NULL, UNIQUE(object_id, object_type, tag)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS confusion_pairs (
            tag_correct TEXT NOT NULL,
            tag_confused TEXT NOT NULL,
            count INTEGER DEFAULT 1,
            last_seen TEXT NOT NULL,
            PRIMARY KEY (tag_correct, tag_confused)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS educational_objectives (
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            sistema TEXT,
            dificuldade TEXT,
            cognitive_order TEXT,
            tags_json TEXT,
            source_question_id TEXT,
            source_explanation TEXT,
            created_at TEXT
        )
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_srs_state_obj ON srs_state(object_id, object_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_srs_state_due ON srs_state(due)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_item_tags_tag ON item_tags(tag)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_item_tags_obj ON item_tags(object_id, object_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_confusion_pairs ON confusion_pairs(tag_correct)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_eo_sistema ON educational_objectives(sistema)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_eo_source ON educational_objectives(source_question_id)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tag_validation (
            tag TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'unproven',
            score REAL,
            total_questions INTEGER DEFAULT 20,
            attempted_at TEXT,
            passed_at TEXT,
            next_attempt_at TEXT,
            proof_id TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS proof_questions (
            id TEXT PRIMARY KEY,
            proof_id TEXT NOT NULL,
            tag TEXT NOT NULL,
            question_json TEXT NOT NULL,
            user_answer TEXT,
            correct_answer TEXT,
            is_correct INTEGER,
            difficulty TEXT,
            cognitive_order TEXT,
            answered_at TEXT
        )
    """)

    # Atualização dinâmica do esquema (Metacognição, Tempo e BKT)
    try:
        conn.execute("ALTER TABLE questions ADD COLUMN time_taken_seconds INTEGER")
        conn.execute("ALTER TABLE questions ADD COLUMN confidence_level TEXT")
    except sqlite3.OperationalError:
        pass # As colunas já existem

    try:
        conn.execute("ALTER TABLE tag_stats ADD COLUMN mastery_prob REAL DEFAULT 0.15")
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("ALTER TABLE tag_stats ADD COLUMN max_difficulty TEXT DEFAULT 'Easy'")
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("ALTER TABLE tag_stats ADD COLUMN max_cognitive_order TEXT DEFAULT '1st Order (Direct Recall / Diagnosis)'")
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("ALTER TABLE questions ADD COLUMN cognitive_order TEXT")
    except sqlite3.OperationalError:
        pass

    for s in SISTEMAS_DISPONIVEIS:
        conn.execute("INSERT OR IGNORE INTO erros_por_sistema (sistema, total) VALUES (?, 0)", (s,))

    conn.commit()


def salvar_questao(sistema, dificuldade, questao, acertou, tags, status="answered", cognitive_order=None):
    conn = get_conn()
    q_id = str(uuid.uuid4())
    ans_val = None if status == "pending" else int(acertou)

    conn.execute("""
        INSERT INTO questions (id, sistema, dificuldade, question_json, correct_answer, answered_correctly, created_at, cognitive_order) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        q_id,
        sistema,
        dificuldade,
        json.dumps(questao, ensure_ascii=False),
        questao["correct"],
        ans_val,
        datetime.now(timezone.utc).isoformat(),
        cognitive_order
    ))

    for tag in tags:
        conn.execute("INSERT INTO item_tags (object_id, object_type, tag) VALUES (?, ?, ?)", (q_id, ItemType.QUESTION.value, tag))

    eo_text = questao.get("educational_objective", "").strip()
    if eo_text:
        correct_opt = questao.get("correct", "A")
        source_explanation = questao.get("explanations", {}).get(correct_opt, "")
        conn.execute("""
            INSERT OR IGNORE INTO educational_objectives
                (id, text, sistema, dificuldade, cognitive_order, tags_json, source_question_id, source_explanation, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            q_id, eo_text, sistema, dificuldade, cognitive_order,
            json.dumps(tags, ensure_ascii=False), q_id, source_explanation,
            datetime.now(timezone.utc).isoformat()
        ))
        conn.execute("""
            INSERT OR IGNORE INTO srs_state (object_id, object_type, due)
            VALUES (?, 'eo', ?)
        """, (q_id, datetime.now(timezone.utc).strftime("%Y-%m-%d")))

    conn.commit()
    return q_id


def marcar_questao_respondida(q_id, acertou, time_taken=None, confidence=None):
    conn = get_conn()
    conn.execute("""
        UPDATE questions 
        SET answered_correctly = ?, time_taken_seconds = ?, confidence_level = ?
        WHERE id = ?
    """, (int(acertou), time_taken, confidence, q_id))
    conn.commit()


def get_questions():
    conn = get_conn()
    rows = conn.execute("""
        SELECT q.*, GROUP_CONCAT(t.tag, '|') as tag_list
        FROM questions q
        LEFT JOIN item_tags t ON q.id = t.object_id AND t.object_type = 'question'
        WHERE q.answered_correctly IS NOT NULL
        GROUP BY q.id
        ORDER BY q.created_at DESC
    """).fetchall()
    return [dict(r) for r in rows]


def get_pending_questions():
    conn = get_conn()
    rows = conn.execute("""
        SELECT q.*, GROUP_CONCAT(t.tag, '|') as tag_list
        FROM questions q
        LEFT JOIN item_tags t ON q.id = t.object_id AND t.object_type = 'question'
        WHERE q.answered_correctly IS NULL
        GROUP BY q.id
        ORDER BY q.created_at ASC
    """).fetchall()
    return [dict(r) for r in rows]


def salvar_flashcard_db(front, back, sistema, tags):
    conn = get_conn()
    f_id = str(uuid.uuid4())
    conn.execute("INSERT INTO flashcards (id, front, back, sistema) VALUES (?, ?, ?, ?)", (f_id, front, back, sistema))

    for tag in tags:
        conn.execute("INSERT INTO item_tags (object_id, object_type, tag) VALUES (?, ?, ?)", (f_id, ItemType.FLASHCARD.value, tag))
    conn.commit()


def get_cards_hoje():
    conn = get_conn()
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    rows = conn.execute("""
        SELECT f.*, 
               COALESCE(s.stability, 0) as stability, 
               COALESCE(s.difficulty, 0) as difficulty, 
               s.due, 
               COALESCE(s.repetitions, 0) as repetitions, 
               COALESCE(s.lapses, 0) as lapses, 
               s.last_review
        FROM flashcards f
        LEFT JOIN srs_state s ON f.id = s.object_id AND s.object_type = 'flashcard'
        WHERE s.due IS NULL OR s.due <= ?
    """, (hoje,)).fetchall()
    return [dict(r) for r in rows]


def get_flashcards_by_tags(tags):
    if not tags:
        return []
    conn = get_conn()
    placeholders = ",".join(["?"] * len(tags))
    query = f"""
        SELECT DISTINCT f.front, f.back
        FROM flashcards f
        JOIN item_tags t ON f.id = t.object_id AND t.object_type = 'flashcard'
        WHERE t.tag IN ({placeholders})
    """
    rows = conn.execute(query, tags).fetchall()
    return [{"front": r["front"], "back": r["back"]} for r in rows]


def get_flashcards_full_by_tags(tags):
    if not tags:
        return []
    conn = get_conn()
    placeholders = ",".join(["?"] * len(tags))
    query = f"""
        SELECT DISTINCT f.*,
               COALESCE(s.stability, 0) as stability,
               COALESCE(s.difficulty, 0) as difficulty,
               s.due,
               COALESCE(s.repetitions, 0) as repetitions,
               COALESCE(s.lapses, 0) as lapses,
               s.last_review
        FROM flashcards f
        JOIN item_tags t ON f.id = t.object_id AND t.object_type = 'flashcard'
        LEFT JOIN srs_state s ON f.id = s.object_id AND s.object_type = 'flashcard'
        WHERE t.tag IN ({placeholders})
    """
    rows = conn.execute(query, tags).fetchall()
    return [dict(r) for r in rows]


def get_pending_questions_by_tags(tags):
    if not tags:
        return []
    conn = get_conn()
    placeholders = ",".join(["?"] * len(tags))
    query = f"""
        SELECT q.*, GROUP_CONCAT(t.tag, '|') as tag_list
        FROM questions q
        JOIN item_tags it ON q.id = it.object_id AND it.object_type = 'question'
        LEFT JOIN item_tags t ON q.id = t.object_id AND t.object_type = 'question'
        WHERE q.answered_correctly IS NULL
          AND it.tag IN ({placeholders})
        GROUP BY q.id
        ORDER BY q.created_at ASC
    """
    rows = conn.execute(query, tags).fetchall()
    return [dict(r) for r in rows]


def registrar_confusao(tag_correct, tag_confused):
    conn = get_conn()
    agora = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO confusion_pairs (tag_correct, tag_confused, count, last_seen)
        VALUES (?, ?, 1, ?)
        ON CONFLICT(tag_correct, tag_confused)
        DO UPDATE SET count = count + 1, last_seen = excluded.last_seen
    """, (tag_correct, tag_confused, agora))
    conn.commit()


def get_tags_em_cooldown(horas=48):
    conn = get_conn()
    corte_tempo = (datetime.now(timezone.utc) - timedelta(hours=horas)).isoformat()
    rows = conn.execute("""
        SELECT DISTINCT t.tag
        FROM item_tags t
        JOIN questions q ON t.object_id = q.id
        WHERE q.created_at >= ?
    """, (corte_tempo,)).fetchall()
    return [r["tag"] for r in rows]


def registrar_cooldown_tags(tags):
    """
    O cooldown já é controlado implicitamente via created_at das questões
    em get_tags_em_cooldown(). Esta função existe por compatibilidade de interface
    e pode ser usada futuramente para um registro explícito de cooldown, se necessário.
    """
    pass


def get_top_confounders(tag_correct, limit=3):
    conn = get_conn()
    rows = conn.execute("""
        SELECT tag_confused 
        FROM confusion_pairs 
        WHERE tag_correct = ? 
        ORDER BY count DESC 
        LIMIT ?
    """, (tag_correct, limit)).fetchall()
    return [r["tag_confused"] for r in rows]


def get_system_stats():
    conn = get_conn()
    rows = conn.execute("""
        SELECT sistema,
               SUM(CASE WHEN answered_correctly = 1 THEN 1 ELSE 0 END) as acertos,
               COUNT(*) as total
        FROM questions
        WHERE answered_correctly IS NOT NULL
        GROUP BY sistema
    """).fetchall()
    return [dict(r) for r in rows]


def get_metacognition_stats():
    conn = get_conn()
    rows = conn.execute("""
        SELECT confidence_level, answered_correctly, COUNT(*) as qtd
        FROM questions
        WHERE confidence_level IS NOT NULL
        GROUP BY confidence_level, answered_correctly
    """).fetchall()
    return [dict(r) for r in rows]


def get_time_stats():
    conn = get_conn()
    rows = conn.execute("""
        SELECT sistema, answered_correctly, AVG(time_taken_seconds) as avg_time
        FROM questions
        WHERE time_taken_seconds IS NOT NULL
        GROUP BY sistema, answered_correctly
    """).fetchall()
    return [dict(r) for r in rows]


def get_fsrs_forecast():
    conn = get_conn()
    rows = conn.execute("""
        SELECT due, COUNT(*) as qtd
        FROM srs_state
        WHERE object_type = 'flashcard' AND due IS NOT NULL
        GROUP BY due
        ORDER BY due ASC
        LIMIT 14
    """).fetchall()
    return [dict(r) for r in rows]


def get_global_confusions(limit=10):
    conn = get_conn()
    rows = conn.execute("""
        SELECT tag_correct, tag_confused, count
        FROM confusion_pairs
        ORDER BY count DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_validation_status(tag):
    conn = get_conn()
    row = conn.execute("SELECT * FROM tag_validation WHERE tag = ?", (tag,)).fetchone()
    if row:
        return dict(row)
    return {"tag": tag, "status": "unproven", "score": None, "proof_id": None,
            "passed_at": None, "next_attempt_at": None}


def set_validation_started(tag, proof_id):
    conn = get_conn()
    agora = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO tag_validation (tag, status, attempted_at, proof_id)
        VALUES (?, 'pending', ?, ?)
        ON CONFLICT(tag) DO UPDATE SET
            status = 'pending', attempted_at = excluded.attempted_at, proof_id = excluded.proof_id
    """, (tag, agora, proof_id))
    conn.commit()


def set_validation_result(tag, proof_id, score, total_q, passed):
    conn = get_conn()
    agora = datetime.now(timezone.utc).isoformat()
    status = "passed" if passed else "failed"
    passed_at = agora if passed else None
    next_attempt = None
    if not passed:
        next_attempt = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

    conn.execute("""
        UPDATE tag_validation
        SET status = ?, score = ?, total_questions = ?, passed_at = ?,
            next_attempt_at = ?
        WHERE tag = ?
    """, (status, score, total_q, passed_at, next_attempt, tag))
    conn.commit()


def save_proof_answer(proof_id, tag, question_json, difficulty, cognitive_order):
    conn = get_conn()
    a_id = str(uuid.uuid4())
    q_data = json.loads(question_json)
    conn.execute("""
        INSERT INTO proof_questions (id, proof_id, tag, question_json, correct_answer, difficulty, cognitive_order)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (a_id, proof_id, tag, question_json, q_data["correct"], difficulty, cognitive_order))
    conn.commit()
    return a_id


def update_proof_answer(q_id, user_answer, is_correct):
    conn = get_conn()
    agora = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        UPDATE proof_questions
        SET user_answer = ?, is_correct = ?, answered_at = ?
        WHERE id = ?
    """, (user_answer, int(is_correct), agora, q_id))
    conn.commit()


def get_tags_eligiveis_prova(stats):
    tags = []
    agora = datetime.now(timezone.utc).isoformat()
    for tag, s in stats.items():
        rk = s.get("real_knowledge", 0)
        if rk < 0.70:
            continue
        valid = get_validation_status(tag)
        if valid["status"] == "passed":
            continue
        if valid["status"] == "failed" and valid.get("next_attempt_at") and valid["next_attempt_at"] > agora:
            continue
        tags.append({"tag": tag, "rk": rk, "status": valid["status"]})
    return sorted(tags, key=lambda x: x["rk"], reverse=True)


def get_tags_proven():
    conn = get_conn()
    rows = conn.execute("SELECT tag FROM tag_validation WHERE status = 'passed'").fetchall()
    return {r["tag"] for r in rows}


def save_educational_objective(q_id, eo_text, source_explanation, tags, sistema, dificuldade, cognitive_order):
    conn = get_conn()
    conn.execute("""
        INSERT OR IGNORE INTO educational_objectives
            (id, text, sistema, dificuldade, cognitive_order, tags_json, source_question_id, source_explanation, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        q_id, eo_text, sistema, dificuldade, cognitive_order,
        json.dumps(tags, ensure_ascii=False), q_id, source_explanation,
        datetime.now(timezone.utc).isoformat()
    ))
    conn.execute("""
        INSERT OR IGNORE INTO srs_state (object_id, object_type, due)
        VALUES (?, 'eo', ?)
    """, (q_id, datetime.now(timezone.utc).strftime("%Y-%m-%d")))
    conn.commit()
    return q_id


def get_eo_by_id(eo_id):
    conn = get_conn()
    row = conn.execute("""
        SELECT eo.*,
               COALESCE(s.stability, 0) as stability,
               COALESCE(s.difficulty, 0) as difficulty,
               s.due,
               COALESCE(s.repetitions, 0) as repetitions,
               COALESCE(s.lapses, 0) as lapses,
               s.last_review
        FROM educational_objectives eo
        LEFT JOIN srs_state s ON eo.id = s.object_id AND s.object_type = 'eo'
        WHERE eo.id = ?
    """, (eo_id,)).fetchone()
    return dict(row) if row else None


def get_eos_due():
    conn = get_conn()
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = conn.execute("""
        SELECT eo.*,
               COALESCE(s.stability, 0) as stability,
               COALESCE(s.difficulty, 0) as difficulty,
               s.due,
               COALESCE(s.repetitions, 0) as repetitions,
               COALESCE(s.lapses, 0) as lapses,
               s.last_review
        FROM educational_objectives eo
        LEFT JOIN srs_state s ON eo.id = s.object_id AND s.object_type = 'eo'
        WHERE s.due IS NULL OR s.due <= ?
        ORDER BY s.due ASC
    """, (hoje,)).fetchall()
    return [dict(r) for r in rows]


def update_eo_srs(eo_id, rating):
    conn = get_conn()
    row = conn.execute("""
        SELECT stability, difficulty, repetitions, lapses, due
        FROM srs_state WHERE object_id = ? AND object_type = 'eo'
    """, (eo_id,)).fetchone()

    if not row:
        return

    reps = row["repetitions"] or 0
    lapses = row["lapses"] or 0
    stability = row["stability"] or 0.0
    diff = row["difficulty"] or 0.0

    if rating == "again":
        lapses += 1
        reps = 0
        stability = max(0.1, stability * 0.4)
        interval_days = 1
    elif rating == "hard":
        reps += 1
        stability = max(0.1, stability * 1.2)
        interval_days = max(1, int(round(stability)))
    elif rating == "good":
        reps += 1
        stability = max(0.5, stability * 1.8 + 0.5 * (3 - diff))
        interval_days = max(1, int(round(stability)))
    else:
        return

    due = (datetime.now(timezone.utc) + timedelta(days=interval_days)).strftime("%Y-%m-%d")
    now_iso = datetime.now(timezone.utc).isoformat()

    conn.execute("""
        UPDATE srs_state
        SET stability = ?, difficulty = ?, due = ?,
            repetitions = ?, lapses = ?, last_review = ?
        WHERE object_id = ? AND object_type = 'eo'
    """, (stability, diff, due, reps, lapses, now_iso, eo_id))
    conn.commit()


def search_eos(query="", sistema=None, limit=50):
    conn = get_conn()
    conditions = []
    params = []
    if query:
        conditions.append("eo.text LIKE ?")
        params.append(f"%{query}%")
    if sistema:
        conditions.append("eo.sistema = ?")
        params.append(sistema)
    where = " AND ".join(conditions) if conditions else "1"
    sql = f"""
        SELECT eo.*,
               COALESCE(s.stability, 0) as stability,
               COALESCE(s.difficulty, 0) as difficulty,
               s.due,
               COALESCE(s.repetitions, 0) as repetitions,
               COALESCE(s.lapses, 0) as lapses,
               s.last_review
        FROM educational_objectives eo
        LEFT JOIN srs_state s ON eo.id = s.object_id AND s.object_type = 'eo'
        WHERE {where}
        ORDER BY eo.created_at DESC
        LIMIT ?
    """
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def mark_tag_for_review(tag):
    conn = get_conn()
    conn.execute("""
        INSERT INTO srs_state (object_id, object_type, due)
        VALUES (?, 'missed_tag', ?)
        ON CONFLICT(object_id, object_type)
        DO UPDATE SET due = excluded.due
    """, (tag, datetime.now(timezone.utc).strftime("%Y-%m-%d")))
    conn.commit()


def get_missed_tags_due():
    conn = get_conn()
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = conn.execute("""
        SELECT object_id, due, repetitions, lapses, last_review
        FROM srs_state
        WHERE object_type = 'missed_tag'
          AND (due IS NULL OR due <= ?)
        ORDER BY due ASC
        LIMIT 5
    """, (hoje,)).fetchall()
    return [dict(r) for r in rows]


def update_missed_tag_srs(tag):
    conn = get_conn()
    row = conn.execute("""
        SELECT stability, difficulty, repetitions, lapses
        FROM srs_state WHERE object_id = ? AND object_type = 'missed_tag'
    """, (tag,)).fetchone()
    if not row:
        return
    reps = (row["repetitions"] or 0) + 1
    lapses = row["lapses"] or 0
    stability = max(1.0, (row["stability"] or 0.0) * 2.0)
    diff = row["difficulty"] or 0.0
    interval_days = max(1, int(round(stability)))
    due = (datetime.now(timezone.utc) + timedelta(days=interval_days)).strftime("%Y-%m-%d")
    conn.execute("""
        UPDATE srs_state
        SET stability = ?, difficulty = ?, due = ?,
            repetitions = ?, last_review = ?
        WHERE object_id = ? AND object_type = 'missed_tag'
    """, (stability, diff, due, reps, datetime.now(timezone.utc).isoformat(), tag))
    conn.commit()


def get_eo_count_by_system():
    conn = get_conn()
    rows = conn.execute("""
        SELECT sistema, COUNT(*) as total
        FROM educational_objectives
        GROUP BY sistema
        ORDER BY total DESC
    """).fetchall()
    return {r["sistema"]: r["total"] for r in rows}
