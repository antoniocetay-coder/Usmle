import streamlit as st
from knowledge_graph import KnowledgeGraph
from centrality import CentralityAnalyzer
from student_graph import StudentGraph
from candidate_generator import CandidateGenerator
from decision_engine import DecisionEngine
from analytics import get_tag_stats
from confusion_engine import ConfusionGraph, StudentConfusionGraph, ConfusionTracker


@st.cache_resource
def get_core_kg_centrality():
    kg = KnowledgeGraph()
    centrality = CentralityAnalyzer(kg)
    return kg, centrality


@st.cache_resource
def _build_pipeline_cached(db_version):
    kg, centrality = get_core_kg_centrality()
    sg = StudentGraph(kg, centrality)

    tag_stats = get_tag_stats()
    sg.load_from_db(tag_stats)

    cg = CandidateGenerator(kg, sg, centrality)

    cg_confusion = ConfusionGraph(kg)
    cg_confusion.load_from_db()
    cg_confusion.load_from_legacy_confusion_pairs()

    sg_confusion = StudentConfusionGraph(kg)
    sg_confusion.load_from_db()

    confusion_tracker = ConfusionTracker(cg_confusion, sg_confusion, kg)

    de = DecisionEngine(kg, sg, centrality, cg, confusion_tracker=confusion_tracker)

    return kg, centrality, sg, cg, de, tag_stats, confusion_tracker


def recommend(db_version=None):
    if db_version is None:
        try:
            db_version = st.session_state.get("db_version", 0)
        except Exception:
            db_version = 0

    kg, centrality, sg, cg, de, tag_stats, ct = _build_pipeline_cached(db_version)

    mission = de.generate_study_mission()
    eligible = cg.eligible_concepts()

    queue = []
    for conc in eligible:
        state = sg.get_state(conc)
        if state is None:
            continue
        tipo = "review" if state.review_due else ("new" if state.mastery < 0.4 else "review")
        priority = 1.0 - state.mastery
        queue.append({
            "concept": conc,
            "mastery": state.mastery,
            "tipo": tipo,
            "priority": round(priority, 4),
        })
    queue.sort(key=lambda x: -x["priority"])

    return {
        "mission": mission,
        "queue": queue[:10],
        "eligible": eligible,
        "summary": sg.student_summary(),
        "eligible_count": len(eligible),
        "blocked_count": len(cg.blocked_concepts()),
        "confusion_count": ct.global_graph.edge_count(),
        "top_confusions": ct.get_student_confusions(n=5),
    }
