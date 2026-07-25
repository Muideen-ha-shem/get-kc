"""SourceRanker — intelligent, multi-signal ranking of merged evidence.

Runs on the ``list[EvidenceItem]`` that :class:`~..merger.ContextMerger`
has already deduplicated and normalised from every retriever (knowledge
base, live web search, live pages), and hands back a re-ordered, trimmed
list for :class:`~..generator.ResponseGenerator`. ContextMerger already
answers "is this evidence usable" (dedup, minimum-score threshold, a
freshness boost); SourceRanker answers "which usable evidence is actually
best", by combining signals ContextMerger does not compute — a source
*authority* tier (official site > documentation > trusted news > social
media) and a softer near-duplicate penalty — with the relevance, confidence,
and freshness signals already present on each item.

This does not change ``EvidenceItem`` or ``ContextMerger``'s contract: it
is a strict downstream refinement, consuming and returning
``list[EvidenceItem]``, and is wired in as one optional constructor
argument on ``SearchManager`` — when not injected, behaviour is unchanged
from before this component existed.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Sequence

from ...shared.domain_classifier import DomainTier, classify_domain, extract_domain
from ...shared.logging import get_logger
from ..merger.context_merger import EvidenceItem

logger: logging.Logger = get_logger(__name__)

_WORD_RE = re.compile(r"[a-z0-9]+")

# Source-authority weights per domain tier (see shared.domain_classifier),
# highest first. These are heuristic weights, not hard filters — a
# low-authority item can still win on relevance/freshness.
_AUTHORITY_KNOWLEDGE_BASE: float = 1.0
_AUTHORITY_BY_TIER: dict[str, float] = {
    DomainTier.OFFICIAL: 0.95,
    DomainTier.VENDOR_DOCS: 0.85,
    DomainTier.TRUSTED_NEWS: 0.7,
    DomainTier.DEFAULT: 0.55,
    DomainTier.SOCIAL_MEDIA: 0.4,
    DomainTier.LOW_QUALITY: 0.2,
}

# Same freshness vocabulary as ContextMerger's own freshness boost — kept as
# a local copy rather than imported, so this module doesn't reach into
# ContextMerger's private constants and the two stay independently testable.
_FRESHNESS_KEYWORDS: frozenset[str] = frozenset({
    "latest", "recent", "current", "today", "yesterday",
    "new", "newest", "newly", "breaking", "upcoming",
    "fresh", "updated", "update", "released", "launch",
})

_DEFAULT_WEIGHTS: dict[str, float] = {
    "relevance": 0.40,
    "authority": 0.25,
    "freshness": 0.15,
    "duplicate_penalty": 0.20,  # subtracted from the base score, not additive
}

_NEAR_DUP_NGRAM: int = 5
_DEFAULT_TOP_K: int = 10


class SourceRanker:
    """Re-scores and trims merged evidence using multiple weighted signals.

    Args:
        weights: Override any of ``relevance``, ``authority``, ``freshness``,
            ``duplicate_penalty``. Unspecified keys keep their default.
            Weights need not sum to 1 — they're relative, not normalised.
        official_domains: Domains that count as this deployment's own
            "official website" tier (e.g. ``["ha-shem.com"]``). Defaults to
            the ``OFFICIAL_DOMAINS`` environment variable (comma-separated)
            when not given, mirroring how other services in this codebase
            (e.g. ``ResponseGenerator``) fall back to environment
            configuration rather than requiring every caller to pass it.
        top_k: Maximum number of evidence items returned.

    Typical usage::

        ranker = SourceRanker(official_domains=["ha-shem.com"])
        best_evidence = ranker.rank(evidence, question="What's new at Ha-Shem?")
    """

    def __init__(
        self,
        *,
        weights: dict[str, float] | None = None,
        official_domains: Sequence[str] | None = None,
        top_k: int = _DEFAULT_TOP_K,
    ) -> None:
        self._weights: dict[str, float] = {**_DEFAULT_WEIGHTS, **(weights or {})}
        self._official_domains: tuple[str, ...] = tuple(
            d.strip().lower()
            for d in (official_domains if official_domains is not None else self._domains_from_env())
            if d.strip()
        )
        self._top_k = top_k

        logger.info(
            "SourceRanker ready (weights=%s, top_k=%d, official_domains=%s).",
            self._weights,
            top_k,
            self._official_domains or "(none)",
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def rank(
        self,
        evidence: Sequence[EvidenceItem],
        question: str | None = None,
    ) -> list[EvidenceItem]:
        """Re-score, reorder, and trim *evidence* to the best ``top_k`` items.

        Args:
            evidence: Already-merged, normalised evidence (typically the
                output of ``ContextMerger.merge()``).
            question: The original user question, used to detect whether
                freshness should be weighted (same "latest/recent/..."
                heuristic ContextMerger itself uses for its boost).

        Returns:
            Up to ``top_k`` ``EvidenceItem`` objects, ordered by composite
            score descending. Empty input returns an empty list.
        """
        if not evidence:
            return []

        needs_freshness = self._detect_freshness(question)

        base_scores = [
            self._base_score(item, needs_freshness) for item in evidence
        ]

        # Greedy selection, applying a near-duplicate penalty relative to
        # items already selected — ContextMerger already hard-deduplicates
        # near-identical text, so this is a softer secondary signal for
        # evidence that overlaps substantially without being an exact dup.
        order = sorted(range(len(evidence)), key=lambda i: base_scores[i], reverse=True)
        selected_texts: list[str] = []
        ranked: list[tuple[EvidenceItem, float]] = []
        for i in order:
            item = evidence[i]
            penalty = self._duplicate_penalty(item.content, selected_texts)
            final_score = max(0.0, base_scores[i] - self._weights["duplicate_penalty"] * penalty)
            ranked.append((item, final_score))
            selected_texts.append(item.content)

        ranked.sort(key=lambda pair: pair[1], reverse=True)
        top = ranked[: self._top_k]

        logger.info(
            "SourceRanker.rank: %d evidence items -> top %d returned (freshness_query=%s).",
            len(evidence),
            len(top),
            needs_freshness,
        )
        return [item for item, _score in top]

    # ------------------------------------------------------------------
    # Scoring signals
    # ------------------------------------------------------------------

    def _base_score(self, item: EvidenceItem, needs_freshness: bool) -> float:
        relevance = max(0.0, min(1.0, item.score))
        authority = self._source_authority(item)
        freshness = self._freshness_score(item, needs_freshness)
        return (
            self._weights["relevance"] * relevance
            + self._weights["authority"] * authority
            + self._weights["freshness"] * freshness
        )

    def _source_authority(self, item: EvidenceItem) -> float:
        if item.source_type == "knowledge_base":
            return _AUTHORITY_KNOWLEDGE_BASE

        domain = extract_domain(item.url)
        tier = classify_domain(domain, official_domains=self._official_domains)
        return _AUTHORITY_BY_TIER[tier]

    @staticmethod
    def _freshness_score(item: EvidenceItem, needs_freshness: bool) -> float:
        if not needs_freshness:
            return 0.5  # neutral when the question isn't time-sensitive
        return 1.0 if item.source_type in ("web", "live_page") else 0.3

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _domains_from_env() -> list[str]:
        raw = os.getenv("OFFICIAL_DOMAINS", "")
        return raw.split(",") if raw else []

    @staticmethod
    def _detect_freshness(question: str | None) -> bool:
        if not question:
            return False
        words = _WORD_RE.findall(question.lower())
        return any(w in _FRESHNESS_KEYWORDS for w in words)

    @staticmethod
    def _ngrams(text: str, n: int) -> set[str]:
        words = _WORD_RE.findall((text or "").lower())
        if len(words) < n:
            return {" ".join(words)} if words else set()
        return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}

    @classmethod
    def _duplicate_penalty(cls, text: str, already_selected: list[str]) -> float:
        """Max fractional n-gram overlap of *text* against any already-selected item."""
        if not text or not already_selected:
            return 0.0
        text_ngrams = cls._ngrams(text, _NEAR_DUP_NGRAM)
        if not text_ngrams:
            return 0.0
        max_overlap = 0.0
        for other in already_selected:
            other_ngrams = cls._ngrams(other, _NEAR_DUP_NGRAM)
            if not other_ngrams:
                continue
            overlap = len(text_ngrams & other_ngrams) / len(text_ngrams)
            max_overlap = max(max_overlap, overlap)
        return max_overlap
