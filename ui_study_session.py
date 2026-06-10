import json
import streamlit as st
from database import get_conn, update_missed_tag_srs
from session_state import sair_do_modo_estudo, limpar_prova, proximo_item_fila
from ui_flashcard import render_flashcard
from ui_question import render_question
from ui_eo_card import render_eo_card
from ui_proof import render_proof_active, render_proof_setup
from database import get_tags_eligiveis_prova
from analytics import get_tag_stats
from ai_engine import gerar_questao


def render_study_session(api_key):
    if st.session_state.get("prova_ativa", False):
        st.button("🔙 Abandonar e Voltar", on_click=limpar_prova)
        if st.session_state["prova_concluida"]:
            from ui_proof import render_proof_result
            render_proof_result()
        else:
            render_proof_active()
        return

    fila = st.session_state["fila_estudo"]
    idx = st.session_state["idx_atual"]

    st.button("🔙 Sair e Voltar ao Dashboard", on_click=sair_do_modo_estudo)

    if idx >= len(fila):
        st.success("🎉 Sessão Concluída! Você destruiu a fila de hoje.")
        st.balloons()
        if st.session_state.get("modo_estudo") == "Targeted":
            _render_targeted_summary(st.session_state.get("targeted_tag"))
        _render_session_summary(fila, api_key)
    else:
        item_atual = fila[idx]
        progresso = f"Progresso: {idx + 1} / {len(fila)}"
        st.progress((idx) / len(fila), text=progresso)

        if item_atual["type"] == "flashcard":
            render_flashcard(item_atual, api_key, fila, idx)
        elif item_atual["type"] == "question":
            render_question(item_atual, api_key)
        elif item_atual["type"] == "eo":
            render_eo_card(item_atual)
        elif item_atual["type"] == "missed_tag":
            _render_missed_tag_card(item_atual, api_key)


def _render_session_summary(fila, api_key):
    conn = get_conn()
    q_ids = [item["item"]["id"] for item in fila if item["type"] == "question"]
    if not q_ids:
        return

    placeholders = ",".join("?" for _ in q_ids)
    rows = conn.execute(
        f"SELECT id, answered_correctly FROM questions WHERE id IN ({placeholders})",
        q_ids
    ).fetchall()

    total = len(rows)
    acertos = sum(1 for r in rows if r["answered_correctly"] == 1)
    if total == 0:
        return

    erros_por_tag = {}
    sistema_atual = None
    for item in fila:
        if item["type"] != "question":
            continue
        q_id = item["item"]["id"]
        sistema_atual = item["item"].get("sistema", sistema_atual)
        row_dict = {r["id"]: r["answered_correctly"] for r in rows}
        if row_dict.get(q_id) == 0:
            qj = item["item"].get("question_json", "{}")
            try:
                q_data = json.loads(qj)
                for t in q_data.get("content_tags", []):
                    erros_por_tag[t] = erros_por_tag.get(t, 0) + 1
            except (json.JSONDecodeError, TypeError):
                pass

    st.markdown("---")
    st.markdown(f"### 📊 Resumo da Sessão")
    c1, c2 = st.columns(2)
    c1.metric("Acertou", acertos)
    c2.metric("Errou", total - acertos)
    if total > 0:
        st.progress(acertos / total, text=f"{acertos}/{total} ({acertos/total:.0%})")

    if erros_por_tag:
        st.markdown("##### ❌ Erros por conceito")
        for tag, count in sorted(erros_por_tag.items(), key=lambda x: -x[1]):
            if st.button(f"📘 {tag} ({count} erro{'s' if count > 1 else ''})", key=f"revisit_{tag}", use_container_width=True):
                _generate_review_question(tag, sistema_atual or "General", api_key)
                st.rerun()


