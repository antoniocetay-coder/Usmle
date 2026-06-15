import streamlit as st
from config import *
from database import init_db
from backup import criar_backup
from session_state import startup, init_session_state, sair_do_modo_estudo
from ui_sidebar import render_sidebar
from ui_dashboard import render_dashboard
from ui_study_session import render_study_session
from ui_targeted import render_targeted_practice
from ui_analytics import render_analytics
from ui_history import render_history
from ui_proof import render_proof_setup, render_proof_active
from ui_explorer import render_explorer
from database import get_tags_eligiveis_prova
from analytics import get_tag_stats

startup()
criar_backup()
init_session_state()

# 1. Recebe APENAS a api_key, pois a dificuldade foi removida da sidebar
api_key = render_sidebar()

st.title("USMLE ECO-SYSTEM V2")

if st.session_state.get("prova_ativa", False):
    render_study_session(api_key)
else:
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["🏠 Dashboard", "🏆 Prove Mastery", "🎯 Targeted Practice", "📊 Analytics", "📜 History", "🌐 Explorer"]
    )

    with tab1:
        if st.session_state["modo_estudo"] is None:
            # 2. Passamos "Medium" como dificuldade padrão, já que não tem mais na sidebar
            render_dashboard(api_key, dificuldade="Medium", show_proof_section=False)
        else:
            render_study_session(api_key)

    with tab2:
        stats = get_tag_stats()
        tags_eligiveis = get_tags_eligiveis_prova(stats)
        render_proof_setup(api_key, tags_eligiveis)

    with tab3:
        # 3. Passamos "Medium" como dificuldade padrão aqui também
        render_targeted_practice(api_key, dificuldade="Medium")

    with tab4:
        render_analytics()

    with tab5:
        render_history()

    with tab6:
        render_explorer()