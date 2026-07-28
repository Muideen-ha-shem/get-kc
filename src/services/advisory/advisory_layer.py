"""AdvisoryResponseLayer — the optional enrichment stage that turns a
grounded chat pipeline into a business advisor.

Sits between retrieval (``SearchManager``) and generation
(``ResponseGenerator``) in ``ChatOrchestrator``: takes the question and its
evidence, and returns everything needed to (a) short-circuit with a
clarifying question when intent is genuinely ambiguous, or (b) tell
``ResponseGenerator`` which product to frame as primary/complementary and
what next actions to attach to the response. Optional and purely additive —
when not injected, ``ChatOrchestrator`` behaves exactly as it did before
this phase.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Sequence

from ...shared.logging import get_logger
from .analytics_service import AnalyticsService, record_safely
from .clarification_engine import ClarificationEngine
from .intent_engine import BusinessIntent, BusinessIntentEngine
from .next_actions import NextAction, NextActionsEngine
from .recommendation_engine import Recommendation, RecommendationEngine

logger: logging.Logger = get_logger(__name__)


@dataclass(frozen=True)
class AdvisoryResult:
    intent: BusinessIntent
    clarification: str | None = None
    recommendations: list[Recommendation] = field(default_factory=list)
    next_actions: list[NextAction] = field(default_factory=list)

    @property
    def needs_clarification(self) -> bool:
        return self.clarification is not None

    @property
    def primary_product(self) -> str | None:
        """The lead product for response framing, or ``None`` when there
        genuinely isn't one — a business theme with no single dominant
        product (e.g. company-wide digital transformation touching 7
        unrelated departments) must **not** silently pick whichever
        product happens to be listed first in that theme's tuple; that's
        an arbitrary registry ordering, not a real recommendation."""
        if self.intent.primary:
            return self.intent.primary
        if not self.intent.via_theme and self.recommendations:
            return self.recommendations[0].product
        return None

    @property
    def complementary_products(self) -> list[str]:
        """Products to frame alongside ``primary_product`` — the rest of
        the recommendation list when there's a primary, or *every*
        recommended product when this is a parallel, no-primary theme
        bundle (so ResponseGenerator still gets the "no single dominant
        one" framing instead of no framing at all)."""
        primary = self.primary_product
        if primary is not None:
            return [r.product for r in self.recommendations if r.product != primary]
        if self.intent.via_theme:
            return [r.product for r in self.recommendations]
        return []


class AdvisoryResponseLayer:
    """Coordinates intent detection, clarification, recommendations, and
    next-action generation for one question.

    Every sub-component is independently injectable (defaults to a real
    instance of each) so this can be tested as a unit or with any piece
    swapped for a mock/stub.
    """

    def __init__(
        self,
        *,
        intent_engine: BusinessIntentEngine | None = None,
        recommendation_engine: RecommendationEngine | None = None,
        clarification_engine: ClarificationEngine | None = None,
        next_actions_engine: NextActionsEngine | None = None,
        analytics: AnalyticsService | None = None,
    ) -> None:
        self._intent_engine = intent_engine or BusinessIntentEngine()
        self._recommendation_engine = recommendation_engine or RecommendationEngine()
        self._clarification_engine = clarification_engine or ClarificationEngine()
        self._next_actions_engine = next_actions_engine or NextActionsEngine()
        self._analytics = analytics
        logger.info("AdvisoryResponseLayer ready (analytics=%s).", "enabled" if analytics else "disabled")

    def build(
        self,
        question: str,
        evidence: Sequence[Any] | None,
        *,
        product_match: Any = None,
    ) -> AdvisoryResult:
        """Build the advisory context for *question*.

        Args:
            question: The user's natural-language message.
            evidence: The retrieved evidence for this question (a list of
                objects with a ``.url`` attribute, e.g. ``EvidenceItem``),
                used to ground recommendations — pass ``None``/empty if
                retrieval hasn't run (e.g. clarification may still fire on
                intent alone).
            product_match: An already-computed ``ProductMatch`` (e.g. from
                ``SearchManager.product_match``) to enrich instead of
                re-classifying the question. When ``None``, the intent
                engine classifies it fresh.
        """
        try:
            intent = (
                self._intent_engine.enrich(question, product_match)
                if product_match is not None
                else self._intent_engine.detect(question)
            )
        except Exception as exc:
            logger.warning("AdvisoryResponseLayer: intent detection failed — %s.", exc)
            return AdvisoryResult(intent=BusinessIntent(question=question))

        clarification = self._safe_clarification(intent)
        if clarification is not None:
            return AdvisoryResult(intent=intent, clarification=clarification)

        recommendations = self._safe_recommendations(intent, evidence)
        next_actions = self._safe_next_actions(intent, recommendations)

        for rec in recommendations:
            record_safely(self._analytics, "record_recommendation", rec.product)
        if len(intent.products) >= 2:
            record_safely(self._analytics, "record_comparison", list(intent.products))
        for category in intent.categories:
            record_safely(self._analytics, "record_business_problem", category)

        return AdvisoryResult(
            intent=intent,
            clarification=None,
            recommendations=recommendations,
            next_actions=next_actions,
        )

    # ------------------------------------------------------------------
    # Failure-isolated sub-steps — a bug in one advisory stage degrades to
    # "skip that enrichment", never breaks the chat response.
    # ------------------------------------------------------------------

    def _safe_clarification(self, intent: BusinessIntent) -> str | None:
        try:
            return self._clarification_engine.check(intent)
        except Exception as exc:
            logger.warning("AdvisoryResponseLayer: clarification check failed — %s.", exc)
            return None

    def _safe_recommendations(self, intent: BusinessIntent, evidence: Sequence[Any] | None) -> list[Recommendation]:
        try:
            return self._recommendation_engine.recommend(intent, evidence)
        except Exception as exc:
            logger.warning("AdvisoryResponseLayer: recommendation build failed — %s.", exc)
            return []

    def _safe_next_actions(self, intent: BusinessIntent, recommendations: list[Recommendation]) -> list[NextAction]:
        try:
            return self._next_actions_engine.generate(intent, recommendations)
        except Exception as exc:
            logger.warning("AdvisoryResponseLayer: next-action generation failed — %s.", exc)
            return []
