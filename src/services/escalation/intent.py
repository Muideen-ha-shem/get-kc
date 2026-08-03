"""Deterministic keyword classifiers for escalation signals (Phase 24).

Same philosophy as ``SourceRouter``/``ProductRouter``: pure functions,
lowercase substring matching, no I/O, no LLM call.
"""

from __future__ import annotations

_HUMAN_REQUEST_KEYWORDS: tuple[str, ...] = (
    "talk to a human",
    "speak to a human",
    "talk to support",
    "speak to support",
    "connect me to an agent",
    "talk to an agent",
    "speak to an agent",
    "human agent",
    "real person",
    "call me",
    "speak with sales",
    "talk to sales",
    "technical support",
    "customer support",
    "escalate",
)


def detect_human_request(question: str) -> bool:
    """True when the question explicitly asks for a human."""
    lowered = question.lower()
    return any(keyword in lowered for keyword in _HUMAN_REQUEST_KEYWORDS)


_CRITICAL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "billing": ("overcharged", "billing error", "wrong invoice", "refund"),
    "security_incident": ("hacked", "breach", "unauthorized access", "compromised"),
    "legal": ("lawsuit", "legal action", "subpoena", "compliance violation"),
    "data_loss": ("lost my data", "data deleted", "data loss", "missing records"),
    "account_access": ("locked out", "can't log in", "cannot log in", "account suspended", "account disabled"),
    "production_outage": ("production is down", "system is down", "outage", "not working in production"),
}


def detect_critical_intent(question: str) -> str | None:
    """Return the matched critical category, or ``None``."""
    lowered = question.lower()
    for category, keywords in _CRITICAL_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return None


_FRUSTRATION_KEYWORDS: tuple[str, ...] = (
    "frustrated",
    "angry",
    "ridiculous",
    "unacceptable",
    "terrible",
    "worst",
    "furious",
    "fed up",
    "sick of",
    "!!!",
)


def detect_sentiment_hint(question: str) -> str:
    """A coarse, deterministic sentiment tag — ``"frustrated"`` or ``"neutral"``.

    Not a real sentiment model — a small keyword heuristic, kept
    deliberately simple per Phase 24's "deterministic (keyword/rule-based)"
    constraint. Exists only because the escalation summary's ``Sentiment``
    field needs a value from somewhere, and nothing else in the pipeline
    produces one.
    """
    lowered = question.lower()
    if any(keyword in lowered for keyword in _FRUSTRATION_KEYWORDS):
        return "frustrated"
    return "neutral"
