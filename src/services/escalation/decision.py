"""decide_escalation — the single point that decides AI-continues vs.
escalate (Phase 24).

Reuses the existing confidence system exclusively — never a second one.
``_CONFIDENCE_THRESHOLD`` is imported directly from ``context_merger``, the
same cross-module convention ``search_manager.py`` already establishes.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..merger.context_merger import _CONFIDENCE_THRESHOLD
from .intent import detect_critical_intent, detect_human_request

EscalationReason = str  # "explicit_request" | "critical_intent" | "low_confidence" | "unresolved"


@dataclass(frozen=True)
class EscalationDecision:
    should_escalate: bool
    reason: EscalationReason | None = None
    critical_category: str | None = None


def decide_escalation(
    *,
    question: str,
    kb_confidence: float | None,
    has_evidence: bool,
) -> EscalationDecision:
    """Priority order: explicit request > critical intent > low/missing
    confidence > no evidence at all > otherwise the AI continues."""
    if detect_human_request(question):
        return EscalationDecision(True, "explicit_request")

    category = detect_critical_intent(question)
    if category is not None:
        return EscalationDecision(True, "critical_intent", category)

    if isinstance(kb_confidence, (int, float)) and kb_confidence < _CONFIDENCE_THRESHOLD:
        return EscalationDecision(True, "low_confidence")

    if not has_evidence:
        return EscalationDecision(True, "unresolved")

    return EscalationDecision(False, None)
