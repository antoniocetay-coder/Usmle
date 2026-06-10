import streamlit as st
import pandas as pd
import plotly.express as px
from database import get_system_stats, get_metacognition_stats, get_time_stats, get_fsrs_forecast, get_global_confusions, get_conn, get_validation_status, get_tags_proven
from mastery import classify_tag_bkt, real_knowledge, get_next_level, is_eligible_for_proof, P_L0
from session_state import now_utc


def render_analytics():
    st.header("📊 Cockpit de Performance USMLE")

    sys_stats = get_system_stats()
    meta_stats = get_metacognition_stats()
    time_stats = get_time_stats()
    fsrs_data = get_fsrs_forecast()
    confusions = get_global_confusions()

    if not sys_stats:
        st.info("Ainda não há dados suficientes. Resolva algumas questões no QBank!")
    else:
        st.subheader("🕸️ Radar de Domínio por Sistema")

        df_sys = pd.DataFrame(sys_stats)
        df_sys["accuracy"] = (df_sys["acertos"] / df_sys["total"]) * 100

        fig_radar = px.line_polar(
            df_sys, r='accuracy', theta='sistema', line_close=True,
            range_r=[0, 100], markers=True,
            color_discrete_sequence=['#00CC96']
        )
        fig_radar.update_traces(fill='toself')
        st.plotly_chart(fig_radar, use_container_width=True)

        st.markdown("---")

        col_meta, col_time = st.columns(2)

        with col_meta:
            st.subheader("🧠 Metacognição (Confiança vs Acerto)")
            if meta_stats:
                df_meta = pd.DataFrame(meta_stats)
                df_meta["Resultado"] = df_meta["answered_correctly"].apply(lambda x: "Acertou" if x == 1 else "Errou")

                fig_meta = px.bar(
                    df_meta, x="confidence_level", y="qtd", color="Resultado",
                    barmode="group",
                    color_discrete_map={"Acertou": "#28a745", "Errou": "#dc3545"},
                    labels={"confidence_level": "Nível de Confiança", "qtd": "Qtd Questões"}
                )
                st.plotly_chart(fig_meta, use_container_width=True)
            else:
                st.caption("Sem dados de confiança registrados ainda.")

        with col_time:
            st.subheader("⏱️ Arrasto Cognitivo (Tempo Médio)")
            if time_stats:
                df_time = pd.DataFrame(time_stats)
                df_time["Resultado"] = df_time["answered_correctly"].apply(lambda x: "Acertou" if x == 1 else "Errou")

                fig_time = px.bar(
                    df_time, x="avg_time", y="sistema", color="Resultado",
                    orientation='h', barmode='group',
                    color_discrete_map={"Acertou": "#28a745", "Errou": "#dc3545"},
                    labels={"avg_time": "Tempo Médio (s)", "sistema": "Sistema"}
                )
                fig_time.add_vline(x=90, line_width=2, line_dash="dash", line_color="red",
                                   annotation_text="USMLE Limit (90s)")
                st.plotly_chart(fig_time, use_container_width=True)
            else:
                st.caption("Sem dados de tempo registrados ainda.")

        st.markdown("---")

        col_fsrs, col_conf = st.columns(2)

        with col_fsrs:
            st.subheader("📅 Forecast de Revisões (FSRS)")
            if fsrs_data:
                df_fsrs = pd.DataFrame(fsrs_data)
                df_fsrs["due"] = pd.to_datetime(df_fsrs["due"])
                df_fsrs = df_fsrs[df_fsrs["due"].dt.date >= now_utc().date()]

                if not df_fsrs.empty:
                    df_fsrs["due_str"] = df_fsrs["due"].dt.strftime('%d/%m')
                    fig_fsrs = px.bar(
                        df_fsrs, x="due_str", y="qtd",
                        labels={"due_str": "Data", "qtd": "Flashcards Agendados"},
                        color_discrete_sequence=['#636EFA']
                    )
                    st.plotly_chart(fig_fsrs, use_container_width=True)
                else:
                    st.caption("Nenhum card agendado para o futuro.")
            else:
                st.caption("Sem dados do FSRS.")

        with col_conf:
            st.subheader("🪤 Top Armadilhas (Red Herrings)")
            if confusions:
                df_conf = pd.DataFrame(confusions)
                st.dataframe(
                    df_conf.rename(columns={
                        "tag_correct": "O que era (Verdadeiro)",
                        "tag_confused": "O que você achou (Falso)",
                        "count": "Vezes que caiu"
                    }),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.success("Você ainda não caiu em nenhum distrator de forma repetida!")

        st.markdown("---")
        with st.expander("Ver Domínio BKT Completo por Micro-Tags"):
            conn = get_conn()
            rows_db = conn.execute("""
                SELECT tag, correct, total, mastery_prob, max_difficulty, max_cognitive_order
                FROM tag_stats
            """).fetchall()

            proven_tags = get_tags_proven()

            rows = []
            for r in rows_db:
                if r["total"] > 0:
                    prob = r["mastery_prob"] if r["mastery_prob"] is not None else (r["correct"] / r["total"])
                    max_diff = r["max_difficulty"] or "Easy"
                    max_cog = r["max_cognitive_order"] or "1st Order (Direct Recall / Diagnosis)"
                    rk = real_knowledge(prob, max_diff, max_cog)
                    next_d, next_c = get_next_level(rk)

                    rk_pct = round(rk * 100, 1)
                    bkt_pct = round(prob * 100, 1)
                    is_proven = r["tag"] in proven_tags
                    nivel_dominio = classify_tag_bkt(rk, is_proven).value
                    gap = bkt_pct - rk_pct

                    gap_str = f"{gap:+.1f}%"
                    if gap > 5:
                        gap_str = f"⚠️ {gap:+.1f}%"

                    next_str = f"{next_d} / {next_c.split('(')[0].strip()}"

                    status_display = nivel_dominio.upper()
                    if is_proven:
                        status_display += " ✅"

                    valid = get_validation_status(r["tag"])
                    proof_label = ""
                    if is_proven:
                        proof_label = "✅"
                    elif valid["status"] == "failed":
                        proof_label = "⏳"
                    elif is_eligible_for_proof(rk):
                        proof_label = "⚡"

                    rows.append({
                        "Tag": r["tag"],
                        "Real Knowledge": rk_pct,
                        "BKT (raw)": bkt_pct,
                        "Gap": gap_str,
                        "Max Difficulty": max_diff,
                        "Next Level Needed": next_str,
                        "Attempts": r["total"],
                        "Status": status_display,
                        "Proof": proof_label
                    })

            if rows:
                df_tags = pd.DataFrame(rows).sort_values("Real Knowledge")
                st.dataframe(df_tags, use_container_width=True, hide_index=True)
