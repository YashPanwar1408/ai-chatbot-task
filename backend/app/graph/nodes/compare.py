"""Compare graph node stubs."""

from app.graph.state import CompareGraphState


async def load_creator_context(state: CompareGraphState) -> dict:
    return {"phase": "load_creator_context"}


async def fetch_platform_stats(state: CompareGraphState) -> dict:
    return {"phase": "fetch_platform_stats", "platform_aggregates": {}}


async def plan_compare_queries(state: CompareGraphState) -> dict:
    return {"phase": "plan_compare_queries", "sub_queries": []}


async def parallel_retrieve(state: CompareGraphState) -> dict:
    return {"phase": "parallel_retrieve"}


async def merge_retrieval(state: CompareGraphState) -> dict:
    return {"phase": "merge_retrieval"}


async def expand_retrieval(state: CompareGraphState) -> dict:
    return {"phase": "expand_retrieval"}


async def synthesize_compare(state: CompareGraphState) -> dict:
    return {"phase": "synthesize_compare", "draft_answer": ""}


async def fact_check_citations(state: CompareGraphState) -> dict:
    return {"phase": "fact_check_citations"}


async def format_structured_output(state: CompareGraphState) -> dict:
    return {"phase": "format_structured_output", "structured_output": {}}
