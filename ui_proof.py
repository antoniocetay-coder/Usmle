import streamlit as st
import json
import uuid
import time as pytime
from database import set_validation_started
from session_state import iniciar_prova, responder_questao_prova, avancar_prova, concluir_prova, limpar_prova
from proof_engine import gerar_prova


def render_proof_setup(api_key, tags_eligiveis):
    st.subheader("🏆 Prove Your Mastery")
    st.write("Selecione uma tag para validar com um teste de 20 questões.")

    if not tags_eligiveis:
        st.info("Nenhuma tag elegível no momento. Continue estudando até pelo menos **Consolidated (RK ≥ 70%)**.")
        return

    for entry in tags_eligiveis:
        tag = entry["tag"]
        rk = entry["rk"]
        status = entry["status"]

        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([3, 1, 1, 2])
            col1.markdown(f"**{tag}**")
            col2.markdown(f"RK: {rk:.0%}")
            col3.markdown(f"Status: {status}")
            if status == "failed":
                col4.warning("Cooldown 7d")
            elif col4.button("⚡ Prove It", key=f"prove_{tag}", use_container_width=True, type="primary"):
                if not api_key:
                    st.error("API Key necessária para gerar a prova.")
                else:
                    with st.spinner(f"Gerando 20 questões de validação para {tag}..."):
                        questoes = gerar_prova(tag, api_key, 20)
                    if len(questoes) < 5:
                        st.error("Não foi possível gerar questões suficientes. Tente novamente.")
                    else:
                        proof_id = str(uuid.uuid4())
                        set_validation_started(tag, proof_id)
                        questoes = questoes[:20]
                        iniciar_prova(tag, proof_id, questoes)
                        st.rerun()


def render_proof_active():
    questoes = st.session_state["prova_questoes"]
    idx = st.session_state["prova_idx"]
    total = len(questoes)
    tag = st.session_state["prova_tag"]

    st.subheader(f"🏆 Prova de Validação: {tag}")
    st.progress((idx) / total, text=f"{idx + 1} / {total}")
    st.caption("Responda todas as 20 questões. Mínimo 80% para validar.")

    if st.button("🔙 Abandonar Prova (contará como falha)"):
        from database import set_validation_result
        score = 0
        total_ans = len(st.session_state["prova_answers"])
        if total_ans > 0:
            acertos = sum(1 for a in st.session_state["prova_answers"] if a["is_correct"])
            score = acertos / total_ans
        set_validation_result(tag, st.session_state["prova_proof_id"], score, total_ans, False)
        limpar_prova()
        st.rerun()

    if st.session_state["prova_concluida"]:
        render_proof_result()
        return

    q = questoes[idx]
    st.markdown("---")

    st.info(q.get("vignette", ""))

    dificuldade = q.get("difficulty", "Medium")
    cognitive_order = q.get("cognitive_order", "1st Order (Direct Recall / Diagnosis)")
    st.caption(f"Dificuldade: {dificuldade} | Ordem: {cognitive_order}")

    options = q.get("options", [])
    key_radio = f"proof_radio_{idx}"

    if f"proof_submitted_{idx}" not in st.session_state:
        st.session_state[f"proof_submitted_{idx}"] = False

    escolha = st.radio("Escolha a alternativa:", options, index=None,
                        key=key_radio, disabled=st.session_state[f"proof_submitted_{idx}"])

    if not st.session_state[f"proof_submitted_{idx}"]:
        if st.button("Confirmar", disabled=escolha is None, key=f"proof_btn_{idx}"):
            letra = escolha[0].upper()
            correto = (letra == q.get("correct", ""))

            responder_questao_prova(idx, letra, correto, dificuldade, cognitive_order)
            st.session_state[f"proof_submitted_{idx}"] = True
            st.rerun()

    if st.session_state[f"proof_submitted_{idx}"]:
        correto = q["correct"]
        explicacoes = q.get("explanations", {})
        st.markdown(f"**Correta:** {correto}")
        for opcao in options:
            letra = opcao[0]
            exp = explicacoes.get(letra, "")
            if letra == correto:
                st.success(f"{opcao}\n\n{exp}")
            else:
                st.write(f"{opcao}\n\n{exp}")
        st.info(q.get("educational_objective", ""))

        if st.button("Próxima ➡️", key=f"proof_next_{idx}", type="primary"):
            st.session_state[f"proof_submitted_{idx}"] = False
            avancar_prova()
            st.rerun()


def render_proof_result():
    passed, acertos, total = concluir_prova()
    tag = st.session_state["prova_tag"]
    pct = acertos / total * 100 if total > 0 else 0

    st.markdown("---")
    st.subheader("📊 Resultado da Validação")

    col1, col2, col3 = st.columns(3)
    col1.metric("Acertos", f"{acertos}/{total}")
    col2.metric("Score", f"{pct:.0f}%")
    col3.metric("Mínimo", "80%")

    if passed:
        st.success(f"✅ **{tag} VALIDADO!** Parabéns, você provou domínio sobre este tópico.")
        st.balloons()
    else:
        st.error(f"❌ **{tag} NÃO validado.** Você fez {pct:.0f}% (mínimo 80%). Tente novamente em 7 dias.")
        st.info("💡 Revise os conceitos que errou e foque nas lacunas identificadas.")

    if st.button("🔙 Voltar ao Dashboard", use_container_width=True):
        limpar_prova()
        st.rerun()
