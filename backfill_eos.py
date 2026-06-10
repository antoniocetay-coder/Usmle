"""
One-time script: extract Educational Objectives from all existing questions
that don't have an EO entry yet.
"""
import json
from database import get_conn, init_db, save_educational_objective


def run():
    init_db()
    conn = get_conn()

    questions = conn.execute("""
        SELECT q.id, q.question_json, q.sistema, q.dificuldade, q.cognitive_order,
               GROUP_CONCAT(t.tag, '|') as tag_list
        FROM questions q
        LEFT JOIN item_tags t ON q.id = t.object_id AND t.object_type = 'question'
        WHERE q.answered_correctly IS NOT NULL
        GROUP BY q.id
        ORDER BY q.created_at ASC
    """).fetchall()

    inserted = 0
    skipped = 0

    for q in questions:
        existing = conn.execute(
            "SELECT id FROM educational_objectives WHERE source_question_id = ?",
            (q["id"],)
        ).fetchone()
        if existing:
            skipped += 1
            continue

        try:
            q_data = json.loads(q["question_json"])
        except (json.JSONDecodeError, TypeError):
            skipped += 1
            continue

        eo_text = q_data.get("educational_objective", "").strip()
        if not eo_text:
            skipped += 1
            continue

        correct_opt = q_data.get("correct", "A")
        source_explanation = q_data.get("explanations", {}).get(correct_opt, "")
        tags = q["tag_list"].split("|") if q["tag_list"] else []

        save_educational_objective(
            q_id=q["id"], eo_text=eo_text,
            source_explanation=source_explanation, tags=tags,
            sistema=q["sistema"], dificuldade=q["dificuldade"],
            cognitive_order=q["cognitive_order"]
        )
        inserted += 1

    total = len(questions)
    print(f"Total questions: {total}")
    print(f"Inserted EOs:    {inserted}")
    print(f"Skipped:         {skipped}")


if __name__ == "__main__":
    run()
