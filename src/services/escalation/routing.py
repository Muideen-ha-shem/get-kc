"""Agent selection (Phase 24 + Phase 25).

``select_agent`` (Phase 24) — "first available agent," intentionally
trivial. Still used wherever "just give me anyone" is enough; not removed.

``select_best_agent`` (Phase 25) — lowest active workload, oldest-idle as
the deterministic tiebreak, with an optional soft department preference.
No AI, no round-robin, no skills-matching.
"""

from __future__ import annotations

from typing import Sequence

from ..agents.agent_models import SupportAgent
from ..agents.availability import is_available


def select_agent(agents: Sequence[SupportAgent]) -> SupportAgent | None:
    available = [a for a in agents if is_available(a)]
    return available[0] if available else None


def select_best_agent(
    agents: Sequence[SupportAgent],
    workloads: dict[str, int],
    *,
    department: str | None = None,
) -> SupportAgent | None:
    """Lowest workload first, oldest-idle (``updated_at`` ascending) as the
    tiebreak. When *department* is given, prefers an available agent in
    that department; if none exists, falls back to any available agent
    workspace-wide rather than leaving the escalation unassigned."""
    available = [a for a in agents if is_available(a)]
    if not available:
        return None

    pool = available
    if department is not None:
        same_department = [a for a in available if a.department == department]
        if same_department:
            pool = same_department

    ordered = sorted(pool, key=lambda a: (workloads.get(a.id, 0), a.updated_at or ""))
    return ordered[0]
