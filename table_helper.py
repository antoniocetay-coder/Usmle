import streamlit as st


def dataframe(rows, use_container_width=True, hide_index=True):
    if not rows:
        st.markdown("<p style='color:#888;'>No data</p>", unsafe_allow_html=True)
        return
    keys = list(rows[0].keys())
    thead = "".join(f"<th style='padding:6px 10px;text-align:left;border-bottom:2px solid #ddd;font-weight:600;white-space:nowrap;'>{k}</th>" for k in keys)
    trows = ""
    for r in rows:
        trows += "<tr>" + "".join(
            f"<td style='padding:4px 10px;border-bottom:1px solid #eee;'>{r.get(k, '')}</td>"
            for k in keys
        ) + "</tr>"
    html = (
        f"<div style='overflow-x:auto;max-height:500px;overflow-y:auto;'>"
        f"<table style='width:100%;border-collapse:collapse;font-size:14px;'>"
        f"<thead>{thead}</thead>"
        f"<tbody>{trows}</tbody>"
        f"</table></div>"
    )
    st.markdown(html, unsafe_allow_html=True)
