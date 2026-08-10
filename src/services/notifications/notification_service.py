"""NotificationService — in-app notifications for a customer's own activity.

Same RLS-authenticated-client pattern as the rest of Phase 20/21's personal
data (``SavedComparisonService``, ``ProfileService``, ...). Every notify()
call here is triggered by a user's own authenticated action (booking an
appointment, saving a recommendation, submitting a demo request while signed
in), so the caller always already has that user's access token on hand —
there's no cross-user "admin notifies someone else" path in this phase.

Designed for future realtime support: callers only ever go through
``notify``/``list_for_user``/``mark_read`` — swapping the underlying
transport (e.g. a Supabase Realtime subscription pushed to the frontend
instead of polling ``GET /notifications``) touches nothing outside this
class.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

from supabase import Client

from ...sb import get_authenticated_client, get_client
from ...services.workspace.workspace_models import DEFAULT_WORKSPACE_ID
from ...shared.logging import get_logger

logger: logging.Logger = get_logger(__name__)

_TABLE = "notifications"

NotificationType = Literal["demo_request", "appointment", "saved_recommendation", "support_update"]


@dataclass(frozen=True)
class Notification:
    id: str
    type: str
    title: str
    body: str | None
    is_read: bool
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Notification":
        return cls(**{field: row.get(field) for field in cls.__dataclass_fields__})


class NotificationService:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def _client_for(self, access_token: str | None) -> Client:
        return get_authenticated_client(access_token) if access_token else self._client

    def notify(
        self,
        user_id: str,
        type: NotificationType,
        title: str,
        body: str | None = None,
        access_token: str | None = None,
        workspace_id: str = DEFAULT_WORKSPACE_ID,
    ) -> Notification | None:
        """Create a notification. Best-effort by design — callers (booking,
        saving a recommendation, ...) must never let a notification failure
        break the primary action, so this swallows and logs rather than
        raising. Returns ``None`` on failure."""
        try:
            payload = {
                "user_id": user_id,
                "type": type,
                "title": title,
                "body": body,
                "workspace_id": workspace_id,
            }
            response = self._client_for(access_token).table(_TABLE).insert(payload).execute()
            return Notification.from_row(response.data[0])
        except Exception as exc:
            logger.warning("NotificationService: notify failed (non-fatal) — %s", exc)
            return None

    def list_for_user(
        self,
        user_id: str,
        access_token: str | None = None,
        limit: int = 50,
        workspace_id: str | None = None,
    ) -> list[Notification]:
        query = (
            self._client_for(access_token)
            .table(_TABLE)
            .select("*")
            .eq("user_id", user_id)
        )
        if workspace_id is not None:
            query = query.eq("workspace_id", workspace_id)
        response = query.order("created_at", desc=True).limit(limit).execute()
        return [Notification.from_row(row) for row in response.data]

    def unread_count(self, user_id: str, access_token: str | None = None, workspace_id: str | None = None) -> int:
        query = (
            self._client_for(access_token)
            .table(_TABLE)
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("is_read", False)
        )
        if workspace_id is not None:
            query = query.eq("workspace_id", workspace_id)
        response = query.execute()
        return response.count or 0

    def mark_read(self, notification_id: str, user_id: str, access_token: str | None = None) -> bool:
        response = (
            self._client_for(access_token)
            .table(_TABLE)
            .update({"is_read": True})
            .eq("id", notification_id)
            .eq("user_id", user_id)
            .execute()
        )
        return bool(response.data)

    def mark_all_read(self, user_id: str, access_token: str | None = None) -> None:
        self._client_for(access_token).table(_TABLE).update({"is_read": True}).eq("user_id", user_id).eq(
            "is_read", False
        ).execute()
