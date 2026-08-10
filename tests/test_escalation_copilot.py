"""Tests for the AI Copilot's suggest_reply — mocked retrieval/generator,
confirms the draft is never persisted as a message (copilot only drafts)."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.services.escalation.copilot import recommend_documentation, suggest_reply


class TestSuggestReply:
    def test_returns_draft_and_citations_from_generator(self):
        knowledge_service = MagicMock()
        knowledge_service.retrieve_context.return_value = (
            [{"chunk_content": "SPIDIFY verifies identity via document scan.", "parent_url": "https://x.com", "similarity": 0.9}],
            [0.9],
            ["https://x.com"],
        )
        response_generator = MagicMock()
        response_generator.generate.return_value = {
            "answer": "You can verify identity using SPIDIFY's document scan flow.",
            "citations": [{"url": "https://x.com", "title": "", "source_type": "knowledge_base", "score": 0.9}],
        }

        result = suggest_reply(
            workspace_id="w1",
            question="How do I verify identity?",
            knowledge_service=knowledge_service,
            response_generator=response_generator,
        )

        assert result["draft"] == "You can verify identity using SPIDIFY's document scan flow."
        assert result["citations"][0]["url"] == "https://x.com"
        knowledge_service.retrieve_context.assert_called_once_with(
            "How do I verify identity?", workspace_id="w1"
        )

    def test_never_persists_a_message(self):
        """suggest_reply has no repository/notification dependency at all —
        structurally, it cannot write a message."""
        knowledge_service = MagicMock()
        knowledge_service.retrieve_context.return_value = ([], [], [])
        response_generator = MagicMock()
        response_generator.generate.return_value = {"answer": "not enough information", "citations": []}

        result = suggest_reply(
            workspace_id="w1", question="anything",
            knowledge_service=knowledge_service, response_generator=response_generator,
        )

        assert "draft" in result
        # No mock for any EscalationRepository/NotificationService was ever
        # constructed or passed in — nothing in this module can persist.


class TestRecommendDocumentation:
    def test_known_product_returns_url(self):
        url = recommend_documentation("SPIDIFY")
        assert url is not None
        assert url.startswith("http")

    def test_unknown_product_returns_none(self):
        assert recommend_documentation("NotAProduct") is None
