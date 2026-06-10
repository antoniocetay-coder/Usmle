from knowledge_graph import KnowledgeGraph
from centrality import CentralityAnalyzer
from student_graph import StudentGraph
from candidate_generator import CandidateGenerator
from decision_engine import DecisionEngine
from analytics import get_tag_stats


def _build_pipeline():
    kg = KnowledgeGraph()
    centrality = CentralityAnalyzer(kg)
    sg = StudentGraph(kg, centrality)
    tag_stats = get_tag_stats()
    sg.load_from_db(tag_stats)
    cg = CandidateGenerator(kg, sg, centrality)
    de = DecisionEngine(kg, sg, centrality, cg)
    return kg, centrality, sg, cg, de, tag_stats


def recommend(modo="default"):
    kg, centrality, sg, cg, de, tag_stats = _build_pipeline()

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
    }
