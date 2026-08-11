"""ClarificationEngine — asks instead of guessing when intent is genuinely
ambiguous.

Only fires for a narrow, deliberate case: exactly two products matched
*purely by intent keywords* — no business-theme match, and the question
didn't itself name either product. Two other "ambiguous" shapes must NOT
trigger this:

* A business-theme match (``intent.via_theme``) is a *deliberate*
  multi-product bundle — "we're digitizing our company" is supposed to
  surface six products at once, and asking "which one did you mean?" there
  would break the working multi-solution recommendation flow from Phase 17.
* An explicitly-named comparison (``intent.named_explicitly`` — e.g.
  "Compare AppManage and Havis eCertify") isn't ambiguous at all: the user
  knows exactly what they asked for. Confirmed live this is a real failure
  mode without the check — every existing "Compare X and Y" question would
  otherwise get a clarifying question instead of the comparison it asked for.
* A comparison asked via business-problem language rather than product
  names — "Compare payroll and expense management solutions" — is just as
  deliberate as naming the products directly; confirmed live this is a
  distinct failure mode from the naming case above (``named_explicitly`` is
  correctly ``False`` here since no product name appears in the text, but
  the "compare" phrasing itself is just as strong a signal of deliberate
  intent as naming would be).

Genuine ambiguity is different: two competing, single-purpose products both
inferred from need-phrased language (not named, not asked to be compared)
with no signal favoring either is exactly when a real consultant would ask
a clarifying question rather than guess.

The question text is built entirely from each candidate's own registry
``business_problem`` field — never invented, so it can't misdescribe what a
product actually does.
"""

from __future__ import annotations

import logging

from ...shared.logging import get_logger
from ...shared.product_registry import PRODUCT_REGISTRY
from .intent_engine import BusinessIntent

logger: logging.Logger = get_logger(__name__)

_COMPARISON_KEYWORDS = ("compare", "comparison", " vs ", " vs. ", " versus ")

_RECOMMENDATION_REQUEST_KEYWORDS = (
    "recommend", "recommendation", "suggest a solution", "suggest a product",
    "best solution", "best product", "best option",
    "what should i use", "which product should i use", "which solution",
    "what do you suggest", "what would you recommend",
    "solution for my business", "solution for my company",
    "help me choose", "help me pick",
)


class ClarificationEngine:
    """Decides whether a question needs a clarifying follow-up instead of
    a direct answer, and builds that follow-up when it does."""

    def check(self, intent: BusinessIntent) -> str | None:
        """Return a clarifying question for *intent*, or ``None`` if the
        question should just be answered normally."""
        if intent.via_theme:
            return None
        if intent.named_explicitly:
            return None
        if self._asks_for_comparison(intent.question):
            return None
        if intent.confidence != "ambiguous":
            return None
        if len(intent.products) != 2:
            # More than two candidates without a theme is rare and not
            # cleanly askable as a single either/or question — let it fall
            # through to the existing per-product retrieval behavior
            # rather than construct an unwieldy multi-way question.
            return None

        first, second = intent.products
        first_problem = PRODUCT_REGISTRY.get(first, {}).get("business_problem", first)
        second_problem = PRODUCT_REGISTRY.get(second, {}).get("business_problem", second)

        question = (
            f"Just to point you to the right solution — are you looking for "
            f"something for **{first_problem}**, or **{second_problem}**?"
        )
        logger.info(
            "ClarificationEngine: ambiguous match %s for %r — asking to clarify.",
            intent.products,
            intent.question,
        )
        return question

    @staticmethod
    def _asks_for_comparison(question: str) -> bool:
        padded = f" {(question or '').lower()} "
        return any(keyword in padded for keyword in _COMPARISON_KEYWORDS)

    def check_zero_signal(self, intent: BusinessIntent) -> str | None:
        """Return a clarifying question when *intent* shows genuinely zero
        product/theme signal AND the question itself explicitly asks to be
        pointed to a solution/recommendation — never for the ambiguous
        two-product case above (that's ``check()``'s job, unchanged), and
        never for a normal informational question that simply doesn't
        match any known product (e.g. "What are your office hours?", or a
        question about an unlisted product name) — those must keep
        falling through to normal retrieval exactly as before.

        Deliberately a separate method, called by ChatOrchestrator
        *before* routing/retrieval even runs — ``check()`` still only ever
        runs after retrieval, inside AdvisoryResponseLayer.build().
        """
        if intent.confidence != "none":
            return None
        if intent.products:
            return None
        if not self._asks_for_recommendation(intent.question):
            return None

        logger.info(
            "ClarificationEngine: zero-signal recommendation ask %r — asking to clarify before searching.",
            intent.question,
        )
        return (
            "I'd love to point you to the right solution — could you tell me a "
            "bit more about the business problem you're trying to solve? For "
            "example: employee records, payroll, identity verification, "
            "expense management, HR/hiring, or something else?"
        )

    @staticmethod
    def _asks_for_recommendation(question: str) -> bool:
        padded = f" {(question or '').lower()} "
        return any(keyword in padded for keyword in _RECOMMENDATION_REQUEST_KEYWORDS)
