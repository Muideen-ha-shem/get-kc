"""DomainQualityFilter — tiers and filters URLs before PageFetcher downloads them.

``SearchManager`` gets a list of URLs back from live web search and, before
this component existed, fetched every one of them (up to
``live_page_max_fetch``) regardless of whether the domain was ever likely to
be useful. Search engines frequently surface generic dictionary/Q&A sites
for short or ambiguous queries (see ``PageFetcher``'s own logs: definition
pages from Wiktionary/Collins/Quora for a query that was actually about
company news) — fetching those wastes a network round-trip and PageFetcher's
retry budget for content that will never make it past ``ContextMerger``.

This filter uses the same tier classification as
:class:`~services.ranking.SourceRanker` (see
``shared.domain_classifier``) to drop known low-quality domains outright and
order the rest so the best candidates are fetched first — valuable when
``live_page_max_fetch`` caps how many URLs actually get downloaded.
"""

from __future__ import annotations

import logging
import os
from typing import Sequence

from ...shared.domain_classifier import DomainTier, classify_domain, extract_domain
from ...shared.logging import get_logger

logger: logging.Logger = get_logger(__name__)

# Tier ordering used to sort surviving URLs, best first.
_TIER_PRIORITY: dict[str, int] = {
    DomainTier.OFFICIAL: 0,
    DomainTier.VENDOR_DOCS: 1,
    DomainTier.TRUSTED_NEWS: 2,
    DomainTier.DEFAULT: 3,
    DomainTier.SOCIAL_MEDIA: 4,
}


class DomainQualityFilter:
    """Drops low-quality domains and prioritises the rest, before fetching.

    Args:
        official_domains: This deployment's own domain(s) — always kept and
            sorted first. Defaults to the ``OFFICIAL_DOMAINS`` environment
            variable (comma-separated), matching ``SourceRanker``.
        blocked_domains: Additional domains to drop outright, on top of the
            built-in low-quality list (generic dictionaries, Quora, etc.).
        block_social_media: When ``True`` (default ``False``), also drops
            social-media domains instead of just deprioritising them —
            useful for deployments that only want fetchable, citable pages.

    Typical usage::

        domain_filter = DomainQualityFilter(official_domains=["ha-shem.com"])
        urls_to_fetch = domain_filter.filter(candidate_urls)
    """

    def __init__(
        self,
        *,
        official_domains: Sequence[str] | None = None,
        blocked_domains: Sequence[str] | None = None,
        block_social_media: bool = False,
    ) -> None:
        self._official_domains: tuple[str, ...] = tuple(
            d.strip().lower()
            for d in (official_domains if official_domains is not None else os.getenv("OFFICIAL_DOMAINS", "").split(","))
            if d.strip()
        )
        self._blocked_domains: tuple[str, ...] = tuple(d.strip().lower() for d in (blocked_domains or ()) if d.strip())
        self._block_social_media = block_social_media

        logger.info(
            "DomainQualityFilter ready (official_domains=%s, blocked_domains=%d, block_social_media=%s).",
            self._official_domains or "(none)",
            len(self._blocked_domains),
            block_social_media,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def filter(self, urls: Sequence[str]) -> list[str]:
        """Drop low-quality URLs and order the rest by domain-authority tier.

        Args:
            urls: Candidate URLs, typically from live web search results,
                in their original (search-ranked) order.

        Returns:
            The surviving URLs, best tier first; original relative order is
            preserved within a tier (a stable sort). Never raises — an
            unparseable URL is treated as :attr:`DomainTier.DEFAULT` rather
            than dropped, since blocking on a filter bug would be worse
            than fetching one extra page.
        """
        if not urls:
            return []

        kept: list[str] = []
        dropped: list[str] = []
        for url in urls:
            tier = self._tier(url)
            if tier is None:
                dropped.append(url)
            else:
                kept.append(url)

        kept.sort(key=lambda u: _TIER_PRIORITY.get(self._tier(u), 99))

        logger.info(
            "DomainQualityFilter.filter: %d urls -> %d kept, %d dropped.",
            len(urls),
            len(kept),
            len(dropped),
        )
        if dropped:
            logger.info("DomainQualityFilter: dropped low-quality URLs: %s", dropped)
        return kept

    def should_fetch(self, url: str) -> bool:
        """True if *url*'s domain is not blocked/low-quality."""
        return self._tier(url) is not None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _tier(self, url: str) -> str | None:
        """Return the domain's tier, or ``None`` if it should be dropped."""
        domain = extract_domain(url)
        tier = classify_domain(
            domain,
            official_domains=self._official_domains,
            extra_low_quality_domains=self._blocked_domains,
        )
        if tier == DomainTier.LOW_QUALITY:
            return None
        if tier == DomainTier.SOCIAL_MEDIA and self._block_social_media:
            return None
        return tier
