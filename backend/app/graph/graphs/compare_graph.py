"""LangGraph compare workflow skeleton."""

from langgraph.graph import END, START, StateGraph

from app.graph.edges import compare_has_enough_context
from app.graph.nodes import compare as compare_nodes
from app.graph.nodes.shared import grade_documents
from app.graph.state import CompareGraphState


def build_compare_graph():
    """Build YouTube Shorts vs Instagram Reels compare graph."""
    graph = StateGraph(CompareGraphState)

    graph.add_node("load_creator_context", compare_nodes.load_creator_context)
    graph.add_node("fetch_platform_stats", compare_nodes.fetch_platform_stats)
    graph.add_node("plan_compare_queries", compare_nodes.plan_compare_queries)
    graph.add_node("parallel_retrieve", compare_nodes.parallel_retrieve)
    graph.add_node("merge_retrieval", compare_nodes.merge_retrieval)
    graph.add_node("grade_documents", grade_documents)
    graph.add_node("expand_retrieval", compare_nodes.expand_retrieval)
    graph.add_node("synthesize_compare", compare_nodes.synthesize_compare)
    graph.add_node("fact_check_citations", compare_nodes.fact_check_citations)
    graph.add_node("format_structured_output", compare_nodes.format_structured_output)

    graph.add_edge(START, "load_creator_context")
    graph.add_edge("load_creator_context", "fetch_platform_stats")
    graph.add_edge("fetch_platform_stats", "plan_compare_queries")
    graph.add_edge("plan_compare_queries", "parallel_retrieve")
    graph.add_edge("parallel_retrieve", "merge_retrieval")
    graph.add_edge("merge_retrieval", "grade_documents")

    graph.add_conditional_edges(
        "grade_documents",
        compare_has_enough_context,
        {
            "sufficient": "synthesize_compare",
            "insufficient": "expand_retrieval",
        },
    )
    graph.add_edge("expand_retrieval", "parallel_retrieve")
    graph.add_edge("synthesize_compare", "fact_check_citations")
    graph.add_edge("fact_check_citations", "format_structured_output")
    graph.add_edge("format_structured_output", END)

    return graph.compile()
