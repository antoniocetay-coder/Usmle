import streamlit as st
import json
import time
from flashcard_engine import orquestrar_flashcards, gerar_mais_flashcards, gerar_flashcard_sob_demanda
from database import get_flashcards_by_tags, registrar_confusao, salvar_flashcard_db
from session_state import salvar_resultado_pendente, proximo_item_fila
from confusion_engine import ConfusionGraph, ConfusionTracker


def _get_confusion_tracker():
    if "confusion_tracker" not in st.session_state:
        cg = ConfusionGraph()
        cg.load_from_db()
        st.session_state["confusion_tracker"] = ConfusionTracker(cg)
    return st.session_state["confusion_tracker"]


def render_question(item_atual, api_key):
    q_db = item_atual["item"]
    q = json.loads(q_db["question_json"])

    if st.session_state["tempo_inicio_questao"] is None:
        st.session_state["tempo_inicio_questao"] = time.time()

    st.markdown(f"## 📝 Questão de {q_db['sistema']} ({q_db['dificuldade']})")
    st.info(q["vignette"])

    escolha = st.radio("Escolha a melhor alternativa:", q["options"],
                        index=None, disabled=st.session_state["resposta_submetida"])

    st.write("**Qual seu nível de confiança nesta resposta?**")
    confianca = st.radio(
        "Confiança",
        ["Certeza Absoluta", "Dúvida entre 2", "Chute Cego"],
        horizontal=True,
        index=None,
        label_visibility="collapsed",
        disabled=st.session_state["resposta_submetida"]
    )

    if not st.session_state["resposta_submetida"]:
        if st.button("Submeter", disabled=(escolha is None or confianca is None)):
            _submit_answer(q_db, q, escolha, confianca)

    if st.session_state["resposta_submetida"]:
        _render_question_result(q_db, q, api_key)


def _submit_answer(q_db, q, escolha, confianca):
    tempo_gasto = int(time.time() - st.session_state["tempo_inicio_questao"])
    letra = escolha[0].upper()
    correto = (letra == q["correct"])

    st.session_state["resposta_submetida"] = True
    st.session_state["acertou_ultima"] = correto
    st.session_state["letra_escolhida"] = letra
    st.session_state["confianca_escolhida"] = confianca
    st.session_state["tempo_gasto"] = tempo_gasto

    salvar_resultado_pendente(
        q_db["id"], q_db["sistema"], correto, q["content_tags"], tempo_gasto, confianca,
        dificuldade=q_db.get("dificuldade", "Medium"),
        cognitive_order=q_db.get("cognitive_order", "1st Order (Direct Recall / Diagnosis)")
    )

    if not correto and confianca != "Chute Cego":
        dist_tags = q.get("distractor_tags", {})
        tag_correta = dist_tags.get(q["correct"])
        tag_errada = dist_tags.get(letra)
        if tag_correta and tag_errada:
            registrar_confusao(tag_correta, tag_errada)
            tracker = _get_confusion_tracker()
            tracker.record_event(
                correct_tag=tag_correta,
                chosen_tag=tag_errada,
                confidence_label=confianca,
                question_id=q_db["id"],
            )
            tracker.graph.save_to_db()

    st.rerun()


def _render_question_result(q_db, q, api_key):
    t_gasto = st.session_state["tempo_gasto"]
    if st.session_state["acertou_ultima"]:
        if st.session_state["confianca_escolhida"] == "Chute Cego":
            st.warning(f"⚠️ Correto, mas foi um Chute Cego! (Tempo: {t_gasto}s)")
        else:
            st.success(f"✅ Correto! (Tempo: {t_gasto}s)")
    else:
        st.error(f"❌ Errado. Correta: {q['correct']} (Tempo: {t_gasto}s)")

    if t_gasto > 90:
        st.caption("⏱️ *Aviso: Você passou da marca de 90 segundos do USMLE.*")

    st.markdown("---")
    for opcao in q["options"]:
        letra = opcao[0]
        exp = q["explanations"].get(letra, "")
        if letra == q["correct"]:
            st.success(f"{opcao}\n\n{exp}")
        else:
            st.write(f"{opcao}\n\n{exp}")

    st.info(f"**Educational Objective:**\n{q['educational_objective']}")
    st.caption(" | ".join(q["content_tags"]))

    _render_forge_panel(q, api_key, q_db)

    st.markdown("---")
    if st.button("Próximo Item ➡️", use_container_width=True, type="primary"):
        proximo_item_fila()


