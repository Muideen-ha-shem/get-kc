from __future__ import annotations

from typing import Any

from ..api.schemas import ChatResponse
from ..services.knowledge import KnowledgeService
from ..services.support import SupportService


class ChatOrchestrator:
    """Coordinates the chat flow while keeping the API layer thin."""

    def __init__(self, knowledge_service: KnowledgeService | None = None, support_service: SupportService | None = None) -> None:
        self.knowledge_service = knowledge_service or KnowledgeService()
        self.support_service = support_service or SupportService()

    def process_request(self, message: str) -> dict[str, Any]:
        matches, _, parent_urls = self.knowledge_service.retrieve_context(message)
        if not matches:
            return {
                "answer": "I couldn’t find enough relevant context in the knowledge base for that question.",
                "sources": [],
            }

        context_text = "\n".join(
            match.get("chunk_content", "") for match in matches if match.get("chunk_content")
        )
        return self.support_service.generate_answer(message, context_text, parent_urls)

    def process_request_response(self, message: str) -> ChatResponse:
        result = self.process_request(message)
        return ChatResponse(**result)


chat_orchestrator = ChatOrchestrator()
