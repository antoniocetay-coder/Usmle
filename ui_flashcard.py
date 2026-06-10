import streamlit as st
import datetime
import time
from fsrs import calcular_fsrs
from ai_engine import explicar_duvida_tutor
from flashcard_engine import gerar_flashcards_do_tutor
from database import get_conn, ItemType, salvar_flashcard_db
from session_state import now_utc, hoje_str, proximo_item_fila


def render_flashcard(item_atual, api_key, fila, idx):
    card = item_atual["item"]

    is_learning = item_atual.get("is_learning", False)
    unlock_time = item_atual.get("unlock_time", 0)
    target_interval = item_atual.get("target_interval", 1)

    if unlock_time > time.time():
        _render_locked_flashcard(item_atual, unlock_time, fila, idx)
    else:
        _render_unlocked_flashcard(card, is_learning, target_interval, api_key)


def _render_locked_flashcard(item_atual, unlock_time, fila, idx):
    restante = int(unlock_time - time.time())
    minutos = restante // 60
    segundos = restante % 60

    is_last_unlocked = True
    for next_item in fila[idx + 1:]:
        if next_item.get("unlock_time", 0) < time.time():
            is_last_unlocked = False
            break

    if is_last_unlocked:
        st.warning("⏳ Aguardando tempo de fixação...")
        st.info(f"O cérebro precisa de um intervalo. Este card estará disponível em **{minutos}m {segundos}s**.")
        if st.button("🔄 Checar Tempo", use_container_width=True, type="primary"):
            st.rerun()
    else:
        st.warning("⏳ Este card está em tempo de fixação (Spaced Learning).")
        st.info("Pule para o próximo item e este card retornará automaticamente na hora certa.")
        if st.button("Pular para o próximo disponível ➡️", use_container_width=True):
            st.session_state["fila_estudo"].append(item_atual)
            st.session_state["idx_atual"] += 1
            st.rerun()


def _render_unlocked_flashcard(card, is_learning, target_interval, api_key):
    st.markdown("## 🃏 Flashcard")
    if is_learning:
        st.caption("🔄 Fase de Fixação (Learning Step)")

    st.info(card["front"])

    if not st.session_state["revelar_flashcard"]:
        if st.button("Mostrar Resposta", use_container_width=True):
            st.session_state["revelar_flashcard"] = True
            st.rerun()
    else:
        st.success(card["back"])
        hoje_data = now_utc().date()
        try:
            last_rev_data = datetime.datetime.strptime(card["last_review"], "%Y-%m-%d").date()
            elapsed_days = (hoje_data - last_rev_data).days
        except Exception:
            elapsed_days = 0

        _render_tutor_ai(card, api_key)

        st.markdown("---")

        if not is_learning:
            _render_fsrs_evaluation(card, elapsed_days)
        else:
            _render_learning_evaluation(card, target_interval)


def _render_tutor_ai(card, api_key):
    st.markdown("### 🧑‍🏫 Tutor AI")
    col_tutor_input, col_tutor_btn = st.columns([4, 1])

    with col_tutor_input:
        duvida_tutor = st.text_input(
            "Dúvida",
            placeholder="Não entendeu o card? Peça uma explicação...",
            label_visibility="collapsed",
            key=f"input_tutor_{card['id']}"
        )

    with col_tutor_btn:
        clicou_perguntar = st.button("🗣️ Perguntar", use_container_width=True, key=f"btn_tutor_{card['id']}")

    if clicou_perguntar:
        if not api_key:
            st.error("API Key necessária.")
        elif not duvida_tutor:
            st.warning("Digite uma dúvida.")
        else:
            with st.spinner("O Tutor está digitando..."):
                contexto = f"Front: {card['front']}\nBack: {card['back']}"
                resposta = explicar_duvida_tutor(contexto, duvida_tutor, api_key)
                st.session_state["resposta_tutor_atual"] = resposta

    if st.session_state["resposta_tutor_atual"]:
        st.info(st.session_state["resposta_tutor_atual"])
        if st.button("⚡ Transformar Explicação em Flashcard", key=f"btn_transf_{card['id']}"):
            with st.spinner("Forjando novo card..."):
                cards_tela = [card]
                rascunhos_tela = st.session_state.get("flashcards_rascunho", [])

                novos_cards = gerar_flashcards_do_tutor(
                    st.session_state["resposta_tutor_atual"],
                    cards_tela,
                    rascunhos_tela,
                    api_key
                )

                if novos_cards:
                    st.session_state["flashcards_rascunho"].extend(novos_cards)
                    st.rerun()

    rascunhos = st.session_state.get("flashcards_rascunho", [])
    if len(rascunhos) > 0:
        st.markdown("---")
        chave_unica = f"form_tutor_{card['id']}"
        with st.form(key=chave_unica):
            editados = []
            for i, c_rascunho in enumerate(rascunhos):
                st.write(f"**Card {i + 1} (Expansão do Tutor)**")
                key_front = f"tf_{i}_{card['id']}"
                key_back = f"tb_{i}_{card['id']}"
                novo_front = st.text_area("Q (Front)", value=c_rascunho.get("front", ""), key=key_front)
                novo_back = st.text_area("A (Back)", value=c_rascunho.get("back", ""), key=key_back)
                editados.append({"front": novo_front, "back": novo_back, "tags": ["Tutor_Expansion"]})

            if st.form_submit_button("Aprovar e Salvar Todos"):
                for c in editados:
                    salvar_flashcard_db(c["front"], c["back"], card.get("sistema", "General"), c["tags"])
                st.session_state["flashcards_rascunho"] = []
                st.success("✅ Card do Tutor Salvo!")
                time.sleep(1)
                st.rerun()


