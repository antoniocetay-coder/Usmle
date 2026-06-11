import streamlit as st
import json
import datetime
import time
from config import *
from database import *
from mastery import update_bkt, DIFFICULTY_RANK, COGNITIVE_RANK, RANK_TO_DIFFICULTY, RANK_TO_COGNITIVE


def increment_db_version():
    st.session_state["db_version"] = st.session_state.get("db_version", 0) + 1


def startup():
    init_db()


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def hoje_str():
    return now_utc().strftime("%Y-%m-%d")


DEFAULTS = {
    "modo_estudo": None,
    "fila_estudo": [],
    "idx_atual": 0,
    "resposta_submetida": False,
    "letra_escolhida": None,
    "acertou_ultima": False,
    "confianca_escolhida": None,
    "tempo_inicio_questao": None,
    "tempo_gasto": None,
    "revelar_flashcard": False,
    "flashcards_rascunho": [],
    "flashcards_salvos": False,
    "checagem_feita": False,
    "resposta_tutor_atual": None,
    "prova_ativa": False,
    "prova_tag": None,
    "prova_proof_id": None,
    "prova_questoes": [],
    "prova_answers": [],
    "prova_idx": 0,
    "prova_concluida": False,
    "db_version": 0,
}


def init_session_state():
    for k, v in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v


def sair_do_modo_estudo():
    for k in DEFAULTS.keys():
        del st.session_state[k]
    st.session_state["flashcards_rascunho"] = []
    st.session_state["flashcards_salvos"] = False
    st.session_state["checagem_feita"] = False
    st.session_state["resposta_tutor_atual"] = None
    st.rerun()


def proximo_item_fila():
    st.session_state["idx_atual"] += 1
    st.session_state["resposta_submetida"] = False
    st.session_state["letra_escolhida"] = None
    st.session_state["revelar_flashcard"] = False
    st.session_state["tempo_inicio_questao"] = None
    st.session_state["confianca_escolhida"] = None
    st.session_state["tempo_gasto"] = None
    st.session_state["resposta_tutor_atual"] = None

    st.session_state["flashcards_rascunho"] = []
    st.session_state["flashcards_salvos"] = False
    st.session_state["checagem_feita"] = False
    st.rerun()


def salvar_resultado_pendente(q_id, sistema, is_correct, tags, time_taken, confidence,
                              dificuldade="Medium", cognitive_order="1st Order (Direct Recall / Diagnosis)"):
    marcar_questao_respondida(q_id, is_correct, time_taken, confidence)
    conn = get_conn()

    for tag in tags:
        row = conn.execute("""
            SELECT correct, total, mastery_prob, max_difficulty, max_cognitive_order
            FROM tag_stats WHERE tag = ?
        """, (tag,)).fetchone()

        if row:
            curr_prob = row["mastery_prob"] if row["mastery_prob"] is not None else 0.15
            corrects = row["correct"] + int(is_correct)
            totals = row["total"] + 1
            old_max_diff = row["max_difficulty"] or "Easy"
            old_max_cog = row["max_cognitive_order"] or "1st Order (Direct Recall / Diagnosis)"
        else:
            curr_prob = 0.15
            corrects = int(is_correct)
            totals = 1
            old_max_diff = "Easy"
            old_max_cog = "1st Order (Direct Recall / Diagnosis)"

        new_prob = update_bkt(curr_prob, is_correct, confidence, dificuldade, totals)

        cur_diff_rank = DIFFICULTY_RANK.get(dificuldade, 0)
        old_diff_rank = DIFFICULTY_RANK.get(old_max_diff, 0)
        new_diff_rank = max(cur_diff_rank, old_diff_rank)

        cur_cog_rank = COGNITIVE_RANK.get(cognitive_order, 0)
        old_cog_rank = COGNITIVE_RANK.get(old_max_cog, 0)
        new_cog_rank = max(cur_cog_rank, old_cog_rank)

        conn.execute("""
            INSERT INTO tag_stats (tag, correct, total, mastery_prob, max_difficulty, max_cognitive_order)
            VALUES (?, ?, 1, ?, ?, ?)
            ON CONFLICT(tag) DO UPDATE SET
                correct = ?,
                total = ?,
                mastery_prob = ?,
                max_difficulty = ?,
                max_cognitive_order = ?
        """, (tag, corrects, new_prob, RANK_TO_DIFFICULTY[new_diff_rank], RANK_TO_COGNITIVE[new_cog_rank],
              corrects, totals, new_prob, RANK_TO_DIFFICULTY[new_diff_rank], RANK_TO_COGNITIVE[new_cog_rank]))

        if not is_correct and new_prob < 0.40:
            conn.execute("""
                INSERT INTO srs_state (object_id, object_type, due)
                VALUES (?, 'missed_tag', ?)
                ON CONFLICT(object_id, object_type)
                DO UPDATE SET due = excluded.due
            """, (tag, datetime.now(timezone.utc).strftime("%Y-%m-%d")))

    if not is_correct:
        conn.execute("UPDATE erros_por_sistema SET total = total + 1 WHERE sistema = ?", (sistema,))

    conn.commit()
    increment_db_version()


