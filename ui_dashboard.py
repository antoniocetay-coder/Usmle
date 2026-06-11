import streamlit as st
from database import get_cards_hoje, get_pending_questions, get_tags_eligiveis_prova, get_tags_proven
from scheduler import montar_fila_estudo
from analytics import get_tag_stats
from mastery import real_knowledge, get_next_level, is_eligible_for_proof
from ui_proof import render_proof_setup
from brain import StudentBrain, StudyPath
from recommender import recommend


def _get_brain():
    if "brain" not in st.session_state:
        st.session_state["brain"] = StudentBrain()
    return st.session_state["brain"]


def _get_sistema_for_tag(tag, taxonomia):
    for sis, disciplinas in taxonomia.items():
        for tags_lista in disciplinas.values():
            if isinstance(tags_lista, list) and tag in tags_lista:
                return sis
    return "General_Principles"


def _build_paths_from_rec(rec):
    from ai_engine import TAXONOMIA_COMPLETA
    stats = get_tag_stats()
    queue = rec["queue"]

    def enrich(tag):
        s = stats.get(tag, {})
        prob = s.get("mastery_prob") or 0.15
        rk = real_knowledge(prob, s.get("max_difficulty", "Easy"),
                            s.get("max_cognitive_order", "1st Order (Direct Recall / Diagnosis)"))
        nd, nc = get_next_level(rk)
        return round(rk, 2), nd, nc

    def make_tags(concepts):
        return [{
            "tag": x["concept"],
            "sistema": _get_sistema_for_tag(x["concept"], TAXONOMIA_COMPLETA),
            "rk": enrich(x["concept"])[0],
            "next_difficulty": enrich(x["concept"])[1],
            "next_cognitive": enrich(x["concept"])[2],
        } for x in concepts]

    review_pool = [x for x in queue if x.get("tipo") == "review" or x["mastery"] < 0.40]
    advance_pool = [x for x in queue if 0.40 <= x["mastery"] < 0.80]
    expand_pool = [x for x in queue if x["mastery"] == 0.0] or queue[-3:]

    return [
        StudyPath(id="review", titulo="Revisar Lacunas",
                  descricao="Fortaleça fundamentos com mastery < 40%",
                  emoji="🔴", tags=make_tags(review_pool[:5]),
                  dificuldade="Medium",
                  ordem_cognitiva="1st Order (Direct Recall / Diagnosis)"),
        StudyPath(id="advance", titulo="Avançar Mastery",
                  descricao="Eleve o nível de conceitos em desenvolvimento",
                  emoji="🟡", tags=make_tags(advance_pool[:5]),
                  dificuldade="Hard",
                  ordem_cognitiva="2nd Order (Pathophysiology / Next Step)"),
        StudyPath(id="expand", titulo="Expandir Áreas",
                  descricao="Explore tópicos novos ou pouco vistos",
                  emoji="🟢", tags=make_tags(expand_pool[:5]),
                  dificuldade="Easy",
                  ordem_cognitiva="1st Order (Direct Recall / Diagnosis)"),
    ]


def _render_proof_section(api_key):
    stats = get_tag_stats()
    proven = get_tags_proven()
    proven_count = len(proven)

    tags_full = []
    for tag, s in stats.items():
        prob = s.get("mastery_prob", 0.15) or 0.15
        rk = real_knowledge(prob, s.get("max_difficulty", "Easy"),
                            s.get("max_cognitive_order", "1st Order (Direct Recall / Diagnosis)"))
        if is_eligible_for_proof(rk) or tag in proven:
            tags_full.append({"tag": tag, "rk": rk})

    if not tags_full and proven_count == 0:
        return

    eligiveis = get_tags_eligiveis_prova(stats)

    st.markdown("---")
    with st.container(border=True):
        col_icon, col_text, col_badge = st.columns([1, 3, 1])
        col_icon.markdown("### 🏆")
        col_text.markdown(f"### Prove Your Mastery")
        col_badge.markdown(f"**{proven_count} provadas**")

        if not eligiveis and proven_count > 0:
            st.success(f"🎉 **{proven_count}** tags já validadas! Continue estudando para liberar mais.")
        elif eligiveis:
            st.info(f"{len(eligiveis)} tags disponíveis para validação.")
            if st.button("⚡ Iniciar Validação", use_container_width=True, type="primary"):
                st.session_state["tab_proof"] = True
                st.rerun()


