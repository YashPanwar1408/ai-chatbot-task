"""Application metrics (stub)."""

from app.domain.exceptions import NotImplementedFeatureError


def record_retrieval_latency(latency_ms: float) -> None:
    raise NotImplementedFeatureError("record_retrieval_latency")


def record_llm_token_usage(input_tokens: int, output_tokens: int) -> None:
    raise NotImplementedFeatureError("record_llm_token_usage")
