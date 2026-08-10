"""Tests for ConversationRepository (mocked Supabase) and ConversationService
(mocked repository)."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.services.conversation.conversation_repository import ConversationRepository
from src.services.conversation.conversation_service import ConversationService
from src.services.workspace.workspace_models import DEFAULT_WORKSPACE_ID


def _conv_row(**overrides):
    base = {"id": "c1", "user_id": "u1", "title": "New conversation", "created_at": None, "updated_at": None}
    base.update(overrides)
    return base


class TestConversationRepository:
    def test_create_conversation(self):
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.return_value.data = [_conv_row()]
        repo = ConversationRepository(client=client)

        row = repo.create_conversation("u1", title="New conversation")

        assert row.id == "c1"
        client.table.return_value.insert.assert_called_once_with(
            {"user_id": "u1", "title": "New conversation", "workspace_id": DEFAULT_WORKSPACE_ID}
        )

    def test_list_conversations_applies_search_filter(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.ilike.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            _conv_row()
        ]
        repo = ConversationRepository(client=client)

        rows = repo.list_conversations("u1", search="SPIDIFY")

        assert len(rows) == 1
        client.table.return_value.select.return_value.eq.return_value.ilike.assert_called_once_with(
            "title", "%SPIDIFY%"
        )

    def test_list_conversations_without_search_skips_ilike(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        repo = ConversationRepository(client=client)

        repo.list_conversations("u1")

        client.table.return_value.select.return_value.eq.return_value.ilike.assert_not_called()

    def test_get_conversation_not_found_returns_none(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        repo = ConversationRepository(client=client)

        assert repo.get_conversation("c1", "u1") is None

    def test_delete_conversation_returns_true_when_deleted(self):
        client = MagicMock()
        client.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value.data = [_conv_row()]
        repo = ConversationRepository(client=client)

        assert repo.delete_conversation("c1", "u1") is True

    def test_delete_conversation_returns_false_when_not_owned(self):
        client = MagicMock()
        client.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        repo = ConversationRepository(client=client)

        assert repo.delete_conversation("c1", "u1") is False


class TestConversationService:
    def test_start_conversation_titles_from_first_message(self):
        repo = MagicMock()
        repo.create_conversation.return_value = _conv_row(title="Tell me about SPIDIFY")
        service = ConversationService(repository=repo)

        service.start_conversation("u1", "Tell me about SPIDIFY")

        repo.create_conversation.assert_called_once_with(
            "u1", title="Tell me about SPIDIFY", access_token=None, workspace_id=DEFAULT_WORKSPACE_ID
        )

    def test_list_conversations_forwards_search_to_repository(self):
        repo = MagicMock()
        repo.list_conversations.return_value = []
        service = ConversationService(repository=repo)

        service.list_conversations("u1", search="SPIDIFY")

        repo.list_conversations.assert_called_once_with(
            "u1", access_token=None, search="SPIDIFY", workspace_id=None
        )

    def test_start_conversation_long_first_message_truncated(self):
        repo = MagicMock()
        repo.create_conversation.return_value = _conv_row()
        service = ConversationService(repository=repo)
        long_message = "word " * 30

        service.start_conversation("u1", long_message)

        title = repo.create_conversation.call_args.kwargs["title"]
        assert len(title) <= 61
        assert title.endswith("…")

    def test_record_turn_persists_both_messages_when_owned(self):
        repo = MagicMock()
        repo.get_conversation.return_value = _conv_row()
        service = ConversationService(repository=repo)

        result = service.record_turn("c1", "u1", "hi", "hello", sources=["https://x.com"])

        assert result is True
        assert repo.add_message.call_count == 2
        repo.touch_conversation.assert_called_once_with("c1", "u1", access_token=None)

    def test_record_turn_noop_when_not_owned(self):
        repo = MagicMock()
        repo.get_conversation.return_value = None
        service = ConversationService(repository=repo)

        result = service.record_turn("c1", "u1", "hi", "hello")

        assert result is False
        repo.add_message.assert_not_called()

    def test_get_messages_returns_none_when_not_owned(self):
        repo = MagicMock()
        repo.get_conversation.return_value = None
        service = ConversationService(repository=repo)

        assert service.get_messages("c1", "u1") is None
