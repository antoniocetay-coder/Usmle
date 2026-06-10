import streamlit as st
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
from knowledge_graph import KnowledgeGraph
from centrality import CentralityAnalyzer
from student_graph import StudentGraph
from analytics import get_tag_stats
from database import search_eos, get_eo_count_by_system


@st.cache_data
def _load_taxonomy():
    with open("taxonomy.json", "r", encoding="utf-8") as f:
        return json.load(f)


def _build_concept_map(taxonomy):
    concept_to_systems = {}
    system_disciplines = {}
    for sys_name, disciplines in taxonomy.items():
        system_disciplines.setdefault(sys_name, {})
        for disc_name, tags in disciplines.items():
            if isinstance(tags, list):
                system_disciplines[sys_name][disc_name] = len(tags)
                for t in tags:
                    concept_to_systems.setdefault(t, []).append((sys_name, disc_name))
    return concept_to_systems, system_disciplines


def _load_pipeline():
    kg = KnowledgeGraph()
    centrality = CentralityAnalyzer(kg)
    sg = StudentGraph(kg, centrality)
    sg.load_from_db(get_tag_stats())
    return kg, centrality, sg


def _mastery_color(mastery, has_data=False):
    if not has_data or mastery == 0.0:
        return "#cccccc"
    if mastery >= 0.80:
        return "#2ecc71"
    if mastery >= 0.40:
        return "#f1c40f"
    return "#e74c3c"


def _render_graph(kg, sg, centrality, nodes, title):
    if len(nodes) == 0:
        st.info("No concepts in this selection.")
        return

    subgraph = kg.graph.subgraph(nodes).copy()
    if subgraph.number_of_nodes() == 0:
        st.info("No concepts to display.")
        return

    pos = nx.spring_layout(subgraph, k=2.5, iterations=50, seed=42)

    colors = []
    sizes = []
    for node in subgraph.nodes:
        state = sg.get_state(node)
        m = state.mastery if state else 0
        has_data = bool(state and (state.attempts > 0 or state.mastery > 0))
        colors.append(_mastery_color(m, has_data))
        deg = centrality.degree(node)
        sizes.append(max(50, min(400, 100 + deg * 500)))

    fig, ax = plt.subplots(figsize=(14, 10))
    nx.draw_networkx_edges(subgraph, pos, alpha=0.15, arrows=True,
                           arrowstyle="-|>", arrowsize=10, ax=ax)
    nx.draw_networkx_nodes(subgraph, pos, node_color=colors,
                           node_size=sizes, alpha=0.85, ax=ax)
    nx.draw_networkx_labels(subgraph, pos, font_size=7, ax=ax)

    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#2ecc71", label="Mastered (≥ 80%)"),
        Patch(facecolor="#f1c40f", label="Learning (40–80%)"),
        Patch(facecolor="#e74c3c", label="Weak (< 40%)"),
        Patch(facecolor="#cccccc", label="Unseen"),
    ]
    ax.legend(handles=legend_elements, loc="upper right", fontsize=9)
    ax.set_title(f"{title}  ({len(nodes)} nodes)", fontsize=14)
    ax.axis("off")
    fig.tight_layout()
    st.pyplot(fig)


