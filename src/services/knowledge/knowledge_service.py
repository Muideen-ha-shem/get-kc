from __future__ import annotations

from typing import Any, Sequence

from ...api.services.embeddings import embed_query
from ...api.services.retrieval import retrieve_context as legacy_retrieve_context


class KnowledgeService:
    """Business service for retrieving knowledge-base context."""

    def retrieve_context(
        self,
        question: str,
        product_filter: Sequence[str] | None = None,
    ) -> tuple[list[dict[str, Any]], list[float], list[str]]:
        return legacy_retrieve_context(question, product_filter=product_filter)

    def embed_query(self, question: str) -> list[float]:
        return embed_query(question)
