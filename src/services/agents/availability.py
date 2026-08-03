"""Agent availability (Phase 24) — manual only.

No automatic scheduling, no business hours, no presence detection — those
are explicitly out of scope for this phase. An agent is "available" purely
because they said so.
"""

from __future__ import annotations

from typing import Literal

from .agent_models import SupportAgent

AgentStatus = Literal["available", "away", "offline"]

AGENT_STATUSES: tuple[AgentStatus, ...] = ("available", "away", "offline")


def is_available(agent: SupportAgent) -> bool:
    return agent.status == "available"
