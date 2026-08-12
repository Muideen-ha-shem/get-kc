"""detect_action_intent — recognizes a live-chat/escalation or appointment
request BEFORE it ever reaches retrieval.

Same philosophy as ``self_identity.py``: pure function, no I/O, imported by
multiple layers (ChatOrchestrator's pre-retrieval short-circuit, and
SearchManager's own web-fallback guards) so they can't drift out of sync.

Live-confirmed bug this fixes: "Can you arrange a quick chat with a
specialist?" followed by "Today 1:45pm WAT, live chat" had zero KB evidence,
so SearchManager's low-confidence fallback fired a live web search for the
raw scheduling text — producing unrelated timezone/city results. Neither
message ever reached the escalation/appointment machinery that already
exists server-side; it should never have gone near retrieval at all.

Reuses ``escalation.intent.detect_human_request`` rather than duplicating
its keyword list — deliberately no new classifier, LLM or otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..escalation.intent import detect_human_request

ActionKind = Literal["escalation", "appointment", "demo"]


@dataclass(frozen=True)
class ActionIntentMatch:
    kind: ActionKind


# Checked first — most specific. A demo request has its own backend
# (POST /demo-request, no time-slot concept) distinct from an appointment
# booking (real SLOT_TEMPLATE availability) — see action_workflow.py.
_DEMO_KEYWORDS: tuple[str, ...] = (
    "demo",
    "book a demo",
    "request a demo",
    "see a demo",
    "product demo",
    "schedule a demo",
)

_APPOINTMENT_KEYWORDS: tuple[str, ...] = (
    "book an appointment",
    "book a call",
    "book a session",
    "schedule an appointment",
    "schedule a call",
    "set up a call",
    "set up a meeting",
)


def detect_action_intent(question: str | None) -> ActionIntentMatch | None:
    """Classify *question* as a demo, appointment, or escalation
    (live-chat/human) request, or ``None`` if it's none of those. Checked
    most-specific first: demo, then appointment, then the broad
    human-request keyword list.
    """
    if not question:
        return None
    lowered = question.lower()
    if any(keyword in lowered for keyword in _DEMO_KEYWORDS):
        return ActionIntentMatch("demo")
    if any(keyword in lowered for keyword in _APPOINTMENT_KEYWORDS):
        return ActionIntentMatch("appointment")
    if detect_human_request(question):
        return ActionIntentMatch("escalation")
    return None
