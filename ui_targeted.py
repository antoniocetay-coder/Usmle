import json
import streamlit as st
from config import SISTEMAS_DISPONIVEIS
from ai_engine import TAXONOMIA_COMPLETA, gerar_lote_questoes
from database import salvar_questao
from session_state import init_session_state


def render_targeted_practice(api_key, dificuldade):
    st.header("🎯 Prática Focada")
    st.write("Gere um bloco de questões sobre uma tag específica e responda de verdade.")

    col1, col2, col3 = st.columns(3)
    with col1:
        sys_brute = st.selectbox("Sistema:", SISTEMAS_DISPONIVEIS, key="tp_sistema")
    with col2:
        qtd = st.selectbox("Quantidade:", [3, 5, 10], index=1, key="tp_qtd")
    with col3:
        cog = st.selectbox("Ordem Cognitiva:", [
            "1st Order (Direct Recall / Diagnosis)",
            "2nd Order (Pathophysiology / Next Step)",
            "3rd Order (Management / Most Likely)"
        ], index=1, key="tp_cog")

    tax_brute = TAXONOMIA_COMPLETA.get(sys_brute, {})
    todas_tags_brute = []
    for tags_l in tax_brute.values():
        if isinstance(tags_l, list):
            todas_tags_brute.extend(tags_l)

    tag_alvo = st.selectbox("Tag Alvo:", sorted(todas_tags_brute), key="tp_tag")

    if st.button("Gerar e Praticar 🚀", use_container_width=True, type="primary"):
        if not api_key:
            st.error("API Key necessária.")
        else:
            with st.spinner(f"Gerando {qtd} questões sobre {tag_alvo}..."):
                questoes = gerar_lote_questoes(sys_brute, dificuldade, cog, api_key, [tag_alvo], qtd)
                if not questoes:
                    st.error("Nenhuma questão gerada. Tente novamente.")
                    return

                fila = []
                for q in questoes:
                    q_id = salvar_questao(sys_brute, dificuldade, q, False, q.get("content_tags", [tag_alvo]),
                                          status="pending", cognitive_order=cog)
                    fila.append({
                        "type": "question",
                        "item": {
                            "id": q_id,
                            "sistema": sys_brute,
                            "dificuldade": dificuldade,
                            "cognitive_order": cog,
                            "question_json": json.dumps(q, ensure_ascii=False),
                        },
                        "source": "targeted",
                    })

                init_session_state()
                st.session_state["fila_estudo"] = fila
                st.session_state["modo_estudo"] = "Targeted"
                st.session_state["targeted_tag"] = tag_alvo
                st.rerun()
