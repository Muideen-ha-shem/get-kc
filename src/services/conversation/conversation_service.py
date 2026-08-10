"""ConversationService — conversation lifecycle for authenticated users.

Sits behind the existing ``/chat`` contract (Workstream 4): the chat route
still returns the same ``ChatResponse`` shape it always has, this service
is only ever invoked *in addition to* that, never instead of it, and only
when the caller is authenticated and passes a conversation_id.

Every method accepts the caller's ``access_token`` and forwards it to
``ConversationRepository`` — required for Row Level Security to resolve
``auth.uid()`` on the underlying tables (see the repository's docstring).
"""

from __future__ import annotations

import logging
from typing import Any

from ...services.workspace.workspace_models import DEFAULT_WORKSPACE_ID
from ...shared.logging import get_logger
from .conversation_repository import ConversationRepository, ConversationRow, MessageRow

logger: logging.Logger = get_logger(__name__)

_TITLE_MAX_LEN = 60


class ConversationService:
    def __init__(self, repository: ConversationRepository | None = None) -> None:
        self._repo = repository or ConversationRepository()

    def start_conversation(
        self,
        user_id: str,
        first_message: str | None = None,
        access_token: str | None = None,
        workspace_id: str = DEFAULT_WORKSPACE_ID,
    ) -> ConversationRow:
        title = self._title_from_message(first_message) if first_message else "New conversation"
        return self._repo.create_conversation(
            user_id, title=title, access_token=access_token, workspace_id=workspace_id
        )

    def get_conversation(
        self,
        conversation_id: str,
        user_id: str,
        access_token: str | None = None,
        workspace_id: str | None = None,
    ) -> ConversationRow | None:
        return self._repo.get_conversation(
            conversation_id, user_id, access_token=access_token, workspace_id=workspace_id
        )

    def list_conversations(
        self,
        user_id: str,
        access_token: str | None = None,
        search: str | None = None,
        workspace_id: str | None = None,
    ) -> list[ConversationRow]:
        return self._repo.list_conversations(
            user_id, access_token=access_token, search=search, workspace_id=workspace_id
        )

    def rename_conversation(
        self, conversation_id: str, user_id: str, title: str, access_token: str | None = None
    ) -> ConversationRow | None:
        return self._repo.rename_conversation(
            conversation_id, user_id, title.strip()[:200] or "New conversation", access_token=access_token
        )

    def delete_conversation(self, conversation_id: str, user_id: str, access_token: str | None = None) -> bool:
        return self._repo.delete_conversation(conversation_id, user_id, access_token=access_token)

    def get_messages(
        self, conversation_id: str, user_id: str, access_token: str | None = None
    ) -> list[MessageRow] | None:
        if self._repo.get_conversation(conversation_id, user_id, access_token=access_token) is None:
            return None
        return self._repo.list_messages(conversation_id, access_token=access_token)

    def record_turn(
        self,
        conversation_id: str,
        user_id: str,
        question: str,
        answer: str,
        sources: list[str] | None = None,
        next_actions: list[dict[str, Any]] | None = None,
        access_token: str | None = None,
    ) -> bool:
        """Persist a user question + assistant answer as two messages.

        Returns False (no-op) if the conversation doesn't exist or isn't
        owned by ``user_id`` — callers must not let a persistence failure
        break the chat response itself.
        """
        if self._repo.get_conversation(conversation_id, user_id, access_token=access_token) is None:
            logger.info("record_turn: conversation %s not found for user", conversation_id)
            return False
        self._repo.add_message(conversation_id, "user", question, access_token=access_token)
        self._repo.add_message(
            conversation_id,
            "assistant",
            answer,
            citations=sources or [],
            metadata={"next_actions": next_actions or []},
            access_token=access_token,
        )
        self._repo.touch_conversation(conversation_id, user_id, access_token=access_token)
        return True

    @staticmethod
    def _title_from_message(message: str) -> str:
        title = " ".join(message.strip().split())
        if len(title) <= _TITLE_MAX_LEN:
            return title or "New conversation"
        return title[:_TITLE_MAX_LEN].rsplit(" ", 1)[0] + "…"