def _generate_review_question(tag, sistema, api_key):
    if not api_key:
        st.warning("API Key necessária.")
        return
    q = gerar_questao(sistema, "Medium", api_key, tags_alvo=[tag])
    if not q:
        st.error("Erro ao gerar questão.")
        return
    from database import salvar_questao
    q_id = salvar_questao(sistema, "Medium", q, False, q.get("content_tags", [tag]),
                          status="pending", cognitive_order=q.get("cognitive_order", "2nd Order (Pathophysiology / Next Step)"))
    novo_item = {"type": "question", "item": {
        "id": q_id, "sistema": sistema, "dificuldade": "Medium",
        "cognitive_order": q.get("cognitive_order"),
        "question_json": json.dumps(q, ensure_ascii=False),
    }, "source": "review"}
    fila = st.session_state["fila_estudo"]
    idx = st.session_state["idx_atual"]
    fila.insert(idx, novo_item)
    st.session_state["fila_estudo"] = fila


def _render_missed_tag_card(item_atual, api_key):
    tag = item_atual["item"]["tag"]
    st.markdown("## 🔁 Revisão Pendente")
    st.warning(f"Você errou uma questão sobre **{tag}** anteriormente e o mastery ainda está baixo.")
    st.markdown("Que tal tentar de novo com uma questão fresca?")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎯 Gerar Nova Questão", use_container_width=True, type="primary"):
            if not api_key:
                st.error("API Key necessária.")
            else:
                with st.spinner(f"Gerando questão para {tag}..."):
                    from database import salvar_questao
                    q = gerar_questao("General", "Medium", api_key, tags_alvo=[tag])
                    if not q:
                        st.error("Erro ao gerar.")
                        return
                    q_id = salvar_questao("General", "Medium", q, False, q.get("content_tags", [tag]),
                                          status="pending",
                                          cognitive_order="2nd Order (Pathophysiology / Next Step)")
                    novo_item = {"type": "question", "item": {
                        "id": q_id, "sistema": "General", "dificuldade": "Medium",
                        "cognitive_order": "2nd Order (Pathophysiology / Next Step)",
                        "question_json": json.dumps(q, ensure_ascii=False),
                    }, "source": "review"}
                    fila = st.session_state["fila_estudo"]
                    idx = st.session_state["idx_atual"]
                    fila[idx] = novo_item
                    st.session_state["fila_estudo"] = fila
                    update_missed_tag_srs(tag)
                    proximo_item_fila()
    with col2:
        if st.button("⏭ Pular", use_container_width=True):
            update_missed_tag_srs(tag)
            proximo_item_fila()


def _render_targeted_summary(tag):
    fila = st.session_state["fila_estudo"]
    conn = get_conn()
    q_ids = [item["item"]["id"] for item in fila if item["type"] == "question"]
    placeholders = ",".join("?" for _ in q_ids)
    rows = conn.execute(
        f"SELECT id, answered_correctly FROM questions WHERE id IN ({placeholders})",
        q_ids
    ).fetchall() if q_ids else []

    total = len(rows)
    acertos = sum(1 for r in rows if r["answered_correctly"] == 1)
    erros = total - acertos

    row = conn.execute("SELECT mastery_prob FROM tag_stats WHERE tag = ?", (tag,)).fetchone()
    mastery = row["mastery_prob"] if row else None

    st.markdown("---")
    st.markdown(f"### 📊 Resumo — {tag}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Acertou", acertos, delta=f"{acertos-total}" if total else None)
    c2.metric("Errou", erros)
    if mastery is not None:
        c3.metric("Mastery", f"{mastery:.0%}")
    else:
        c3.metric("Mastery", "N/A")
    if total > 0:
        st.progress(acertos / total, text=f"{acertos}/{total} ({acertos/total:.0%})")
    with st.expander("Detalhes por questão"):
        for item in fila:
            if item["type"] == "question":
                row = conn.execute(
                    "SELECT answered_correctly FROM questions WHERE id = ?",
                    (item["item"]["id"],)
                ).fetchone()
                status = "✅" if row and row["answered_correctly"] == 1 else "❌" if row and row["answered_correctly"] == 0 else "⏳"
                st.write(f"{status} {item['item']['id'][:8]}...")
