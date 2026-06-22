from langgraph.graph import StateGraph, START, END
from langgraph_layer.state import ResearchState
from langgraph_layer.nodes import planner_node, research_node, merge_node, validator_node, citation_node, synthesizer_node, writer_node


def build_graph():

    graph = StateGraph(
        ResearchState
    )

    graph.add_node("planner", planner_node)
    graph.add_node("research", research_node)
    graph.add_node("merge", merge_node)
    graph.add_node("validator", validator_node)
    graph.add_node("citation", citation_node)
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_node("writer", writer_node)


    graph.add_edge(START, "planner")
    graph.add_edge("planner", "research")
    graph.add_edge("research", "merge")
    graph.add_edge("merge", "validator")
    graph.add_edge("validator", "citation")
    graph.add_edge("citation", "synthesizer")
    graph.add_edge("synthesizer", "writer")
    graph.add_edge("writer", END)

    return graph.compile()
