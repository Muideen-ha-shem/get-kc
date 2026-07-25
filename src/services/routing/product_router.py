"""ProductRouter — classifies which named product a question is about.

Ha-Shem's knowledge base spans general company content plus multiple named
products (SPIDIFY, ZivaAIRA, ...). :class:`~.source_router.SourceRouter`
decides *where* to look (knowledge base vs. live web); this decides *which
product's* knowledge-base content is relevant, so retrieval can be scoped
to it instead of mixing every product's content together indiscriminately.

Pure keyword heuristics, same philosophy as SourceRouter — no I/O, no LLM,
deterministic and trivially testable. An explicit product-name mention
("SPIDIFY", "ZivaAIRA") always wins outright; otherwise it's classified by
intent keywords (e.g. "recruitment", "KYC").
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Mapping, Sequence

from ...shared.logging import get_logger

logger: logging.Logger = get_logger(__name__)


# Product name aliases — matching any of these mentions the product by name
# directly, taking priority over intent-keyword matching below.
_DEFAULT_PRODUCT_NAMES: dict[str, tuple[str, ...]] = {
    "SPIDIFY": ("spidify",),
    "ZivaAIRA": ("zivaaira", "ziva aira", "aira"),
}

# Intent keywords per product, from the SPIDIFY/ZivaAIRA intent-classification
# spec: recruitment/hiring/talent/HR -> ZivaAIRA; identity verification/KYC/
# secure access -> SPIDIFY. Phrases are used (rather than single ambiguous
# words like "onboarding" alone) to avoid false positives across products.
_DEFAULT_PRODUCT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "ZivaAIRA": (
        "recruitment", "recruit", "recruiting", "recruiter",
        "hiring", "hire", "hiring automation",
        "talent acquisition", "talent management",
        "hr management", "human resources", "hr workflow",
        "applicant tracking", "job applicants", "candidate screening",
        "interview scheduling", "onboarding employees", "onboard staff",
        "workforce management", "employee onboarding",
    ),
    "SPIDIFY": (
        "identity verification", "verify users", "verify identity",
        "user verification", "identity validation",
        "kyc", "know your customer",
        "secure access", "user authentication", "authentication",
        "compliance verification", "onboarding users", "onboard users",
        "verify customers", "customer verification", "secure onboarding",
    ),
}


@dataclass(frozen=True)
class ProductMatch:
    """The result of classifying a question against known products.

    Attributes:
        products:   Product name(s) the question signals interest in.
                    Empty when no product-specific signal was found (the
                    question is general/ambiguous — search everything).
        confidence: ``"high"`` (exactly one product matched, or named
                    explicitly), ``"ambiguous"`` (more than one product
                    matched), or ``"none"`` (no product signal at all).
    """

    products: tuple[str, ...] = ()
    confidence: str = "none"

    def any_active(self) -> bool:
        """True if a specific product was identified (mirrors RoutingDecision)."""
        return len(self.products) > 0


class ProductRouter:
    """Classifies a question against a configured set of named products.

    Args:
        product_names: ``{product: (alias, ...)}`` — mentioning any alias
            names that product directly, taking priority over keywords.
        product_keywords: ``{product: (keyword_phrase, ...)}`` — intent
            signals for that product.

    Typical usage::

        router = ProductRouter()
        match = router.classify("What cybersecurity services does SPIDIFY offer?")
        match.products      # -> ("SPIDIFY",)
        match.confidence    # -> "high"
    """

    def __init__(
        self,
        *,
        product_names: Mapping[str, Sequence[str]] | None = None,
        product_keywords: Mapping[str, Sequence[str]] | None = None,
    ) -> None:
        self._product_names: dict[str, tuple[str, ...]] = (
            {name: tuple(a.lower() for a in aliases) for name, aliases in product_names.items()}
            if product_names is not None
            else _DEFAULT_PRODUCT_NAMES
        )
        self._product_keywords: dict[str, tuple[str, ...]] = (
            {name: tuple(k.lower() for k in kws) for name, kws in product_keywords.items()}
            if product_keywords is not None
            else _DEFAULT_PRODUCT_KEYWORDS
        )

        logger.info(
            "ProductRouter ready (products=%s).",
            sorted(set(self._product_names) | set(self._product_keywords)),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify(self, question: str) -> ProductMatch:
        """Classify *question* against the configured products.

        Args:
            question: The user's natural-language question.

        Returns:
            A :class:`ProductMatch`. Never raises — a blank/empty question
            returns ``ProductMatch()`` (no product, "none" confidence)
            rather than erroring, since this is a soft retrieval hint, not
            a hard requirement.
        """
        cleaned = (question or "").strip().lower()
        if not cleaned:
            return ProductMatch()

        named = {
            product
            for product, aliases in self._product_names.items()
            if self._matches_any(cleaned, aliases)
        }
        if named:
            products = tuple(sorted(named))
            confidence = "high" if len(products) == 1 else "ambiguous"
            logger.info("ProductRouter: %r named %s directly (%s).", question, products, confidence)
            return ProductMatch(products=products, confidence=confidence)

        matched = {
            product
            for product, keywords in self._product_keywords.items()
            if self._matches_any(cleaned, keywords)
        }
        if not matched:
            logger.info("ProductRouter: no product signal in %r.", question)
            return ProductMatch()

        products = tuple(sorted(matched))
        confidence = "high" if len(products) == 1 else "ambiguous"
        logger.info("ProductRouter: %r matched %s (%s).", question, products, confidence)
        return ProductMatch(products=products, confidence=confidence)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _matches_any(text: str, phrases: tuple[str, ...]) -> bool:
        return any(phrase in text for phrase in phrases)
