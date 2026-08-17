"""AttendanceService — clock in/out and AUX state transitions.

Enforces the clocking rules explicitly here (not left implicit in the route
layer): one active work session per agent, AUX only inside a valid session,
clocking out force-ends any active AUX. "Only one active AUX at a time" is
enforced by design, not by rejection — starting a new AUX period while one
is already active cleanly ends the previous one first (a deliberate UX
choice: switching straight from "Meeting" to "Break" is one action, not
"end AUX" then "start AUX"). Keeps `SupportAgent.status`
("available"/"away"/"offline" — load-bearing for auto-assignment via
`AgentService.list_available()`/`select_best_agent()`) in sync
automatically so no existing routing code needs to change: starting any
AUX period sets status="away"; ending AUX sets status="available"; clocking
out sets status="offline".
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from ...shared.logging import get_logger
from .agent_service import AgentService
from .attendance_models import AuxEvent, WorkSession
from .attendance_repository import AttendanceRepository

logger: logging.Logger = get_logger(__name__)


class AlreadyClockedInError(Exception):
    """Raised when clocking in while an active session already exists."""


class NotClockedInError(Exception):
    """Raised when clocking out, or starting AUX, with no active session."""


class NoActiveAuxError(Exception):
    """Raised when ending AUX with no active AUX period to end."""


def _seconds_between(start_iso: str, end: datetime) -> int:
    start = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    return max(0, int((end - start).total_seconds()))


class AttendanceService:
    def __init__(
        self,
        repository: AttendanceRepository | None = None,
        agent_service: AgentService | None = None,
    ) -> None:
        self._repo = repository or AttendanceRepository()
        self._agents = agent_service or AgentService()

    # ------------------------------------------------------------------
    # Work sessions
    # ------------------------------------------------------------------

    def clock_in(self, workspace_id: str, agent_id: str) -> WorkSession:
        if self._repo.get_active_session(agent_id) is not None:
            raise AlreadyClockedInError("Agent already has an active work session.")
        session = self._repo.clock_in(workspace_id, agent_id)
        self._agents.update_status(agent_id, "available")
        return session

    def clock_out(self, agent_id: str) -> WorkSession:
        session = self._repo.get_active_session(agent_id)
        if session is None:
            raise NotClockedInError("Agent has no active work session to clock out of.")

        # Clocking out force-ends any active AUX first — a work session
        # can never close with an AUX period still open.
        active_aux = self._repo.get_active_aux(agent_id)
        if active_aux is not None:
            now = datetime.now(timezone.utc)
            self._repo.end_aux(active_aux.id, _seconds_between(active_aux.started_at, now))

        now = datetime.now(timezone.utc)
        total_seconds = _seconds_between(session.clock_in_at, now)
        closed = self._repo.clock_out(session.id, total_seconds)
        self._agents.update_status(agent_id, "offline")
        return closed

    def get_current_session(self, agent_id: str) -> WorkSession | None:
        return self._repo.get_active_session(agent_id)

    # ------------------------------------------------------------------
    # AUX
    # ------------------------------------------------------------------

    def start_aux(
        self, workspace_id: str, agent_id: str, aux_type: str, reason: str | None = None
    ) -> AuxEvent:
        """Starts a new AUX period. "available" isn't a real AUX period —
        returning to Available is `end_aux()`, not `start_aux("available")`;
        callers (the route layer) are expected to route accordingly."""
        session = self._repo.get_active_session(agent_id)
        if session is None:
            raise NotClockedInError("Cannot start an AUX state without an active work session.")

        active_aux = self._repo.get_active_aux(agent_id)
        if active_aux is not None:
            # Only one AUX at a time — ending the previous one is an
            # explicit, deliberate transition, not silently overwritten.
            now = datetime.now(timezone.utc)
            self._repo.end_aux(active_aux.id, _seconds_between(active_aux.started_at, now))

        event = self._repo.start_aux(workspace_id, agent_id, session.id, aux_type, reason)
        self._agents.update_status(agent_id, "away")
        return event

    def end_aux(self, agent_id: str) -> AuxEvent:
        active = self._repo.get_active_aux(agent_id)
        if active is None:
            raise NoActiveAuxError("No active AUX state to end.")
        now = datetime.now(timezone.utc)
        closed = self._repo.end_aux(active.id, _seconds_between(active.started_at, now))
        self._agents.update_status(agent_id, "available")
        return closed

    def get_current_aux(self, agent_id: str) -> AuxEvent | None:
        return self._repo.get_active_aux(agent_id)
