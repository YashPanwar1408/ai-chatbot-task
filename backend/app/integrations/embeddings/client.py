"""BGE embedding client using sentence-transformers."""

from __future__ import annotations

import asyncio
from functools import lru_cache

from app.config.settings import Settings, get_settings
from app.domain.exceptions import IntegrationError

QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
DOCUMENT_PREFIX = "Represent this document for retrieval: "


@lru_cache
def _load_model(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise IntegrationError(
            "embeddings",
            "sentence-transformers is not installed",
        ) from exc

    model_id = "BAAI/bge-small-en-v1.5" if "bge-large" in model_name else model_name
    return SentenceTransformer(model_id)

 
class EmbeddingClient:
    """Local BGE embeddings with async offloading."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self.model_name = self._settings.embedding_model_name
        self.batch_size = self._settings.embedding_batch_size
        self._model = None

    def _get_model(self):
        if self._model is None:
            self._model = _load_model(self.model_name)
        return self._model

    def _encode_documents(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        prefixed = [f"{DOCUMENT_PREFIX}{text}" for text in texts]
        vectors = model.encode(
            prefixed,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [vector.tolist() for vector in vectors]

    def _encode_query(self, query: str) -> list[float]:
        model = self._get_model()
        vector = model.encode(
            f"{QUERY_PREFIX}{query}",
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vector.tolist()

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            return await asyncio.to_thread(self._encode_documents, texts)
        except Exception as exc:
            raise IntegrationError("embeddings", str(exc)) from exc

    async def embed_query(self, query: str) -> list[float]:
        try:
            return await asyncio.to_thread(self._encode_query, query)
        except Exception as exc:
            raise IntegrationError("embeddings", str(exc)) from exc


@lru_cache
def get_embedding_client() -> EmbeddingClient:
    return EmbeddingClient()
