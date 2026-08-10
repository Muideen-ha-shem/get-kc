"""Tests for FeedbackService — public feature, no RLS, Supabase mocked."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.services.feedback.feedback_service import FeedbackService


def _row(**overrides):
    base = {
        "id": "f1", "question": "What is SPIDIFY?", "answer": "SPIDIFY is...",
        "rating": "helpful", "comment": None, "created_at": None,
    }
    base.update(overrides)
    return base


class TestFeedbackService:
    def test_submit_inserts_and_returns_row(self):
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.return_value.data = [_row()]
        service = FeedbackService(client=client)

        feedback = service.submit("What is SPIDIFY?", "SPIDIFY is...", "helpful")

        assert feedback.rating == "helpful"
        payload = client.table.return_value.insert.call_args[0][0]
        assert payload["user_id"] is None

    def test_submit_records_optional_context(self):
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.return_value.data = [
            _row(comment="Very helpful, thanks!")
        ]
        service = FeedbackService(client=client)

        service.submit(
            "q", "a", "helpful", comment="Very helpful, thanks!",
            user_id="u1", session_id="s1", conversation_id="c1",
        )

        payload = client.table.return_value.insert.call_args[0][0]
        assert payload["user_id"] == "u1"
        assert payload["session_id"] == "s1"
        assert payload["conversation_id"] == "c1"
        assert payload["comment"] == "Very helpful, thanks!"

    def test_not_helpful_rating_accepted(self):
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.return_value.data = [_row(rating="not_helpful")]
        service = FeedbackService(client=client)

        feedback = service.submit("q", "a", "not_helpful")

        assert feedback.rating == "not_helpful"