def render_dashboard(api_key, dificuldade, show_proof_section=True):
    cards_hoje = get_cards_hoje()
    questoes_pendentes = get_pending_questions()

    col1, col2 = st.columns(2)
    col1.metric("🃏 Flashcards Vencidos", len(cards_hoje))
    col2.metric("📝 Questões na Fila", len(questoes_pendentes))

    st.markdown("---")
    st.subheader("O que fazer agora?")

    qtd_gerar = st.slider("Quantas questões?", min_value=1, max_value=10, value=5)

    brain = _get_brain()
    paths = brain.get_paths()

    c1, c2, c3 = st.columns(3)
    gerando_agora = False

    for col, path in zip([c1, c2, c3], paths):
        with col:
            with st.container(border=True):
                st.markdown(f"**{path.emoji} {path.titulo}**")
                st.caption(path.descricao)
                st.write("")
                st.write("")

                if st.button(f"{path.emoji} {path.titulo}", use_container_width=True, key=f"path_{path.id}"):
                    gerando_agora = True
                    if not api_key:
                        st.error("API Key necessária.")
                    else:
                        with st.spinner(f"Gerando {qtd_gerar} questões..."):
                            sucessos = brain.execute(path.id, qtd_gerar, api_key)
                            if sucessos > 0:
                                st.success(f"{sucessos} questões geradas!")
                                from session_state import increment_db_version
                                increment_db_version()
                                st.rerun()
                            else:
                                st.error("Nenhuma questão gerada.")

    st.markdown("---")
    st.subheader("Modo de Estudo")

    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("🔋 Review Mode\n(Apenas Anki)", use_container_width=True, disabled=gerando_agora):
            st.session_state["modo_estudo"] = "Review"
            st.session_state["fila_estudo"] = montar_fila_estudo("Review")
            st.rerun()
    with c2:
        if st.button("⚡ QBank Mode\n(Apenas Questões)", use_container_width=True, disabled=gerando_agora):
            st.session_state["modo_estudo"] = "QBank"
            st.session_state["fila_estudo"] = montar_fila_estudo("QBank")
            st.rerun()
    with c3:
        if st.button("🧠 Interleaved Mode\n(O Super Deck)", use_container_width=True, disabled=gerando_agora):
            st.session_state["modo_estudo"] = "Interleaved"
            st.session_state["fila_estudo"] = montar_fila_estudo("Interleaved")
            st.rerun()

    st.markdown("---")

    mostrar_mapa = st.checkbox("🧩 Visualizar Mapa Cognitivo & Detalhes da IA (Avançado)", value=False)
    if mostrar_mapa:
        with st.spinner("Analisando seu mapa cognitivo..."):
            rec = recommend()
            summary = rec["summary"]
            mission = rec["mission"]

            with st.container(border=True):
                hub = mission.get("focus_hub", "—")
                conc = mission.get("study_concept")
                reason = mission.get("reason", {})
                col_hub, col_meta = st.columns([3, 1])
                col_hub.markdown(f"**Today's Mission** — *{hub}*")
                if conc:
                    col_hub.caption(f"Study concept: **{conc}** (mastery {reason.get('mastery', 0):.0%}, uncertainty {reason.get('uncertainty', 1):.1f})")
                col_meta.metric("Mastered", summary["mastered"])
                col_meta.metric("Weak", summary["weak"])

            st.write("##### 🎯 Sugestões Detalhadas do Recomentador:")
            paths_detail = _build_paths_from_rec(rec)
            cd1, cd2, cd3 = st.columns(3)
            for col_det, p_det in zip([cd1, cd2, cd3], paths_detail):
                with col_det:
                    with st.container(border=True):
                        st.markdown(f"**{p_det.emoji} {p_det.titulo}**")
                        for t in p_det.tags:
                            diff_str = f" → {t['next_difficulty']}/{t['next_cognitive'].split('(')[0].strip()}"
                            st.write(f"- **{t['tag']}** (RK: {t['rk']:.0%})")
                            st.caption(f"  {t['sistema']}{diff_str}")

    if show_proof_section:
        _render_proof_section(api_key)
