from langgraph_layer.state import ResearchState


def router_node(state: ResearchState) -> dict:
    """Pass the planner's per-source queries to the parallel search branches."""
    routes = state.get("routes", {})
    return {
        "academic_questions": routes.get("academic", []),
        "general_questions": routes.get("general", []),
        "coding_questions": routes.get("coding", []),
    }
