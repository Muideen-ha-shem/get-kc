"""build_summary — the structured AI-to-human handoff summary (Phase 24).

Sourced entirely from data the advisory layer already computed per turn
(``AdvisoryResult``) — no new LLM call.
"""

from __future__ import annotations

from typing import Any

from ..advisory.advisory_layer import AdvisoryResult


def build_summary(
    *,
    workspace_name: str,
    customer_company: str | None,
    advisory: AdvisoryResult | None,
    question: str,
    sentiment: str,
) -> dict[str, Any]:
    intent = advisory.intent if advisory else None
    return {
        "customer": customer_company or "Unknown",
        "workspace": workspace_name,
        "intent": list(intent.categories) if intent else [],
        "sentiment": sentiment,
        "products": list(intent.products) if intent else [],
        "problem": question,
        "actions_already_taken": [
            {"label": action.label, "action_type": action.action_type}
            for action in (advisory.next_actions if advisory else [])
        ],
        "suggested_resolution": [
            {"product": rec.product, "reason": rec.reason}
            for rec in (advisory.recommendations if advisory else [])
        ],
    }
