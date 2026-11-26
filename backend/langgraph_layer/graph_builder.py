from langgraph.graph import END, START, StateGraph

from langgraph_layer.nodes import (
    academic_node,
    citation_node,
    coding_node,
    general_node,
    memory_load_node,
    memory_save_node,
    merge_node,
    planner_node,
    reflect_node,
    reflect_route,
    router_node,
    synthesizer_node,
    validator_node,
    writer_node,
)
from langgraph_layer.state import ResearchState


def memory_route(state: ResearchState) -> str:
    return "hit" if state.get("memory_hit") else "miss"


def build_graph():
    graph = StateGraph(ResearchState)

    # Each function below is one visible step in the research pipeline.
    graph.add_node("memory_load", memory_load_node)
    graph.add_node("planner", planner_node)
    graph.add_node("router", router_node)
    graph.add_node("academic", academic_node)
    graph.add_node("general", general_node)
    graph.add_node("coding", coding_node)
    graph.add_node("merge", merge_node)
    graph.add_node("validator", validator_node)
    graph.add_node("citation", citation_node)
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_node("reflect", reflect_node)
    graph.add_node("writer", writer_node)
    graph.add_node("memory_save", memory_save_node)

    graph.add_edge(START, "memory_load")

    graph.add_conditional_edges(
        "memory_load",
        memory_route,
        {
            "hit": END,
            "miss": "planner",
        },
    )

    # Plan and route search queries.
    graph.add_edge("planner", "router")

    # LangGraph runs these independent MCP searches in parallel.
    graph.add_edge("router", "academic")
    graph.add_edge("router", "general")
    graph.add_edge("router", "coding")

    # Combine evidence and synthesize what is known so far.
    graph.add_edge("academic", "merge")
    graph.add_edge("general", "merge")
    graph.add_edge("coding", "merge")

    graph.add_edge("merge", "validator")
    graph.add_edge("validator", "citation")
    graph.add_edge("citation", "synthesizer")
    graph.add_edge("synthesizer", "reflect")

    # Deep-research loop: reflect on knowledge gaps and either search again
    # with follow-up queries or move on to writing the report.
    graph.add_conditional_edges(
        "reflect",
        reflect_route,
        {
            "continue": "router",
            "done": "writer",
        },
    )

    graph.add_edge("writer", "memory_save")
    graph.add_edge("memory_save", END)

    return graph.compile()