def _render_fsrs_evaluation(card, elapsed_days):
    st.write("Avalie sua resposta (FSRS):")
    g_info = {}
    for g in [1, 2, 3, 4]:
        g_info[g] = calcular_fsrs(g, card["difficulty"], card["stability"], max(0, elapsed_days),
                                   card["repetitions"], card["lapses"])

    col1, col2, col3, col4 = st.columns(4)

    if col1.button("Again (<1m)", use_container_width=True):
        d, s, r, interval, reps, lapses = g_info[1]
        _update_srs_state(card, d, s, reps, lapses, hoje_str())
        st.session_state["fila_estudo"].append({
            "type": "flashcard", "item": card, "is_learning": True,
            "unlock_time": time.time() + 60, "target_interval": interval
        })
        st.toast("Enviado para fixação (1 min) 🔄")
        proximo_item_fila()

    if col2.button("Hard (5m)", use_container_width=True):
        d, s, r, interval, reps, lapses = g_info[2]
        _update_srs_state(card, d, s, reps, lapses, hoje_str())
        st.session_state["fila_estudo"].append({
            "type": "flashcard", "item": card, "is_learning": True,
            "unlock_time": time.time() + 300, "target_interval": interval
        })
        st.toast("Enviado para fixação (5 min) 🔄")
        proximo_item_fila()

    if col3.button(f"Good ({g_info[3][3]}d)", use_container_width=True):
        d, s, r, interval, reps, lapses = g_info[3]
        prox = (now_utc() + datetime.timedelta(days=interval)).strftime("%Y-%m-%d")
        _update_srs_state(card, d, s, reps, lapses, prox)
        st.toast(f"Próxima revisão em: {interval} dia(s)")
        proximo_item_fila()

    if col4.button(f"Easy ({g_info[4][3]}d)", use_container_width=True):
        d, s, r, interval, reps, lapses = g_info[4]
        prox = (now_utc() + datetime.timedelta(days=interval)).strftime("%Y-%m-%d")
        _update_srs_state(card, d, s, reps, lapses, prox)
        st.toast(f"Próxima revisão em: {interval} dia(s)")
        proximo_item_fila()


def _render_learning_evaluation(card, target_interval):
    st.write("Avalie a sua fixação:")
    col1, col2, col3 = st.columns(3)

    if col1.button("Again (<1m)", use_container_width=True):
        st.session_state["fila_estudo"].append({
            "type": "flashcard", "item": card, "is_learning": True,
            "unlock_time": time.time() + 60, "target_interval": target_interval
        })
        st.toast("Mantido na fixação (1 min) 🔄")
        proximo_item_fila()

    if col2.button("Hard (5m)", use_container_width=True):
        st.session_state["fila_estudo"].append({
            "type": "flashcard", "item": card, "is_learning": True,
            "unlock_time": time.time() + 300, "target_interval": target_interval
        })
        st.toast("Mantido na fixação (5 min) 🔄")
        proximo_item_fila()

    if col3.button("Good (Graduar)", use_container_width=True):
        prox = (now_utc() + datetime.timedelta(days=target_interval)).strftime("%Y-%m-%d")
        conn = get_conn()
        conn.execute("UPDATE srs_state SET due=? WHERE object_id=? AND object_type=?",
                     (prox, card["id"], ItemType.FLASHCARD.value))
        conn.commit()
        st.toast(f"Card Graduado! 🎉 Próximo em: {target_interval} dia(s)")
        proximo_item_fila()


def _update_srs_state(card, d, s, reps, lapses, due):
    conn = get_conn()
    conn.execute("""
        INSERT INTO srs_state (object_id, object_type, repetitions, stability, difficulty, last_review, due, lapses)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(object_id, object_type) DO UPDATE SET
            repetitions=excluded.repetitions, stability=excluded.stability,
            difficulty=excluded.difficulty, last_review=excluded.last_review,
            due=excluded.due, lapses=excluded.lapses
    """, (card["id"], ItemType.FLASHCARD.value, reps, s, d, hoje_str(), due, lapses))
    conn.commit()
