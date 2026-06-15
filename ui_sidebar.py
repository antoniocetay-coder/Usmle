import streamlit as st
from config import MODELOS_DISPONIVEIS

def render_sidebar():
    with st.sidebar:
        st.header("Configurações")

        try:
            chave_salva = st.secrets.get("OPENROUTER_API_KEY", "")
        except Exception:
            chave_salva = ""

        api_key = st.text_input("OpenRouter API Key", value=chave_salva, type="password")

        modelo_nome = st.selectbox("Modelo", list(MODELOS_DISPONIVEIS.keys()))
        modelos = MODELOS_DISPONIVEIS[modelo_nome]
        st.session_state["model_qbank"]     = modelos["qbank"]
        st.session_state["model_flashcard"] = modelos["flashcard"]

        return api_key