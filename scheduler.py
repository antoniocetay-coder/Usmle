import time
import streamlit as st
from database import get_cards_hoje, get_pending_questions, get_flashcards_full_by_tags, get_pending_questions_by_tags, get_eos_due, get_missed_tags_due
from recommender import recommend


def _get_srs_items():
    cards = get_cards_hoje()
    questions = get_pending_questions()
    eos = get_eos_due()
    srs_ids = set()
    items = []
    for c in cards:
        items.append({"type": "flashcard", "item": c, "source": "srs"})
        srs_ids.add(("flashcard", c["id"]))
    for q in questions:
        items.append({"type": "question", "item": q, "source": "srs"})
        srs_ids.add(("question", q["id"]))
    for eo in eos:
        items.append({"type": "eo", "item": eo, "source": "srs"})
    missed = get_missed_tags_due()
    for m in missed:
        items.append({"type": "missed_tag", "item": {"tag": m["object_id"]}, "source": "srs"})
    return items, srs_ids


def _get_pipeline_items(concepts, modo, srs_ids):
    if not concepts:
        return []
    items = []
    cards = get_flashcards_full_by_tags(concepts)
    for c in cards:
        key = ("flashcard", c["id"])
        if key not in srs_ids:
            items.append({"type": "flashcard", "item": c, "source": "pipeline"})
    qs = get_pending_questions_by_tags(concepts)
    for q in qs:
        key = ("question", q["id"])
        if key not in srs_ids:
            items.append({"type": "question", "item": q, "source": "pipeline"})
    return items


def montar_fila_estudo(modo_escolhido, qtd=10):
    srs_items, srs_ids = _get_srs_items()
    now = time.time()
    if ("recommend_cache" not in st.session_state
        or now - st.session_state.get("recommend_cache_ts", 0) > 60):
        st.session_state["recommend_cache"] = recommend()
        st.session_state["recommend_cache_ts"] = now
    rec = st.session_state["recommend_cache"]
    rec_concepts = rec.get("eligible", [])

    if modo_escolhido == "Review":
        pipeline_items = _get_pipeline_items(rec_concepts, "review", srs_ids)
        srs_review = [i for i in srs_items if i["type"] == "flashcard"]
        fila = srs_review + pipeline_items[:max(0, qtd - len(srs_review))]

    elif modo_escolhido == "QBank":
        pipeline_items = _get_pipeline_items(rec_concepts, "qbank", srs_ids)
        srs_qbank = [i for i in srs_items if i["type"] == "question"]
        fila = srs_qbank + pipeline_items[:max(0, qtd - len(srs_qbank))]

    elif modo_escolhido == "Interleaved":
        pipeline_items = _get_pipeline_items(rec_concepts, "interleaved", srs_ids)
        fila = []
        srs_cards = [i for i in srs_items if i["type"] == "flashcard"]
        srs_questions = [i for i in srs_items if i["type"] == "question"]
        p_cards = [i for i in pipeline_items if i["type"] == "flashcard"]
        p_questions = [i for i in pipeline_items if i["type"] == "question"]

        ic = iq = ipc = ipq = 0
        while len(fila) < qtd and (ic < len(srs_cards) or iq < len(srs_questions) or ipc < len(p_cards) or ipq < len(p_questions)):
            for _ in range(3):
                if ic < len(srs_cards):
                    fila.append(srs_cards[ic]); ic += 1
                elif ipc < len(p_cards):
                    fila.append(p_cards[ipc]); ipc += 1
            for _ in range(2):
                if iq < len(srs_questions):
                    fila.append(srs_questions[iq]); iq += 1
                elif ipq < len(p_questions):
                    fila.append(p_questions[ipq]); ipq += 1
            if len(fila) >= qtd:
                break

    else:
        fila = srs_items

    return fila[:qtd]
