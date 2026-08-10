"""ProductRouter — classifies which named product a question is about.

Ha-Shem's knowledge base spans general company content plus multiple named
products (SPIDIFY, ZivaAIRA, ...). :class:`~.source_router.SourceRouter`
decides *where* to look (knowledge base vs. live web); this decides *which
product's* knowledge-base content is relevant, so retrieval can be scoped
to it instead of mixing every product's content together indiscriminately.

Pure keyword heuristics, same philosophy as SourceRouter — no I/O, no LLM,
deterministic and trivially testable. An explicit product-name mention
("SPIDIFY", "ZivaAIRA") always wins outright; otherwise it's classified by
intent keywords (e.g. "recruitment", "KYC"); if neither matches, a broader
business-theme fallback (e.g. "modernize our HR operations") can still
resolve to a cluster of relevant products — see ``business_themes``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Mapping, Sequence

from ...shared.business_themes import BUSINESS_THEMES, BusinessTheme
from ...shared.logging import get_logger
from .workspace_product_registry import get_product_registry

logger: logging.Logger = get_logger(__name__)


# Product name aliases and intent keywords are derived from the (currently
# single-workspace) product registry via get_product_registry() — the Phase
# 22 seam for a future per-workspace catalog (see workspace_product_registry.py)
# — the single source of truth also used by the crawl/metadata pipeline.
# Adding product #12 means adding one entry there, nothing here. Matching
# any alias mentions the product by name directly, taking priority over
# intent-keyword matching below.
_DEFAULT_PRODUCT_NAMES: dict[str, tuple[str, ...]] = {
    name: info["aliases"] for name, info in get_product_registry().items()
}

_DEFAULT_PRODUCT_KEYWORDS: dict[str, tuple[str, ...]] = {
    name: info["keywords"] for name, info in get_product_registry().items()
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
        primary:    When a business-theme match designates one product as
                    the primary recommendation (the rest being
                    complementary), its name — otherwise ``None``, meaning
                    either no theme matched, or the theme's products are
                    parallel/equally-weighted recommendations with no
                    single dominant one.
        via_theme:  ``True`` when ``products`` came from a business-theme
                    fallback match rather than an explicit product name or
                    a single product's own intent keywords. Lets callers
                    add business-recommendation framing (primary vs.
                    complementary, or "these solutions together cover...")
                    only for genuine business-need questions — not for an
                    ordinary "compare X and Y" naming two products.
    """

    products: tuple[str, ...] = ()
    confidence: str = "none"
    primary: str | None = None
    via_theme: bool = False

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
        business_themes: ``{theme: {"keywords", "products", "primary"}}`` —
            broader business-need phrases resolving to a product cluster,
            checked only when neither of the above finds anything. Defaults
            to ``BUSINESS_THEMES`` (see ``shared.business_themes``).

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
        business_themes: Mapping[str, BusinessTheme] | None = None,
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
        self._business_themes: Mapping[str, BusinessTheme] = (
            business_themes if business_themes is not None else BUSINESS_THEMES
        )

        logger.info(
            "ProductRouter ready (products=%s, themes=%d).",
            sorted(set(self._product_names) | set(self._product_keywords)),
            len(self._business_themes),
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
        if matched:
            products = tuple(sorted(matched))
            confidence = "high" if len(products) == 1 else "ambiguous"
            logger.info("ProductRouter: %r matched %s (%s).", question, products, confidence)
            return ProductMatch(products=products, confidence=confidence)

        theme_match = self._match_business_theme(cleaned)
        if theme_match is not None:
            theme_name, theme = theme_match
            logger.info(
                "ProductRouter: %r matched business theme %r -> %s (primary=%s).",
                question, theme_name, theme["products"], theme["primary"],
            )
            return ProductMatch(
                products=theme["products"], confidence="ambiguous",
                primary=theme["primary"], via_theme=True,
            )

        logger.info("ProductRouter: no product signal in %r.", question)
        return ProductMatch()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _matches_any(text: str, phrases: tuple[str, ...]) -> bool:
        return any(phrase in text for phrase in phrases)

    def _match_business_theme(self, cleaned: str) -> tuple[str, BusinessTheme] | None:
        """Return the first matching ``(theme_name, theme)`` for *cleaned*,
        or ``None``. Themes are checked in registry order; ties are
        resolved by first-match rather than merged, since two themes both
        matching the same question is expected to be rare and picking one
        deterministically is preferable to conflating their product sets."""
        for theme_name, theme in self._business_themes.items():
            if self._matches_any(cleaned, theme["keywords"]):
                return theme_name, theme
        return None
