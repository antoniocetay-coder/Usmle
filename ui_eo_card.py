import streamlit as st
from database import update_eo_srs
from session_state import proximo_item_fila


def render_eo_card(item_atual):
    eo = item_atual["item"]

    st.markdown("## 📚 Educational Objective")
    st.markdown("---")
    st.markdown(
        f"<div style='font-size:1.2rem; padding:1.5rem; background:#f0f2f6; "
        f"border-radius:0.5rem; line-height:1.6;'>{eo['text']}</div>",
        unsafe_allow_html=True,
    )

    revealed = st.session_state.get(f"eo_revealed_{eo['id']}", False)

    if not revealed:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.caption("Pense no que você sabe sobre este objetivo. Depois clique em **Revelar**.")
        with col2:
            if st.button("🔍 Revelar Explicação", use_container_width=True):
                st.session_state[f"eo_revealed_{eo['id']}"] = True
                st.rerun()
    else:
        st.markdown("---")
        st.markdown("### Explicação")
        st.info(eo.get("source_explanation", eo["text"]))
        st.caption(f"Sistema: {eo.get('sistema', '—')}  •  "
                   f"{'Revisado ' + str(eo.get('repetitions', 0)) + 'x' if eo.get('repetitions', 0) else 'Nunca revisado'}")

        st.markdown("---")
        st.markdown("### Como foi?")

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            if st.button("❌ Ainda não sei", use_container_width=True):
                update_eo_srs(eo["id"], "again")
                _cleanup(eo["id"])
                proximo_item_fila()
        with col_b:
            if st.button("🔄 Quase lá", use_container_width=True):
                update_eo_srs(eo["id"], "hard")
                _cleanup(eo["id"])
                proximo_item_fila()
        with col_c:
            if st.button("✅ Já dominei", use_container_width=True, type="primary"):
                update_eo_srs(eo["id"], "good")
                _cleanup(eo["id"])
                proximo_item_fila()


def _cleanup(eo_id):
    if f"eo_revealed_{eo_id}" in st.session_state:
        del st.session_state[f"eo_revealed_{eo_id}"]
