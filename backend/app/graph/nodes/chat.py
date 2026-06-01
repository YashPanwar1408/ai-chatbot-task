"""Chat graph node stubs."""

from app.graph.state import ChatGraphState
from app.graph.nodes.shared import grade_documents as grade_documents_node


async def rewrite_query(state: ChatGraphState) -> dict:
    return {"phase": "rewrite_query", "rewritten_query": state.get("user_query", "")}


async def retrieve(state: ChatGraphState) -> dict:
    return {"phase": "retrieve"}


grade_documents = grade_documents_node


async def generate(state: ChatGraphState) -> dict:
    return {"phase": "generate", "draft_answer": ""}