def iniciar_prova(tag, proof_id, questoes):
    st.session_state["prova_ativa"] = True
    st.session_state["prova_tag"] = tag
    st.session_state["prova_proof_id"] = proof_id
    st.session_state["prova_questoes"] = questoes
    st.session_state["prova_answers"] = []
    st.session_state["prova_idx"] = 0
    st.session_state["prova_concluida"] = False


def _update_bkt_from_proof(tag, is_correct, dificuldade, cognitive_order):
    conn = get_conn()
    row = conn.execute("""
        SELECT correct, total, mastery_prob, max_difficulty, max_cognitive_order
        FROM tag_stats WHERE tag = ?
    """, (tag,)).fetchone()

    if row:
        curr_prob = row["mastery_prob"] if row["mastery_prob"] is not None else 0.15
        corrects = row["correct"] + int(is_correct)
        totals = row["total"] + 1
        old_max_diff = row["max_difficulty"] or "Easy"
        old_max_cog = row["max_cognitive_order"] or "1st Order (Direct Recall / Diagnosis)"
    else:
        curr_prob = 0.15
        corrects = int(is_correct)
        totals = 1
        old_max_diff = "Easy"
        old_max_cog = "1st Order (Direct Recall / Diagnosis)"

    new_prob = update_bkt(curr_prob, is_correct, "Certeza Absoluta", dificuldade, totals)

    cur_diff_rank = DIFFICULTY_RANK.get(dificuldade, 0)
    old_diff_rank = DIFFICULTY_RANK.get(old_max_diff, 0)
    new_diff_rank = max(cur_diff_rank, old_diff_rank)

    cur_cog_rank = COGNITIVE_RANK.get(cognitive_order, 0)
    old_cog_rank = COGNITIVE_RANK.get(old_max_cog, 0)
    new_cog_rank = max(cur_cog_rank, old_cog_rank)

    conn.execute("""
        INSERT INTO tag_stats (tag, correct, total, mastery_prob, max_difficulty, max_cognitive_order)
        VALUES (?, ?, 1, ?, ?, ?)
        ON CONFLICT(tag) DO UPDATE SET
            correct = ?,
            total = ?,
            mastery_prob = ?,
            max_difficulty = ?,
            max_cognitive_order = ?
    """, (tag, corrects, new_prob, RANK_TO_DIFFICULTY[new_diff_rank], RANK_TO_COGNITIVE[new_cog_rank],
          corrects, totals, new_prob, RANK_TO_DIFFICULTY[new_diff_rank], RANK_TO_COGNITIVE[new_cog_rank]))
    conn.commit()
    increment_db_version()


def responder_questao_prova(questao_idx, letra_escolhida, is_correct, dificuldade, cognitive_order):
    from database import save_proof_answer, update_proof_answer
    questoes = st.session_state["prova_questoes"]
    tag = st.session_state["prova_tag"]
    proof_id = st.session_state["prova_proof_id"]
    q = questoes[questao_idx]

    a_id = save_proof_answer(
        proof_id, tag,
        json.dumps(q, ensure_ascii=False),
        dificuldade, cognitive_order
    )
    update_proof_answer(a_id, letra_escolhida, is_correct)

    _update_bkt_from_proof(tag, is_correct, dificuldade, cognitive_order)

    st.session_state["prova_answers"].append({
        "proof_answer_id": a_id,
        "is_correct": is_correct
    })


def avancar_prova():
    st.session_state["prova_idx"] += 1
    if st.session_state["prova_idx"] >= len(st.session_state["prova_questoes"]):
        st.session_state["prova_concluida"] = True


def concluir_prova():
    from database import set_validation_result
    answers = st.session_state["prova_answers"]
    total = len(answers)
    acertos = sum(1 for a in answers if a["is_correct"])
    score = acertos / total if total > 0 else 0
    passed = score >= 0.80
    tag = st.session_state["prova_tag"]

    set_validation_result(tag, st.session_state["prova_proof_id"],
                          score, total, passed)

    if passed:
        conn = get_conn()
        row = conn.execute("""
            SELECT mastery_prob FROM tag_stats WHERE tag = ?
        """, (tag,)).fetchone()
        curr_prob = row["mastery_prob"] if row and row["mastery_prob"] is not None else 0.15
        boosted = max(curr_prob, 0.70)
        conn.execute("""
            UPDATE tag_stats SET mastery_prob = ? WHERE tag = ?
        """, (boosted, tag))
        conn.commit()
        increment_db_version()

    return passed, acertos, total


def limpar_prova():
    for k in ["prova_ativa", "prova_tag", "prova_proof_id", "prova_questoes",
              "prova_answers", "prova_idx", "prova_concluida"]:
        if k in st.session_state:
            del st.session_state[k]
