import asyncio

import streamlit as st

from backend.langgraph_layer.graph_builder import build_graph


STAGE_LABELS = {
    "memory_load": "Checking memory",
    "memory_writer": "Loading cached report",
    "planner": "Planning search queries",
    "router": "Routing queries",
    "academic": "Searching academic sources",
    "general": "Searching the web",
    "coding": "Searching GitHub",
    "merge": "Merging and deduplicating",
    "validator": "Validating evidence",
    "citation": "Creating passage citations",
    "synthesizer": "Synthesizing findings",
    "writer": "Writing report",
    "memory_save": "Saving report",
}


async def run_research(graph, payload, progress_bar, status_box, log_box):
    final_state = dict(payload)
    completed = []
    total = len(STAGE_LABELS)

    async for update in graph.astream(payload, stream_mode="updates"):
        for node_name, node_update in update.items():
            completed.append(node_name)
            if isinstance(node_update, dict):
                final_state.update(node_update)

            label = STAGE_LABELS.get(node_name, node_name)
            progress_bar.progress(min(len(completed) / total, 1.0))
            status_box.info(f"Running: {label}")
            log_box.markdown(
                "\n".join(
                    f"- {STAGE_LABELS.get(name, name)}"
                    for name in completed
                )
            )

    progress_bar.progress(1.0)
    status_box.success("Research completed")
    return final_state


st.set_page_config(
    page_title="Deep Research Agent",
    page_icon="DR",
    layout="wide"
)

st.title("Deep Research Agent")

query = st.text_input(
    "Enter your research query"
)

use_memory = st.checkbox(
    "Use cached result when available",
    value=False
)

if st.button("Start Research"):

    if not query.strip():
        st.warning("Please enter a research query.")
        st.stop()

    graph = build_graph()
    progress_bar = st.progress(0)
    status_box = st.empty()

    with st.expander("Progress", expanded=True):
        log_box = st.empty()

    result = asyncio.run(
        run_research(
            graph,
            {
                "query": query,
                "use_memory": use_memory
            },
            progress_bar,
            status_box,
            log_box,
        )
    )

    st.markdown("## Report")
    st.markdown(result["report"])

    if "results" in result:
        with st.expander("Evidence"):
            st.json(result["results"])
