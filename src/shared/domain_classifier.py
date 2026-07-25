"""domain_classifier — shared domain-authority/quality tier classification.

Used by both :class:`~services.ranking.SourceRanker` (ranks already-merged
evidence) and :class:`~services.filtering.DomainQualityFilter` (filters and
prioritises URLs *before* they're fetched), so the notion of "official site
> vendor documentation > trusted news > social media > low-quality" lives in
exactly one place instead of being duplicated across both.
"""

from __future__ import annotations

from typing import Sequence
from urllib.parse import urlparse


class DomainTier:
    """String constants for each recognised domain tier."""

    OFFICIAL = "official"
    VENDOR_DOCS = "vendor_docs"
    TRUSTED_NEWS = "trusted_news"
    SOCIAL_MEDIA = "social_media"
    LOW_QUALITY = "low_quality"
    DEFAULT = "default"


_DOCUMENTATION_HINTS: tuple[str, ...] = ("docs.", "documentation.", "developer.", "wiki.", "help.")

# Well-known vendor documentation domains (Tier 2 in the domain-quality spec:
# official vendor docs for products/services commonly referenced alongside
# an enterprise IT company's own offerings).
_VENDOR_DOC_DOMAINS: frozenset[str] = frozenset({
    "learn.microsoft.com", "docs.microsoft.com", "microsoft.com",
    "aws.amazon.com", "docs.aws.amazon.com",
    "solarwinds.com", "support.solarwinds.com",
    "cisco.com", "developer.cisco.com",
})

_TRUSTED_NEWS_DOMAINS: frozenset[str] = frozenset({
    "reuters.com", "apnews.com", "bloomberg.com", "bbc.com", "bbc.co.uk",
    "techcrunch.com", "forbes.com", "businessday.ng", "punchng.com",
    "thisdaylive.com", "guardian.ng", "premiumtimesng.com", "nairametrics.com",
    "techcabal.com", "vanguardngr.com", "cio.com",
})

_SOCIAL_MEDIA_DOMAINS: frozenset[str] = frozenset({
    "facebook.com", "instagram.com", "twitter.com", "x.com", "tiktok.com",
    "linkedin.com", "youtube.com", "threads.net", "pinterest.com",
})

# Generic definition/Q&A sites that are almost never a useful source for an
# enterprise support chatbot, even though they frequently rank highly in
# generic web search results for short/ambiguous queries.
_LOW_QUALITY_DOMAINS: frozenset[str] = frozenset({
    "merriam-webster.com", "dictionary.com", "wiktionary.org",
    "quora.com", "answers.com", "vocabulary.com", "thefreedictionary.com",
    "urbandictionary.com", "wikihow.com", "yourdictionary.com",
    "collinsdictionary.com", "dictionary.cambridge.org", "oxfordlearnersdictionaries.com",
    "macmillandictionary.com", "ldoceonline.com",
})


def extract_domain(url: str) -> str:
    """Return the lowercased, ``www.``-stripped netloc of *url*, or ``""``."""
    if not url:
        return ""
    try:
        netloc = urlparse(url).netloc.lower()
    except Exception:
        return ""
    return netloc[4:] if netloc.startswith("www.") else netloc


def matches_any(domain: str, candidates: Sequence[str]) -> bool:
    """True if *domain* equals or is a subdomain of any entry in *candidates*."""
    return any(domain == c or domain.endswith("." + c) for c in candidates)


def classify_domain(
    domain: str,
    *,
    official_domains: Sequence[str] = (),
    extra_low_quality_domains: Sequence[str] = (),
) -> str:
    """Classify *domain* into one of :class:`DomainTier`'s tiers.

    Args:
        domain: A bare domain (e.g. ``"ha-shem.com"``), typically from
            :func:`extract_domain`.
        official_domains: This deployment's own domain(s) — always
            classified as :attr:`DomainTier.OFFICIAL` when matched, taking
            priority over every other tier.
        extra_low_quality_domains: Additional domains to treat as
            :attr:`DomainTier.LOW_QUALITY`, on top of the built-in list.

    Returns:
        One of the :class:`DomainTier` constants.
    """
    if not domain:
        return DomainTier.DEFAULT
    if official_domains and matches_any(domain, official_domains):
        return DomainTier.OFFICIAL
    if extra_low_quality_domains and matches_any(domain, extra_low_quality_domains):
        return DomainTier.LOW_QUALITY
    if matches_any(domain, _LOW_QUALITY_DOMAINS):
        return DomainTier.LOW_QUALITY
    if any(domain.startswith(hint) for hint in _DOCUMENTATION_HINTS) or matches_any(domain, _VENDOR_DOC_DOMAINS):
        return DomainTier.VENDOR_DOCS
    if matches_any(domain, _SOCIAL_MEDIA_DOMAINS):
        return DomainTier.SOCIAL_MEDIA
    if matches_any(domain, _TRUSTED_NEWS_DOMAINS):
        return DomainTier.TRUSTED_NEWS
    return DomainTier.DEFAULT
