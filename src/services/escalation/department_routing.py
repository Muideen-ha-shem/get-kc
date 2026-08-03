"""determine_department — deterministic escalation → department mapping
(Phase 25).

Same keyword-classifier philosophy as ``intent.py``: pure functions,
lowercase substring matching, no I/O, no LLM. Department was informational
only in Phase 24; ``EscalationService`` now uses the value returned here to
*prefer* an available agent in the same department (falling back to any
available agent workspace-wide if none match) before applying
``select_best_agent``'s workload/idle-time ordering — see ``routing.py``.
"""

from __future__ import annotations

CRITICAL_CATEGORY_DEPARTMENT: dict[str, str] = {
    "billing": "Finance",
    "security_incident": "Support",
    "legal": "Support",
    "data_loss": "Support",
    "account_access": "Support",
    "production_outage": "Support",
}

_DEMO_KEYWORDS: tuple[str, ...] = ("demo", "demonstration", "see it in action")
_TRAINING_KEYWORDS: tuple[str, ...] = ("training", "certification", "onboarding session", "how do i use")
_IMPLEMENTATION_KEYWORDS: tuple[str, ...] = ("implementation", "rollout", "go live", "deployment project")

DEFAULT_DEPARTMENT = "Support"


def determine_department(*, critical_category: str | None, question: str) -> str:
    if critical_category is not None and critical_category in CRITICAL_CATEGORY_DEPARTMENT:
        return CRITICAL_CATEGORY_DEPARTMENT[critical_category]

    lowered = question.lower()
    if any(keyword in lowered for keyword in _DEMO_KEYWORDS):
        return "Sales"
    if any(keyword in lowered for keyword in _TRAINING_KEYWORDS):
        return "Training"
    if any(keyword in lowered for keyword in _IMPLEMENTATION_KEYWORDS):
        return "Implementation"

    return DEFAULT_DEPARTMENT
