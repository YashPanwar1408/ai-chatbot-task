"""LangGraph chat RAG workflow."""

from langgraph.graph import END, START, StateGraph

from app.graph.edges import documents_relevant
from app.graph.nodes import rag as rag_nodes
from app.graph.state import ChatGraphState


def build_chat_graph():
    """retrieve -> grade -> generate -> cite with conversation memory."""
    graph = StateGraph(ChatGraphState)

    graph.add_node("load_memory", rag_nodes.load_memory)
    graph.add_node("rewrite_query", rag_nodes.rewrite_query)
    graph.add_node("retrieve", rag_nodes.retrieve)
    graph.add_node("grade_documents", rag_nodes.grade_documents)
    graph.add_node("generate", rag_nodes.generate)
    graph.add_node("cite", rag_nodes.cite)
    graph.add_node("save_memory", rag_nodes.save_memory)

    graph.add_edge(START, "load_memory")
    graph.add_edge("load_memory", "rewrite_query")
    graph.add_edge("rewrite_query", "retrieve")
    graph.add_edge("retrieve", "grade_documents")

    graph.add_conditional_edges(
        "grade_documents",
        documents_relevant,
        {
            "sufficient": "generate",
            "insufficient": "retrieve",
        },
    )
    graph.add_edge("generate", "cite")
    graph.add_edge("cite", "save_memory")
    graph.add_edge("save_memory", END)

    return graph.compile()
