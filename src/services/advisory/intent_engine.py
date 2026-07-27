"""BusinessIntentEngine — understands *why* a customer is asking, not just
*what* they named.

``ProductRouter`` already does deterministic, keyword/theme-based product
classification (Phases 15-17) — this engine doesn't reimplement that (would
duplicate the same keyword tables ``ProductRouter`` already owns). Instead
it wraps a ``ProductRouter`` and enriches its raw ``ProductMatch`` with
human-readable business-problem context pulled from ``PRODUCT_REGISTRY``,
producing a result the rest of the advisory layer (RecommendationEngine,
ClarificationEngine, NextActionsEngine) can reason about without each of
them re-deriving the same registry lookups independently.

Pure, deterministic, no I/O, no LLM — same philosophy as SourceRouter and
ProductRouter.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from ...shared.logging import get_logger
from ...shared.product_registry import PRODUCT_REGISTRY
from ..routing.product_router import ProductMatch, ProductRouter

logger: logging.Logger = get_logger(__name__)


@dataclass(frozen=True)
class BusinessIntent:
    """A question's business intent, enriched with registry context.

    Attributes:
        question:          The original question.
        products:           Product(s) the question signals interest in —
                            copied from the underlying ``ProductMatch``.
        confidence:         ``"high"``, ``"ambiguous"``, or ``"none"``.
        primary:            Primary product recommendation, if the match
                            (typically a business-theme match) designates one.
        via_theme:          Whether this came from a broad business-theme
                            match rather than a direct name/keyword match.
        named_explicitly:   Whether the question itself contains the
                            matched product(s)' own name/alias text — e.g.
                            "Compare AppManage and Havis eCertify" names
                            both deliberately, versus a need-phrased
                            question that happens to match a product's
                            intent keywords without naming it. Distinguishes
                            a deliberate multi-product request (never
                            ambiguous — the user knows exactly what they
                            asked for) from genuine uncertainty about which
                            product fits; see ``ClarificationEngine``.
        business_problems:  Human-readable business-problem descriptions
                            (``PRODUCT_REGISTRY[...]["business_problem"]``)
                            for each matched product, in the same order as
                            ``products`` — real registry text, never invented.
        categories:         The matched products' registry categories, same
                            order as ``products``.
    """

    question: str
    products: tuple[str, ...] = ()
    confidence: str = "none"
    primary: str | None = None
    via_theme: bool = False
    named_explicitly: bool = False
    business_problems: tuple[str, ...] = field(default_factory=tuple)
    categories: tuple[str, ...] = field(default_factory=tuple)

    def any_active(self) -> bool:
        return len(self.products) > 0


class BusinessIntentEngine:
    """Detects business intent from a natural-language question.

    Args:
        product_router: A :class:`~services.routing.ProductRouter` instance.
            If ``None``, a default one is created (same defaults ProductRouter
            itself uses — derived from ``PRODUCT_REGISTRY``).

    Typical usage::

        engine = BusinessIntentEngine()
        intent = engine.detect("I need to automate employee attendance.")
        intent.products      # -> ("STAAS",)
        intent.confidence    # -> "high"
    """

    def __init__(self, *, product_router: ProductRouter | None = None) -> None:
        self._product_router = product_router or ProductRouter()
        logger.info("BusinessIntentEngine ready (product_router=%s).", type(self._product_router).__name__)

    def detect(self, question: str) -> BusinessIntent:
        """Detect business intent from *question*. Never raises — a blank
        question resolves to a blank :class:`BusinessIntent`."""
        match = self._product_router.classify(question)
        return self.enrich(question, match)

    def enrich(self, question: str, match: ProductMatch) -> BusinessIntent:
        """Build a :class:`BusinessIntent` from an already-computed
        :class:`ProductMatch` (avoids re-classifying when a caller — e.g.
        ``SearchManager`` — already has one from the same question)."""
        business_problems = tuple(
            PRODUCT_REGISTRY[p]["business_problem"] for p in match.products if p in PRODUCT_REGISTRY
        )
        categories = tuple(
            PRODUCT_REGISTRY[p]["category"] for p in match.products if p in PRODUCT_REGISTRY
        )
        return BusinessIntent(
            question=question,
            products=match.products,
            confidence=match.confidence,
            primary=match.primary,
            via_theme=match.via_theme,
            named_explicitly=self._is_named_explicitly(question, match.products),
            business_problems=business_problems,
            categories=categories,
        )

    @staticmethod
    def _is_named_explicitly(question: str, products: tuple[str, ...]) -> bool:
        """True if *question* itself contains any matched product's own
        name/alias text (e.g. "Compare AppManage and Havis eCertify" names
        both deliberately) rather than only matching via intent keywords."""
        lowered = question.lower()
        return any(
            alias in lowered
            for product in products
            if product in PRODUCT_REGISTRY
            for alias in PRODUCT_REGISTRY[product]["aliases"]
        )
