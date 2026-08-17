"""AttendanceRepository — raw persistence for `agent_work_sessions`/
`agent_aux_events` (Agent Operations).

No RLS (team/shared-visibility tables, same precedent as `support_agents`/
`escalations`) — every method uses the plain anon-key client, workspace_id
filtering happens in the query, mirroring `AgentRepository`/
`EscalationRepository`'s exact style. Historical rows are never deleted —
only the still-open row (no `clock_out_at`/`ended_at`) is ever updated.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from supabase import Client

from ...sb import get_client
from ...shared.logging import get_logger
from .attendance_models import AuxEvent, WorkSession

logger: logging.Logger = get_logger(__name__)

_SESSIONS = "agent_work_sessions"
_AUX_EVENTS = "agent_aux_events"


class AttendanceRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    # ------------------------------------------------------------------
    # Work sessions
    # ------------------------------------------------------------------

    def get_active_session(self, agent_id: str) -> WorkSession | None:
        response = (
            self._client.table(_SESSIONS)
            .select("*")
            .eq("agent_id", agent_id)
            .is_("clock_out_at", "null")
            .limit(1)
            .execute()
        )
        return WorkSession.from_row(response.data[0]) if response.data else None

    def clock_in(self, workspace_id: str, agent_id: str) -> WorkSession:
        now = datetime.now(timezone.utc)
        payload = {
            "workspace_id": workspace_id,
            "agent_id": agent_id,
            "work_date": now.date().isoformat(),
            "clock_in_at": now.isoformat(),
        }
        response = self._client.table(_SESSIONS).insert(payload).execute()
        return WorkSession.from_row(response.data[0])

    def clock_out(self, session_id: str, total_work_seconds: int) -> WorkSession:
        response = (
            self._client.table(_SESSIONS)
            .update({
                "clock_out_at": datetime.now(timezone.utc).isoformat(),
                "total_work_seconds": total_work_seconds,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", session_id)
            .execute()
        )
        return WorkSession.from_row(response.data[0])

    def list_sessions_for_workspace(
        self, workspace_id: str, start_date: str, end_date: str
    ) -> list[WorkSession]:
        response = (
            self._client.table(_SESSIONS)
            .select("*")
            .eq("workspace_id", workspace_id)
            .gte("work_date", start_date)
            .lte("work_date", end_date)
            .execute()
        )
        return [WorkSession.from_row(row) for row in response.data or []]

    # ------------------------------------------------------------------
    # AUX events
    # ------------------------------------------------------------------

    def get_active_aux(self, agent_id: str) -> AuxEvent | None:
        response = (
            self._client.table(_AUX_EVENTS)
            .select("*")
            .eq("agent_id", agent_id)
            .is_("ended_at", "null")
            .limit(1)
            .execute()
        )
        return AuxEvent.from_row(response.data[0]) if response.data else None

    def start_aux(
        self,
        workspace_id: str,
        agent_id: str,
        work_session_id: str,
        aux_type: str,
        reason: str | None = None,
    ) -> AuxEvent:
        payload = {
            "workspace_id": workspace_id,
            "agent_id": agent_id,
            "work_session_id": work_session_id,
            "aux_type": aux_type,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
        }
        response = self._client.table(_AUX_EVENTS).insert(payload).execute()
        return AuxEvent.from_row(response.data[0])

    def end_aux(self, aux_id: str, duration_seconds: int) -> AuxEvent:
        response = (
            self._client.table(_AUX_EVENTS)
            .update({
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": duration_seconds,
            })
            .eq("id", aux_id)
            .execute()
        )
        return AuxEvent.from_row(response.data[0])

    def list_aux_events_for_session(self, work_session_id: str) -> list[AuxEvent]:
        response = (
            self._client.table(_AUX_EVENTS)
            .select("*")
            .eq("work_session_id", work_session_id)
            .order("started_at")
            .execute()
        )
        return [AuxEvent.from_row(row) for row in response.data or []]

    def list_aux_events_for_workspace(
        self, workspace_id: str, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """Raw rows (not models) joined loosely by date range on started_at —
        used by TenantAnalyticsService for AUX-time aggregation, same
        "select just what's needed" style as its other queries."""
        response = (
            self._client.table(_AUX_EVENTS)
            .select("agent_id,aux_type,duration_seconds,started_at,ended_at")
            .eq("workspace_id", workspace_id)
            .gte("started_at", start_date)
            .lte("started_at", end_date)
            .execute()
        )
        return response.data or []
