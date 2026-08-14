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
from .escalation_models import Escalation, EscalationMessage, EscalationNote

logger: logging.Logger = get_logger(__name__)

_ESCALATIONS = "escalations"
_MESSAGES = "escalation_messages"
_NOTES = "escalation_notes"
_ACTIVE_STATUSES = ("assigned", "active", "waiting_for_customer")


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
                "ai_engaged": False,
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

    def set_waiting_for_customer(self, escalation_id: str) -> Escalation:
        response = (
            self._client.table(_ESCALATIONS)
            .update({"status": "waiting_for_customer"})
            .eq("id", escalation_id)
            .execute()
        )
        return Escalation.from_row(response.data[0])

    def set_active(self, escalation_id: str) -> None:
        self._client.table(_ESCALATIONS).update({"status": "active"}).eq(
            "id", escalation_id
        ).eq("status", "waiting_for_customer").execute()

    def set_ai_engaged(self, escalation_id: str, engaged: bool) -> Escalation:
        response = (
            self._client.table(_ESCALATIONS)
            .update({"ai_engaged": engaged})
            .eq("id", escalation_id)
            .execute()
        )
        return Escalation.from_row(response.data[0])

    def count_active_for_agent(self, agent_id: str) -> int:
        response = (
            self._client.table(_ESCALATIONS)
            .select("id", count="exact")
            .eq("assigned_agent_id", agent_id)
            .in_("status", list(_ACTIVE_STATUSES))
            .execute()
        )
        return response.count or 0

    def list_by_conversation_ids(self, conversation_ids: list[str]) -> list[Escalation]:
        if not conversation_ids:
            return []
        response = (
            self._client.table(_ESCALATIONS)
            .select("*")
            .in_("conversation_id", conversation_ids)
            .order("created_at", desc=True)
            .execute()
        )
        return [Escalation.from_row(row) for row in response.data]

    def resolution_stats_for_agent(self, agent_id: str) -> tuple[int, int]:
        """(resolved_or_closed_count, total_ever_assigned_count) — all-time,
        for the agent's own resolution-rate KPI card."""
        response = (
            self._client.table(_ESCALATIONS)
            .select("status", count="exact")
            .eq("assigned_agent_id", agent_id)
            .execute()
        )
        rows = response.data or []
        resolved = sum(1 for row in rows if row["status"] in ("resolved", "closed"))
        return resolved, len(rows)

    def avg_first_response_minutes_for_agent(self, agent_id: str) -> float | None:
        """Mirrors TenantAnalyticsService's per-workspace calculation, scoped
        to one agent: first agent message timestamp minus assigned_at (or
        created_at if never separately assigned)."""
        assigned_rows = (
            self._client.table(_ESCALATIONS)
            .select("id,assigned_at,created_at")
            .eq("assigned_agent_id", agent_id)
            .not_.is_("assigned_agent_id", "null")
            .execute()
        ).data or []
        if not assigned_rows:
            return None
        escalation_ids = [row["id"] for row in assigned_rows]
        assigned_at_by_id = {row["id"]: row.get("assigned_at") or row.get("created_at") for row in assigned_rows}
        message_rows = (
            self._client.table(_MESSAGES)
            .select("escalation_id,created_at")
            .in_("escalation_id", escalation_ids)
            .eq("sender_type", "agent")
            .order("created_at")
            .execute()
        ).data or []
        first_agent_message: dict[str, str] = {}
        for row in message_rows:
            eid = row["escalation_id"]
            if eid not in first_agent_message:
                first_agent_message[eid] = row["created_at"]

        minutes: list[float] = []
        for eid, first_at in first_agent_message.items():
            assigned_at = assigned_at_by_id.get(eid)
            if not assigned_at:
                continue
            delta = (
                datetime.fromisoformat(first_at.replace("Z", "+00:00"))
                - datetime.fromisoformat(assigned_at.replace("Z", "+00:00"))
            ).total_seconds() / 60
            minutes.append(max(0.0, delta))
        return (sum(minutes) / len(minutes)) if minutes else None

    def list_resolved_today_for_agent(self, agent_id: str, since_iso: str) -> list[Escalation]:
        response = (
            self._client.table(_ESCALATIONS)
            .select("*")
            .eq("assigned_agent_id", agent_id)
            .eq("status", "resolved")
            .gte("resolved_at", since_iso)
            .execute()
        )
        return [Escalation.from_row(row) for row in response.data]

    def mark_resolved(self, escalation_id: str) -> Escalation:
        response = (
            self._client.table(_ESCALATIONS)
            .update({"status": "resolved", "resolved_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", escalation_id)
            .execute()
        )
        return Escalation.from_row(response.data[0])

    def merge_summary(self, escalation_id: str, updates: dict[str, Any]) -> Escalation:
        """Fetch-merge-write into the flexible `summary` JSON column —
        used to attach fields (resolution summary, AI-rejoin handoff
        recap) after creation without a schema migration, same precedent
        as `build_summary()` populating this column in the first place."""
        current = self.get(escalation_id)
        summary = dict(current.summary) if current and current.summary else {}
        summary.update(updates)
        response = (
            self._client.table(_ESCALATIONS)
            .update({"summary": summary})
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

    def add_note(
        self, workspace_id: str, escalation_id: str, author_agent_id: str | None, content: str
    ) -> EscalationNote:
        payload = {
            "workspace_id": workspace_id,
            "escalation_id": escalation_id,
            "author_agent_id": author_agent_id,
            "content": content,
        }
        response = self._client.table(_NOTES).insert(payload).execute()
        return EscalationNote.from_row(response.data[0])

    def list_notes(self, escalation_id: str) -> list[EscalationNote]:
        response = (
            self._client.table(_NOTES)
            .select("*")
            .eq("escalation_id", escalation_id)
            .order("created_at")
            .execute()
        )
        return [EscalationNote.from_row(row) for row in response.data]
