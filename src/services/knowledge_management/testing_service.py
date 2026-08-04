"""testing_service (Phase 27) — the Knowledge Testing page's backend.

Calls the EXISTING, unmodified `KnowledgeService.retrieve_context` (Phase
22) — zero new retrieval logic. This is deliberately a thin formatting
wrapper, not a second retrieval path.
"""

from __future__ import annotations

from typing import Any

from ...services.knowledge.knowledge_service import KnowledgeService


class TestingService:
    def __init__(self, knowledge_service: KnowledgeService | None = None) -> None:
        self._knowledge_service = knowledge_service or KnowledgeService()

    def test_question(
        self, question: str, workspace_id: str, product_filter: list[str] | None = None
    ) -> dict[str, Any]:
        matches, similarities, urls = self._knowledge_service.retrieve_context(
            question, product_filter=product_filter, workspace_id=workspace_id
        )
        confidence = max(similarities) if similarities else 0.0
        return {
            "question": question,
            "chunks": [
                {
                    "content": match.get("chunk_content", ""),
                    "similarity": match.get("similarity", 0.0),
                    "url": match.get("parent_url", ""),
                    "product": match.get("product"),
                }
                for match in matches
            ],
            "sources": urls,
            "confidence": confidence,
        }
