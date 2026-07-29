"""ConversationRepository — raw persistence for conversations/messages.

Every query is explicitly scoped by ``user_id`` (defense in depth
regardless of whether the configured Supabase key is anon+RLS or
service-role) — the same ownership-at-the-query-layer pattern already used
by the rest of this codebase's Supabase access (see
``document_service.py``).

Both tables have Row Level Security keyed on ``auth.uid()``, so every call
also needs the caller's access token (see ``get_authenticated_client``) —
the module's own anon-key client alone cannot read/write these tables.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from supabase import Client

from ...sb import get_authenticated_client, get_client
from ...shared.logging import get_logger

logger: logging.Logger = get_logger(__name__)

_CONVERSATIONS = "conversations"
_MESSAGES = "conversation_messages"


@dataclass(frozen=True)
class ConversationRow:
    id: str
    user_id: str
    title: str
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "ConversationRow":
        return cls(**{field: row.get(field) for field in cls.__dataclass_fields__})


@dataclass(frozen=True)
class MessageRow:
    id: str
    conversation_id: str
    role: str
    content: str
    citations: list[Any]
    metadata: dict[str, Any]
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "MessageRow":
        return cls(**{field: row.get(field) for field in cls.__dataclass_fields__})


class ConversationRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def _client_for(self, access_token: str | None) -> Client:
        return get_authenticated_client(access_token) if access_token else self._client

    def create_conversation(
        self, user_id: str, title: str = "New conversation", access_token: str | None = None
    ) -> ConversationRow:
        response = (
            self._client_for(access_token)
            .table(_CONVERSATIONS)
            .insert({"user_id": user_id, "title": title})
            .execute()
        )
        return ConversationRow.from_row(response.data[0])

    def get_conversation(
        self, conversation_id: str, user_id: str, access_token: str | None = None
    ) -> ConversationRow | None:
        response = (
            self._client_for(access_token)
            .table(_CONVERSATIONS)
            .select("*")
            .eq("id", conversation_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        return ConversationRow.from_row(response.data[0])

    def list_conversations(
        self, user_id: str, limit: int = 50, access_token: str | None = None, search: str | None = None
    ) -> list[ConversationRow]:
        query = (
            self._client_for(access_token)
            .table(_CONVERSATIONS)
            .select("*")
            .eq("user_id", user_id)
        )
        if search:
            query = query.ilike("title", f"%{search}%")
        response = query.order("updated_at", desc=True).limit(limit).execute()
        return [ConversationRow.from_row(row) for row in response.data]

    def rename_conversation(
        self, conversation_id: str, user_id: str, title: str, access_token: str | None = None
    ) -> ConversationRow | None:
        from datetime import datetime, timezone

        response = (
            self._client_for(access_token)
            .table(_CONVERSATIONS)
            .update({"title": title, "updated_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", conversation_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not response.data:
            return None
        return ConversationRow.from_row(response.data[0])

    def touch_conversation(self, conversation_id: str, user_id: str, access_token: str | None = None) -> None:
        from datetime import datetime, timezone

        self._client_for(access_token).table(_CONVERSATIONS).update(
            {"updated_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", conversation_id).eq("user_id", user_id).execute()

    def delete_conversation(self, conversation_id: str, user_id: str, access_token: str | None = None) -> bool:
        response = (
            self._client_for(access_token)
            .table(_CONVERSATIONS)
            .delete()
            .eq("id", conversation_id)
            .eq("user_id", user_id)
            .execute()
        )
        return bool(response.data)

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        citations: list[Any] | None = None,
        metadata: dict[str, Any] | None = None,
        access_token: str | None = None,
    ) -> MessageRow:
        payload = {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "citations": citations or [],
            "metadata": metadata or {},
        }
        response = self._client_for(access_token).table(_MESSAGES).insert(payload).execute()
        return MessageRow.from_row(response.data[0])

    def list_messages(self, conversation_id: str, access_token: str | None = None) -> list[MessageRow]:
        response = (
            self._client_for(access_token)
            .table(_MESSAGES)
            .select("*")
            .eq("conversation_id", conversation_id)
            .order("created_at")
            .execute()
        )
        return [MessageRow.from_row(row) for row in response.data]
