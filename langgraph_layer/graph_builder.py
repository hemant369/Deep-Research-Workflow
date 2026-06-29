from langgraph.graph import StateGraph, START, END
from langgraph_layer.state import ResearchState
from langgraph_layer.nodes import (
    planner_node,
    general_node,
    coding_node,
    academic_node,
    merge_node,
    validator_node,
    citation_node,
    synthesizer_node,
    writer_node,
    memory_load_node,
    memory_save_node,
    memory_writer_node
)
from langgraph_layer.router_node import router_node


def check_memory(state: ResearchState) -> str:
    if state.get("memory_hit"):
        print("Memory HIT → skipping agents")
        return "hit"
    print("Memory MISS → running full research")
    return "miss"


def build_graph():
    graph = StateGraph(ResearchState)

    # ── Nodes ────────────────────────────────────────────
    graph.add_node("memory_load",  memory_load_node)
    graph.add_node("memory_writer", memory_writer_node)
    graph.add_node("planner",      planner_node)
    graph.add_node("router",       router_node)
    graph.add_node("academic",     academic_node)
    graph.add_node("general",      general_node)
    graph.add_node("coding",       coding_node)
    graph.add_node("merge",        merge_node)
    graph.add_node("validator",    validator_node)
    graph.add_node("citation",     citation_node)
    graph.add_node("synthesizer",  synthesizer_node)
    graph.add_node("writer",       writer_node)
    graph.add_node("memory_save",  memory_save_node)

    # ── Entry ─────────────────────────────────────────────
    graph.add_edge(START, "memory_load")

    # ── Memory check ──────────────────────────────────────
    graph.add_conditional_edges(
        "memory_load",
        check_memory,
        {
            "hit":  "memory_writer",  # skip all agents
            "miss": "planner"       # run full research
        }
    )

    # ── Research flow ─────────────────────────────────────
    graph.add_edge("planner",     "router")

    graph.add_edge("router",      "academic")
    graph.add_edge("router",      "general")
    graph.add_edge("router",      "coding")

    graph.add_edge("academic",    "merge")
    graph.add_edge("general",     "merge")
    graph.add_edge("coding",      "merge")

    graph.add_edge("merge",       "validator")
    graph.add_edge("validator",   "citation")
    graph.add_edge("citation",    "synthesizer")
    graph.add_edge("synthesizer", "writer")
    graph.add_edge("writer",      "memory_save")

    # ── Exit ──────────────────────────────────────────────
    graph.add_edge("memory_writer", END)

    return graph.compile()