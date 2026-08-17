"""Tests for the AI Copilot's suggest_reply — mocked retrieval/generator,
confirms the draft is never persisted as a message (copilot only drafts)."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.services.escalation.copilot import clean_dangling_citations, recommend_documentation, suggest_reply


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


    def test_conversation_transcript_grounds_summary_requests(self):
        """A "summarize this conversation" request has no KB matches at
        all — without the transcript folded in as evidence, generate()
        would short-circuit to the no-evidence fallback. Confirms the
        transcript is passed through as grounding evidence."""
        knowledge_service = MagicMock()
        knowledge_service.retrieve_context.return_value = ([], [], [])
        response_generator = MagicMock()
        response_generator.generate.return_value = {
            "answer": "The customer asked about pricing; the agent explained the tiers.",
            "citations": [],
        }

        result = suggest_reply(
            workspace_id="w1", question="Summarize this conversation",
            conversation_transcript="Customer: What does it cost?\nAgent: Here are our tiers...",
            knowledge_service=knowledge_service, response_generator=response_generator,
        )

        assert "customer asked about pricing" in result["draft"]
        context = response_generator.generate.call_args.kwargs["context"]
        assert any(item.source_type == "escalation_transcript" for item in context)

    def test_strips_dangling_citation_for_transcript_only_evidence(self):
        knowledge_service = MagicMock()
        knowledge_service.retrieve_context.return_value = ([], [], [])
        response_generator = MagicMock()
        response_generator.generate.return_value = {
            "answer": "Summary text here.\n\n**Sources**\n[1]",
            "citations": [{"url": "", "title": "Conversation so far", "source_type": "escalation_transcript", "score": 1.0}],
        }

        result = suggest_reply(
            workspace_id="w1", question="Summarize this conversation",
            conversation_transcript="Customer: Hi\nAgent: Hello",
            knowledge_service=knowledge_service, response_generator=response_generator,
        )

        assert "Sources" not in result["draft"]
        assert result["citations"] == []


class TestCleanDanglingCitations:
    def test_preserves_real_citations_untouched(self):
        answer = "Answer.\n\n**Sources**\n[1] https://x.com"
        citations = [{"url": "https://x.com"}]
        cleaned_answer, cleaned_citations = clean_dangling_citations(answer, citations)
        assert cleaned_answer == answer
        assert cleaned_citations == citations

    def test_strips_sources_section_when_no_real_citations_remain(self):
        answer = "Here is the summary.\n\n**Sources**\n[1]"
        citations = [{"url": ""}]
        cleaned_answer, cleaned_citations = clean_dangling_citations(answer, citations)
        assert cleaned_answer == "Here is the summary."
        assert cleaned_citations == []


class TestRecommendDocumentation:
    def test_known_product_returns_url(self):
        url = recommend_documentation("SPIDIFY")
        assert url is not None
        assert url.startswith("http")

    def test_unknown_product_returns_none(self):
        assert recommend_documentation("NotAProduct") is None
