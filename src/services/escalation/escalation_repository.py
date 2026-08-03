"""EscalationRepository — raw persistence for `escalations`/`escalation_messages`
(Phase 24). No RLS (team/shared-visibility tables) — app-layer workspace_id
filtering, same precedent as `WorkspaceRepository`/`AgentRepository`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from supabase import Client

from ...sb import get_client
from ...shared.logging import get_logger
from .escalation_models import Escalation, EscalationMessage

logger: logging.Logger = get_logger(__name__)

_ESCALATIONS = "escalations"
_MESSAGES = "escalation_messages"


class EscalationRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def create(
        self,
        workspace_id: str,
        conversation_id: str | None,
        trigger_reason: str,
        department: str | None,
        summary: dict[str, Any] | None,
    ) -> Escalation:
        payload = {
            "workspace_id": workspace_id,
            "conversation_id": conversation_id,
            "trigger_reason": trigger_reason,
            "department": department,
            "summary": summary,
        }
        response = self._client.table(_ESCALATIONS).insert(payload).execute()
        return Escalation.from_row(response.data[0])

    def get(self, escalation_id: str) -> Escalation | None:
        response = (
            self._client.table(_ESCALATIONS).select("*").eq("id", escalation_id).limit(1).execute()
        )
        if not response.data:
            return None
        return Escalation.from_row(response.data[0])

    def list_waiting(self, workspace_id: str) -> list[Escalation]:
        response = (
            self._client.table(_ESCALATIONS)
            .select("*")
            .eq("workspace_id", workspace_id)
            .eq("status", "waiting")
            .order("created_at")
            .execute()
        )
        return [Escalation.from_row(row) for row in response.data]

    def list_assigned_to(self, agent_id: str) -> list[Escalation]:
        response = (
            self._client.table(_ESCALATIONS)
            .select("*")
            .eq("assigned_agent_id", agent_id)
            .order("created_at", desc=True)
            .execute()
        )
        return [Escalation.from_row(row) for row in response.data]

    def assign(self, escalation_id: str, agent_id: str) -> Escalation:
        response = (
            self._client.table(_ESCALATIONS)
            .update({
                "status": "assigned",
                "assigned_agent_id": agent_id,
                "assigned_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", escalation_id)
            .execute()
        )
        return Escalation.from_row(response.data[0])

    def mark_active_if_first_message(self, escalation_id: str) -> None:
        if self.list_messages(escalation_id):
            return
        self._client.table(_ESCALATIONS).update({"status": "active"}).eq(
            "id", escalation_id
        ).eq("status", "assigned").execute()

    def mark_resolved(self, escalation_id: str) -> Escalation:
        response = (
            self._client.table(_ESCALATIONS)
            .update({"status": "resolved", "resolved_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", escalation_id)
            .execute()
        )
        return Escalation.from_row(response.data[0])

    def mark_closed(self, escalation_id: str) -> Escalation:
        response = (
            self._client.table(_ESCALATIONS)
            .update({"status": "closed", "closed_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", escalation_id)
            .execute()
        )
        return Escalation.from_row(response.data[0])

    def add_message(
        self, escalation_id: str, sender_type: str, sender_auth_user_id: str | None, content: str
    ) -> EscalationMessage:
        payload = {
            "escalation_id": escalation_id,
            "sender_type": sender_type,
            "sender_auth_user_id": sender_auth_user_id,
            "content": content,
        }
        response = self._client.table(_MESSAGES).insert(payload).execute()
        return EscalationMessage.from_row(response.data[0])

    def list_messages(self, escalation_id: str) -> list[EscalationMessage]:
        response = (
            self._client.table(_MESSAGES)
            .select("*")
            .eq("escalation_id", escalation_id)
            .order("created_at")
            .execute()
        )
        return [EscalationMessage.from_row(row) for row in response.data]
