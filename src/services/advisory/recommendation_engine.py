"""RecommendationEngine — turns a :class:`BusinessIntent` into ranked,
grounded product recommendations.

Grounding rule (the core anti-hallucination guarantee): a product is only
ever recommended if it's a real ``PRODUCT_REGISTRY`` entry, and its
recommendation text is built *exclusively* from registry fields (never
LLM-generated) — the "why" is always the product's own real
``business_problem`` string, not an invented explanation. Confidence is
downgraded when the matched product has no supporting evidence in the
current retrieval results (checked by resolving each evidence item's URL
back to a product via the same ``product_metadata_for_url`` used by the
crawl/upload pipeline — no new coupling to ContextMerger/EvidenceItem
needed for this).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Sequence

from ...shared.logging import get_logger
from ...shared.product_registry import PRODUCT_REGISTRY
from .intent_engine import BusinessIntent

logger: logging.Logger = get_logger(__name__)


@dataclass(frozen=True)
class Recommendation:
    """One ranked, grounded product recommendation.

    Attributes:
        product:          The recommended product's name (a real
                          ``PRODUCT_REGISTRY`` key — never invented).
        confidence:        ``"high"``, ``"medium"``, or ``"low"``.
        reason:            Why this product fits — built from the
                          registry's own ``business_problem`` text.
        primary_benefit:   The product's core business benefit (same
                          registry field, framed as a benefit statement).
        alternatives:      Other *competing* products the question could
                          also mean (only populated for a genuinely
                          ambiguous, non-theme match — e.g. two products
                          both named with no clear winner).
        related:           *Complementary* products from the same
                          business-theme bundle, if this came from one
                          (e.g. HR modernization's STAAS/PayCheq/etc.
                          alongside primary ZivaAIRA) — never competing
                          alternatives.
        grounded:          Whether the current retrieval evidence actually
                          contains this product's own content.
    """

    product: str
    confidence: str
    reason: str
    primary_benefit: str
    alternatives: tuple[str, ...] = ()
    related: tuple[str, ...] = ()
    grounded: bool = False


class RecommendationEngine:
    """Builds ranked recommendations from intent + retrieval evidence.

    Args:
        product_metadata_resolver: A callable ``url -> {"product": str|None, ...}``
            used to check whether a product's own content was actually
            retrieved. Defaults to
            ``scripts.product_metadata.product_metadata_for_url`` — the
            same URL→product resolver the crawl/upload pipeline uses, so
            grounding checks stay consistent with how content was tagged
            in the first place. Injectable for testing without importing
            the real crawler module.
    """

    def __init__(self, *, product_metadata_resolver: Any = None) -> None:
        if product_metadata_resolver is None:
            from scripts.product_metadata import product_metadata_for_url

            product_metadata_resolver = product_metadata_for_url
        self._resolve = product_metadata_resolver
        logger.info("RecommendationEngine ready.")

    def recommend(self, intent: BusinessIntent, evidence: Sequence[Any] | None = None) -> list[Recommendation]:
        """Return ranked recommendations for *intent*, grounded against
        *evidence* (a list of objects with a ``.url`` attribute, e.g.
        ``EvidenceItem`` — or ``None``/empty if retrieval hasn't run)."""
        if not intent.products:
            return []

        grounded_products = self._grounded_products(evidence or [])
        ordered = self._order_products(intent)

        recommendations: list[Recommendation] = []
        for product in ordered:
            info = PRODUCT_REGISTRY.get(product)
            if info is None:
                # Never recommend a product that isn't a real registry
                # entry — should be unreachable (ProductMatch only ever
                # returns registry keys), but this is the hard guardrail.
                continue

            is_primary = product == intent.primary or (intent.primary is None and product == ordered[0])
            grounded = product in grounded_products
            confidence = self._confidence_for(intent, is_primary, grounded)

            if intent.via_theme:
                alternatives: tuple[str, ...] = ()
                related = tuple(p for p in intent.products if p != product)
            elif intent.confidence == "ambiguous":
                alternatives = tuple(p for p in intent.products if p != product)
                related = ()
            else:
                alternatives = ()
                related = ()

            recommendations.append(
                Recommendation(
                    product=product,
                    confidence=confidence,
                    reason=f"{product} directly addresses: {info['business_problem']}.",
                    primary_benefit=info["business_problem"],
                    alternatives=alternatives,
                    related=related,
                    grounded=grounded,
                )
            )

        logger.info(
            "RecommendationEngine: %d recommendation(s) for %r (grounded=%s).",
            len(recommendations),
            intent.question,
            sorted(grounded_products),
        )
        return recommendations

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _grounded_products(self, evidence: Sequence[Any]) -> set[str]:
        grounded: set[str] = set()
        for item in evidence:
            url = getattr(item, "url", None)
            if not url:
                continue
            try:
                meta = self._resolve(url)
            except Exception as exc:
                logger.warning("RecommendationEngine: metadata resolution failed for %s — %s.", url, exc)
                continue
            product = meta.get("product") if isinstance(meta, dict) else None
            if product:
                grounded.add(product)
        return grounded

    @staticmethod
    def _order_products(intent: BusinessIntent) -> list[str]:
        if intent.primary and intent.primary in intent.products:
            rest = [p for p in intent.products if p != intent.primary]
            return [intent.primary, *rest]
        return list(intent.products)

    @staticmethod
    def _confidence_for(intent: BusinessIntent, is_primary: bool, grounded: bool) -> str:
        if intent.confidence == "high":
            return "high" if grounded else "medium"
        if intent.confidence == "ambiguous":
            if intent.via_theme:
                if is_primary:
                    return "high" if grounded else "medium"
                return "medium" if grounded else "low"
            return "medium" if grounded else "low"
        return "low"
