import streamlit as st
import plotly.graph_objects as go
from database import get_system_stats, get_metacognition_stats, get_time_stats, get_fsrs_forecast, get_global_confusions, get_conn, get_validation_status, get_tags_proven
from mastery import classify_tag_bkt, real_knowledge, get_next_level, is_eligible_for_proof, P_L0
from session_state import now_utc
from datetime import datetime


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

        sistemas = [r["sistema"] for r in sys_stats]
        accuracies = [(r["acertos"] / r["total"]) * 100 for r in sys_stats]

        fig_radar = go.Figure(go.Scatterpolar(
            r=accuracies,
            theta=sistemas,
            fill='toself',
            line_color='#00CC96',
            mode='lines+markers',
        ))
        fig_radar.update_layout(polar=dict(radialaxis=dict(range=[0, 100])))
        st.plotly_chart(fig_radar, use_container_width=True)

        st.markdown("---")

        col_meta, col_time = st.columns(2)

        with col_meta:
            st.subheader("🧠 Metacognição (Confiança vs Acerto)")
            if meta_stats:
                levels = sorted(set(r["confidence_level"] for r in meta_stats))
                acertou = {l: 0 for l in levels}
                errou = {l: 0 for l in levels}
                for r in meta_stats:
                    if r["answered_correctly"] == 1:
                        acertou[r["confidence_level"]] += r["qtd"]
                    else:
                        errou[r["confidence_level"]] += r["qtd"]

                fig_meta = go.Figure()
                fig_meta.add_trace(go.Bar(name="Acertou", x=levels, y=[acertou[l] for l in levels], marker_color="#28a745"))
                fig_meta.add_trace(go.Bar(name="Errou", x=levels, y=[errou[l] for l in levels], marker_color="#dc3545"))
                fig_meta.update_layout(barmode="group", xaxis_title="Nível de Confiança", yaxis_title="Qtd Questões")
                st.plotly_chart(fig_meta, use_container_width=True)
            else:
                st.caption("Sem dados de confiança registrados ainda.")

        with col_time:
            st.subheader("⏱️ Arrasto Cognitivo (Tempo Médio)")
            if time_stats:
                sistemas_t = list(dict.fromkeys(r["sistema"] for r in time_stats))
                t_acertou = {s: 0 for s in sistemas_t}
                t_errou = {s: 0 for s in sistemas_t}
                t_acertou_cnt = {s: 0 for s in sistemas_t}
                t_errou_cnt = {s: 0 for s in sistemas_t}
                for r in time_stats:
                    s = r["sistema"]
                    if r["answered_correctly"] == 1:
                        t_acertou[s] += r["avg_time"]
                        t_acertou_cnt[s] += 1
                    else:
                        t_errou[s] += r["avg_time"]
                        t_errou_cnt[s] += 1
                acertou_avg = [round(t_acertou[s] / t_acertou_cnt[s], 1) if t_acertou_cnt[s] > 0 else 0 for s in sistemas_t]
                errou_avg = [round(t_errou[s] / t_errou_cnt[s], 1) if t_errou_cnt[s] > 0 else 0 for s in sistemas_t]

                fig_time = go.Figure()
                fig_time.add_trace(go.Bar(name="Acertou", y=sistemas_t, x=acertou_avg, orientation='h', marker_color="#28a745"))
                fig_time.add_trace(go.Bar(name="Errou", y=sistemas_t, x=errou_avg, orientation='h', marker_color="#dc3545"))
                fig_time.update_layout(barmode="group", xaxis_title="Tempo Médio (s)", yaxis_title="Sistema")
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
                hoje = now_utc().date()
                fsrs_filtrado = []
                for r in fsrs_data:
                    try:
                        d = datetime.fromisoformat(r["due"]).date() if r["due"] else None
                    except (ValueError, TypeError):
                        d = None
                    if d and d >= hoje:
                        fsrs_filtrado.append({"due": d, "due_str": d.strftime('%d/%m'), "qtd": r["qtd"]})

                if fsrs_filtrado:
                    fsrs_filtrado.sort(key=lambda x: x["due"])
                    fig_fsrs = go.Figure(go.Bar(
                        x=[r["due_str"] for r in fsrs_filtrado],
                        y=[r["qtd"] for r in fsrs_filtrado],
                        marker_color="#636EFA",
                    ))
                    fig_fsrs.update_layout(xaxis_title="Data", yaxis_title="Flashcards Agendados")
                    st.plotly_chart(fig_fsrs, use_container_width=True)
                else:
                    st.caption("Nenhum card agendado para o futuro.")
            else:
                st.caption("Sem dados do FSRS.")

        with col_conf:
            st.subheader("🪤 Top Armadilhas (Red Herrings)")
            if confusions:
                st.dataframe(
                    [{
                        "O que era (Verdadeiro)": r["tag_correct"],
                        "O que você achou (Falso)": r["tag_confused"],
                        "Vezes que caiu": r["count"],
                    } for r in confusions],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.success("Você ainda não caiu em nenhum distrator de forma repetida!")

        st.markdown("---")
        with st.expander("🧩 Mapa de Confusão Cognitiva (Aluno vs Global)", expanded=False):
            try:
                from knowledge_graph import KnowledgeGraph
                from confusion_engine import ConfusionGraph, StudentConfusionGraph

                kg = KnowledgeGraph()
                cg = ConfusionGraph(kg)
                cg.load_from_db()
                cg.load_from_legacy_confusion_pairs()

                sg = StudentConfusionGraph(kg)
                sg.load_from_db()

                dash = sg.confusion_dashboard()

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total de Pares", dash["total_edges"])
                col2.metric("Confusões Ativas", dash["active_confusions"])
                col3.metric("Resolvidas", dash["resolved_confusions"])
                col4.metric("Mastery Médio", f"{dash['average_confusion_mastery']:.0%}")

                if dash["top_unresolved"]:
                    st.subheader("🔴 Principais Confusões por Resolver")
                    st.dataframe([{
                        "Conceito A": c["concept_a"],
                        "Conceito B": c["concept_b"],
                        "Peso": f"{c['weight']:.0%}",
                        "Evidências": c["evidence_count"],
                        "Mastery": f"{c['confusion_mastery']:.0%}",
                        "Acertos Seguidos": c["correct_streak"],
                    } for c in dash["top_unresolved"]], use_container_width=True, hide_index=True)

                global_top = cg.global_top_confusions(n=20)
                if global_top:
                    st.subheader("🌐 Top Confusões Globais (População)")
                    st.dataframe([{
                        "Conceito A": e["concept_a"],
                        "Conceito B": e["concept_b"],
                        "Peso": f"{e['weight']:.0%}",
                        "Evidências": e["evidence_count"],
                    } for e in global_top], use_container_width=True, hide_index=True)
            except Exception:
                st.caption("Mapa de confusão indisponível — resolva algumas questões primeiro.")

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
                rows.sort(key=lambda x: x["Real Knowledge"])
                st.dataframe(rows, use_container_width=True, hide_index=True)
