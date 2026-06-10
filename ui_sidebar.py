import streamlit as st
from config import *


def render_sidebar():
    with st.sidebar:
        st.header("Configurações")
        try:
            chave_salva = st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            chave_salva = ""
        api_key = st.text_input("Gemini API Key", value=chave_salva, type="password")
        dificuldade = st.selectbox("Difficulty", ["Easy", "Medium", "Hard", "Insane"])
    return api_key, dificuldade