def _render_forge_panel(q, api_key, q_db):
    st.markdown("---")
    st.markdown("### 🛠️ Forja de Flashcards")

    cards_banco_atual = get_flashcards_by_tags(q["content_tags"])

    col_btn_erro, col_btn_mais = st.columns(2)
    with col_btn_erro:
        if st.button("💡 Analisar meu Erro/Chute", use_container_width=True):
            with st.spinner("Analisando seu viés e checando banco de cards..."):
                rascunhos_tela = st.session_state.get("flashcards_rascunho", [])
                cards_ia = orquestrar_flashcards(
                    q,
                    st.session_state["letra_escolhida"],
                    st.session_state["acertou_ultima"],
                    st.session_state["confianca_escolhida"],
                    cards_banco_atual,
                    rascunhos_tela,
                    api_key
                )
                if cards_ia:
                    if "flashcards_rascunho" not in st.session_state:
                        st.session_state["flashcards_rascunho"] = []
                    st.session_state["flashcards_rascunho"].extend(cards_ia)
                    st.rerun()

    with col_btn_mais:
        if st.button("➕ Explorar Outros Ângulos", use_container_width=True):
            with st.spinner("Buscando novos ângulos da doença..."):
                rascunhos_tela = st.session_state.get("flashcards_rascunho", [])
                novos_cards = gerar_mais_flashcards(q, cards_banco_atual, rascunhos_tela, api_key)
                if novos_cards:
                    if "flashcards_rascunho" not in st.session_state:
                        st.session_state["flashcards_rascunho"] = []
                    st.session_state["flashcards_rascunho"].extend(novos_cards)
                    st.rerun()

    st.write("")
    col_input, col_btn_especifico = st.columns([3, 1])
    with col_input:
        pedido_customizado = st.text_input(
            "Lacuna Específica",
            placeholder="Ex: Fisiopatologia da alternativa C",
            label_visibility="collapsed"
        )
    with col_btn_especifico:
        if st.button("🎯 Gerar Específico", use_container_width=True):
            if pedido_customizado:
                with st.spinner("Forjando card sob demanda..."):
                    rascunhos_tela = st.session_state.get("flashcards_rascunho", [])
                    novos_cards = gerar_flashcard_sob_demanda(q, pedido_customizado, cards_banco_atual,
                                                               rascunhos_tela, api_key)
                    if novos_cards:
                        if "flashcards_rascunho" not in st.session_state:
                            st.session_state["flashcards_rascunho"] = []
                        st.session_state["flashcards_rascunho"].extend(novos_cards)
                        st.rerun()
            else:
                st.warning("Digite algo ao lado.")

    _render_draft_approval_form(q, q_db)


def _render_draft_approval_form(q, q_db):
    if st.session_state.get("flashcards_salvos", False):
        st.success("✅ Cards salvos no Baralho!")
    else:
        rascunhos = st.session_state.get("flashcards_rascunho", [])
        if len(rascunhos) > 0:
            st.markdown("---")
            chave_unica = f"form_{q_db['id']}"
            with st.form(key=chave_unica):
                editados = []
                for i, card in enumerate(rascunhos):
                    st.write(f"**Card {i + 1}**")
                    key_front = f"f_{i}_{q_db['id']}"
                    key_back = f"b_{i}_{q_db['id']}"
                    novo_front = st.text_area("Q (Front)", value=card.get("front", ""), key=key_front)
                    novo_back = st.text_area("A (Back)", value=card.get("back", ""), key=key_back)
                    editados.append({"front": novo_front, "back": novo_back, "tags": card.get("tags", q["content_tags"])})

                if st.form_submit_button("Aprovar e Salvar Todos"):
                    for c in editados:
                        salvar_flashcard_db(c["front"], c["back"], q_db["sistema"], c["tags"])
                    st.session_state["flashcards_salvos"] = True
                    st.rerun()