def render_explorer():
    st.subheader("Knowledge Graph Explorer")

    taxonomy = _load_taxonomy()
    concept_map, system_stats = _build_concept_map(taxonomy)
    kg, centrality, sg = _load_pipeline()

    system_names = sorted(taxonomy.keys())

    # ── Gap Analysis ───────────────────────────────────────────────────
    with st.expander("📊 Gap Analysis by System", expanded=True):
        rows = []
        for sys_name in system_names:
            disc_names = list(taxonomy[sys_name].keys())
            total_in_system = 0
            seen = 0
            mastered = 0
            weak = 0
            for disc_name in disc_names:
                tags = taxonomy[sys_name][disc_name]
                if not isinstance(tags, list):
                    continue
                for t in tags:
                    total_in_system += 1
                    state = sg.get_state(t)
                    if state and (state.attempts > 0 or state.mastery > 0):
                        seen += 1
                    if state and state.mastery >= 0.80:
                        mastered += 1
                    if state and 0 < state.mastery < 0.40:
                        weak += 1

            unseen = total_in_system - seen
            pct = f"{seen / total_in_system * 100:.1f}%" if total_in_system else "0%"
            rows.append({
                "System": sys_name,
                "Total": total_in_system,
                "Seen": seen,
                "Unseen": unseen,
                "Mastered (≥80%)": mastered,
                "Weak (<40%)": weak,
                "% Seen": pct,
            })

        st.dataframe(rows, use_container_width=True, hide_index=True)

    # ── System Quick Stats ─────────────────────────────────────────────
    st.subheader("System Overview")
    cols = st.columns(len(system_names))
    for i, sys_name in enumerate(system_names):
        row = rows[i]
        with cols[i % len(cols)]:
            seen_pct = row["% Seen"]
            st.metric(
                sys_name.replace("_", " "),
                row["Seen"],
                f"{row['Total']} total  ({seen_pct})",
            )

    # ── Educational Objectives Browser ─────────────────────────────────
    with st.expander("📚 Educational Objectives Bank", expanded=False):
        eo_counts = get_eo_count_by_system()
        if eo_counts:
            st.caption("EOs por sistema: " + " | ".join(f"{k}: {v}" for k, v in sorted(eo_counts.items())))
        else:
            st.caption("Nenhum EO registrado ainda. Responda questões para gerar EOs.")

        col_eo1, col_eo2 = st.columns([2, 1])
        with col_eo1:
            eo_query = st.text_input("Buscar EO", placeholder="Ex: pericarditis, aortic stenosis...", key="eo_search")
        with col_eo2:
            eo_sys_filter = st.selectbox("Sistema", ["All"] + sorted(eo_counts.keys()) if eo_counts else ["All"],
                                         key="eo_sys_filter")

        eo_results = search_eos(
            query=eo_query or "",
            sistema=None if eo_sys_filter == "All" else eo_sys_filter,
            limit=30
        )

        if not eo_results:
            st.info("Nenhum EO encontrado.")
        else:
            st.write(f"{len(eo_results)} EOs encontrados")
            for eo in eo_results:
                with st.container(border=True):
                    st.markdown(f"**{eo['text']}**")
                    tags_str = ""
                    if eo.get("tags_json"):
                        try:
                            tags = json.loads(eo["tags_json"])
                            tags_str = " | ".join(tags[:5])
                            if len(tags) > 5:
                                tags_str += " ..."
                        except json.JSONDecodeError:
                            pass
                    st.caption(f"{eo.get('sistema', '—')}  •  "
                               f"{'Revisado ' + str(eo.get('repetitions', 0)) + 'x' if eo.get('repetitions', 0) else 'Não revisado'}"
                               f"{'  •  ' + tags_str if tags_str else ''}")

    # ── Colored Graph ──────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Concept Map")

    sel_system = st.selectbox("Filter by system", ["All"] + system_names)

    if sel_system == "All":
        all_disciplines = ["All"]
    else:
        all_disciplines = ["All"] + sorted(taxonomy[sel_system].keys())

    sel_discipline = st.selectbox("Filter by discipline", all_disciplines)

    if st.button("Render Graph", type="primary", use_container_width=True):
        if sel_system == "All":
            nodes = list(kg.graph.nodes)
        else:
            filtered = set()
            for disc_name, tags in taxonomy[sel_system].items():
                if isinstance(tags, list):
                    if sel_discipline == "All" or disc_name == sel_discipline:
                        filtered.update(tags)
            nodes = [n for n in filtered if kg.has_concept(n)]

        with st.spinner("Rendering graph..."):
            _render_graph(kg, sg, centrality, nodes,
                          f"{sel_system} — {sel_discipline}" if sel_discipline != "All" else sel_system)
