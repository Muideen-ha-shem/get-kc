"""workspace_analyst — "Ask HavisIQ" for Workspace Admins.

Reuses ResponseGenerator for synthesis (the exact same object used by the
customer-facing chat, the Agent Copilot, and resolution summaries — not a
second generation system) and TenantAnalyticsService for real, workspace-
scoped data. The analyst's job is narrow: gather real numbers, hand them
to the model as evidence, and require it to distinguish FACT (a number
straight from the evidence) from ANALYSIS (a trend/comparison computed
from those numbers) from RECOMMENDATION (a suggested action) — never
inventing a number not present in the evidence, and saying so plainly when
asked about something the evidence doesn't cover (knowledge gaps,
frequently-searched topics, source failures aren't tracked yet — see
tenant_analytics_service.py's own honesty note).

workspace_id always comes from the caller's own require_workspace_admin
resolution (see api/routes/admin_workspaces.py) — never accepted as
free-form input here, so isolation is inherited from
TenantAnalyticsService's own workspace_id-scoped queries.
"""

from __future__ import annotations

import json
from typing import Any

from ..generator.response_generator import ResponseGenerator
from ..merger.context_merger import EvidenceItem
from .tenant_analytics_service import TenantAnalyticsService

_FORMAT_INSTRUCTIONS = (
    "Answer using labeled sections where relevant: FACT (a number taken directly "
    "from the evidence below), ANALYSIS (a comparison, trend, or interpretation "
    "computed from those numbers), and RECOMMENDATION (a suggested action, clearly "
    "marked as a suggestion, never phrased as a measured fact). Never state a "
    "number that isn't present in the evidence below. If the question asks about "
    "something the evidence doesn't cover — for example knowledge gaps, "
    "frequently-searched topics, or source failures — say plainly that you don't "
    "have that data tracked yet instead of guessing."
)

_BRIEFING_QUESTION = (
    "Give a brief operational summary for this workspace: conversation and "
    "escalation volume, resolution rate and timing, the top requested product, "
    "and anything that needs attention."
)


def _format_snapshot(snapshot: dict[str, Any]) -> str:
    return json.dumps(snapshot, indent=2, default=str)


def answer_question(
    workspace_id: str,
    question: str,
    *,
    analytics_service: TenantAnalyticsService | None = None,
    response_generator: ResponseGenerator | None = None,
) -> dict[str, Any]:
    """Answers *question* grounded in this workspace's real operational
    metrics. Returns ``{"answer": str}`` — never raises; a generation
    failure surfaces through ResponseGenerator's own existing error
    fallback, same as every other caller of ``generate()``.
    """
    analytics_service = analytics_service or TenantAnalyticsService()
    snapshot = analytics_service.workspace_operational_report(workspace_id)

    evidence = [EvidenceItem(
        content=_format_snapshot(snapshot), score=1.0,
        title="Workspace operational metrics snapshot", url="", source_type="workspace_metrics",
    )]

    generator = response_generator or ResponseGenerator()
    result = generator.generate(question=f"{question}\n\n{_FORMAT_INSTRUCTIONS}", context=evidence)
    return {"answer": result.get("answer", "")}


def daily_briefing(
    workspace_id: str,
    *,
    analytics_service: TenantAnalyticsService | None = None,
    response_generator: ResponseGenerator | None = None,
) -> dict[str, Any]:
    """A thin variant of answer_question with a canned prompt — not a
    separate pipeline. On-demand for this pass; a scheduled/proactive push
    is out of scope (no scheduling infrastructure exists in this codebase
    to hook into safely without its own scoping pass)."""
    return answer_question(
        workspace_id, _BRIEFING_QUESTION,
        analytics_service=analytics_service, response_generator=response_generator,
    )
