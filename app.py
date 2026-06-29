import asyncio

import streamlit as st

from langgraph_layer.graph_builder import build_graph


st.set_page_config(
    page_title="Deep Research Agent",
    page_icon="🔎",
    layout="wide"
)

st.title("🔎 Deep Research Agent")

query = st.text_input(
    "Enter your research query"
)

if st.button("Start Research"):

    if not query.strip():
        st.warning("Please enter a research query.")
        st.stop()

    graph = build_graph()

    with st.spinner("Researching..."):

        result = asyncio.run(
            graph.ainvoke(
                {
                    "query": query
                }
            )
        )

    st.success("Research completed!")

    st.markdown("## Report")

    st.markdown(result["report"])

    if "results" in result:
        with st.expander("Evidence"):
            st.json(result["results"])
