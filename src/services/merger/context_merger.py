"""ContextMerger — combines evidence from multiple retrievers into a unified context.

This module provides two main exports:

* :class:`EvidenceItem` — a normalised representation of a single piece of
  evidence, regardless of which retriever produced it.
* :class:`ContextMerger` — the merger itself, which deduplicates, ranks, and
  merges evidence into a single context suitable for the language model.

Unified evidence model
----------------------
The existing retrievers produce different shapes:

  +--------------------+-------------------------------------------+
  | Retriever          | Output shape                              |
  +--------------------+-------------------------------------------+
  | KnowledgeService   | ``list[dict]`` with keys ``chunk_content``,|
  |                    | ``parent_url``, ``similarity``            |
  +--------------------+-------------------------------------------+
  | SearchService      | ``list[SearchResult]`` with ``title``,    |
  |                    | ``url``, ``snippet``, ``source``, ``score``|
  +--------------------+-------------------------------------------+
  | PageFetcher + RAG  | ``list[ChunkResult]`` with ``text``,      |
  |                    | ``score``, ``source_idx``                 |
  +--------------------+-------------------------------------------+

The :class:`EvidenceItem` normalises these into one shape so downstream
consumers (prompt assemblers, answer generators) never need to know which
retriever produced the evidence.

Deduplication strategy
----------------------
1. **Exact-URL dedup**: If two items share the same resolved URL, the one
   with the higher score is kept.
2. **Near-duplicate text**: Items whose text cosine-similarity (via a simple
   character n-gram overlap heuristic) exceeds a threshold are collapsed.
   This catches cases where the same paragraph appears in slightly different
   formatting from the KB and the live web.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Sequence

from ...shared.logging import get_logger

logger: logging.Logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Tags that indicate a query is asking for recent/fresh information.
# Items from live-web sources get a freshness boost when these are present.
_FRESHNESS_KEYWORDS: frozenset[str] = frozenset({
    "latest", "recent", "current", "today", "yesterday",
    "new", "newest", "newly", "breaking", "upcoming",
    "fresh", "updated", "update", "released", "launch",
})

# Boost multiplier applied to web-sourced evidence when freshness keywords
# are detected in the question.
_FRESHNESS_BOOST: float = 0.15

# Default similarity threshold for confidence-based filtering.
# Items below this threshold are considered low-confidence.
_CONFIDENCE_THRESHOLD: float = 0.50


# ---------------------------------------------------------------------------
# Domain model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceItem:
    """A single normalised piece of evidence from any retriever.

    Attributes:
        content:      The text content (chunk, snippet, or cleaned page).
        score:        Relevance score in ``[0, 1]``.  Items without a score
                      get ``0.0``.
        title:        Optional page/article title.
        url:          Optional source URL.
        source:       Human-readable label for where this came from
                      (e.g. ``"knowledge_base"``, ``"Tavily"``, ``"Brave"``).
        source_type:  Category tag — ``"knowledge_base"``, ``"web"``,
                      or ``"live_page"``.
        metadata:     Optional dict for extra attributes (chunk index,
                      page index, etc.).
    """

    content: str = ""
    score: float = 0.0
    title: str = ""
    url: str = ""
    source: str = ""
    source_type: str = ""
    metadata: dict[str, object] = field(default_factory=dict, compare=False)

    def __post_init__(self) -> None:
        # Ensure score is clamped to [0, 1]
        if self.score < 0.0 or self.score > 1.0:
            object.__setattr__(self, "score", max(0.0, min(1.0, self.score)))

    def to_dict(self) -> dict[str, object]:
        """Serialise to a JSON-safe dictionary."""
        return {
            "content": self.content,
            "score": round(self.score, 6),
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "source_type": self.source_type,
            "metadata": dict(self.metadata),
        }

    @property
    def content_preview(self) -> str:
        """Return the first 80 characters of ``content`` for logging."""
        return self.content[:80].replace("\n", " ") + ("..." if len(self.content) > 80 else "")


# ---------------------------------------------------------------------------
# ContextMerger
# ---------------------------------------------------------------------------

# Default separator used when joining evidence into a single context string.
_DEFAULT_SEPARATOR: str = "\n\n---\n\n"

# Score threshold for near-duplicate text detection (0 = identical, 1 = totally different).
# Two items whose bigram-overlap distance is below this threshold are considered
# near-duplicates and the lower-scored one is dropped.
_NGRAM_DUPS_THRESHOLD: float = 0.35

# Minimum content length (characters) for text-based near-duplicate detection.
# Short snippets are unlikely to be meaningful duplicates and would produce
# misleadingly high bigram scores (e.g. "Chunk 0" vs "Chunk 1").
_TEXT_DEDUP_MIN_LENGTH: int = 60


class ContextMerger:
    """Deduplicates, ranks, and merges evidence from multiple retrievers.

    Typical usage::

        from src.services.merger import ContextMerger

        merger = ContextMerger(
            max_evidence=10,
            min_score=0.15,
            dedup_url=True,
            dedup_text=True,
        )

        evidence = merger.merge(
            knowledge=knowledge_matches,
            web_search=search_results,
            live_pages=rag_chunks,
        )

        # Consume as a combined text block
        prompt_context = merger.merge_to_text(...)

        # Or iterate over individual items
        for item in evidence:
            print(f"[{item.source_type}] {item.score:.2f} {item.url}")
    """

    def __init__(
        self,
        max_evidence: int = 10,
        min_score: float = 0.0,
        dedup_url: bool = True,
        dedup_text: bool = True,
        ngram_threshold: float = _NGRAM_DUPS_THRESHOLD,
    ) -> None:
        """Initialise the context merger.

        Args:
            max_evidence:   Maximum number of evidence items to keep after
                            merging (capped after dedup and ranking).
            min_score:      Minimum score threshold.  Items below this are
                            discarded before merging.  ``0.0`` keeps everything.
            dedup_url:      Whether to collapse items sharing the same URL.
            dedup_text:     Whether to collapse near-duplicate text items.
            ngram_threshold: Bigram-overlap threshold for text dedup
                            (lower = stricter, 0.35 default).
        """
        self._max_evidence = max(1, max_evidence)
        self._min_score = min_score
        self._dedup_url = dedup_url
        self._dedup_text = dedup_text
        self._ngram_threshold = ngram_threshold

        logger.info(
            "ContextMerger ready (max_evidence=%d, min_score=%.2f, dedup_url=%s, dedup_text=%s).",
            self._max_evidence,
            self._min_score,
            self._dedup_url,
            self._dedup_text,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def merge(
        self,
        knowledge: Sequence[Any] | None = None,
        web_search: Sequence[Any] | None = None,
        live_pages: Sequence[Any] | None = None,
        *,
        question: str | None = None,
    ) -> list[EvidenceItem]:
        """Merge evidence from up to three retriever outputs.

        Args:
            knowledge:   Output of ``KnowledgeService.retrieve_context()``;
                         a list of dicts with keys like ``chunk_content``,
                         ``parent_url``, ``similarity``.
            web_search:  Output of ``SearchService.search()``; a list of
                         ``SearchResult`` objects (or anything with ``title``,
                         ``url``, ``snippet``, ``score`` attributes).
            live_pages:  Output of an ephemeral RAG retriever; a list of
                         objects with ``text``, ``score``, and optional
                         ``source_idx`` / ``chunk_idx`` attributes.
            question:    The original user question.  When provided, it is
                         used to apply freshness-based scoring boosts for
                         time-sensitive queries.

        Returns:
            A list of :class:`EvidenceItem` ordered by score descending
            (most relevant first), capped at ``max_evidence``.
        """
        all_evidence: list[EvidenceItem] = []

        # Detect if the question is time-sensitive (freshness keywords)
        needs_freshness = self._detect_freshness(question)

        # --- Ingest from knowledge base ---
        if knowledge:
            for match in knowledge:
                item = self._from_knowledge_match(match)
                if item and item.score >= self._min_score:
                    all_evidence.append(item)

        # --- Ingest from web search ---
        if web_search:
            for result in web_search:
                item = self._from_search_result(result)
                if item and item.score >= self._min_score:
                    all_evidence.append(item)

        # --- Ingest from live page chunks ---
        if live_pages:
            for chunk in live_pages:
                item = self._from_live_chunk(chunk)
                if item and item.score >= self._min_score:
                    all_evidence.append(item)

        if not all_evidence:
            logger.info("ContextMerger.merge: no evidence provided — returning empty.")
            return []

        logger.info(
            "ContextMerger.merge: %d raw items before dedup (freshness=%s).",
            len(all_evidence),
            needs_freshness,
        )

        # --- Deduplicate ---
        all_evidence = self._deduplicate(all_evidence)

        # --- Apply freshness boost when query is time-sensitive ---
        if needs_freshness:
            boosted: list[EvidenceItem] = []
            for item in all_evidence:
                # Web and live-page sources get a freshness boost
                if item.source_type in ("web", "live_page"):
                    new_score = min(1.0, item.score + _FRESHNESS_BOOST)
                    logger.debug(
                        "ContextMerger: freshness boost applied to %s item "
                        "(score %.4f → %.4f, url=%s).",
                        item.source_type,
                        item.score,
                        new_score,
                        item.url or "(no url)",
                    )
                    boosted.append(
                        EvidenceItem(
                            content=item.content,
                            score=new_score,
                            title=item.title,
                            url=item.url,
                            source=item.source,
                            source_type=item.source_type,
                            metadata=item.metadata,
                        )
                    )
                else:
                    boosted.append(item)
            all_evidence = boosted

        # --- Sort by score descending ---
        all_evidence.sort(key=lambda e: e.score, reverse=True)

        # --- Cap at max_evidence ---
        result = all_evidence[: self._max_evidence]

        logger.info(
            "ContextMerger.merge: returning %d items (capped at %d, %d deduped).",
            len(result),
            self._max_evidence,
            len(all_evidence) - len(result),
        )
        return result

    def merge_to_text(
        self,
        knowledge: Sequence[Any] | None = None,
        web_search: Sequence[Any] | None = None,
        live_pages: Sequence[Any] | None = None,
        separator: str = _DEFAULT_SEPARATOR,
    ) -> str:
        """Merge evidence and return a single joined text block.

        This is the most common entry point when building an LLM prompt.

        Args:
            knowledge:  See :meth:`merge`.
            web_search: See :meth:`merge`.
            live_pages: See :meth:`merge`.
            separator:  String to join individual evidence texts.

        Returns:
            A single string concatenating all evidence content, or an empty
            string if no evidence survives filtering.
        """
        items = self.merge(knowledge=knowledge, web_search=web_search, live_pages=live_pages)
        return separator.join(item.content for item in items) if items else ""

    # ------------------------------------------------------------------
    # Converters — normalise each retriever's output shape
    # ------------------------------------------------------------------

    @staticmethod
    def _from_knowledge_match(match: dict[str, Any]) -> EvidenceItem | None:
        """Convert a knowledge-base match dict to an ``EvidenceItem``."""
        content: str = (match.get("chunk_content") or "").strip()
        if not content:
            return None
        return EvidenceItem(
            content=content,
            score=float(match.get("similarity", 0.0)),
            url=str(match.get("parent_url", "")),
            source="knowledge_base",
            source_type="knowledge_base",
            metadata={"match_index": match.get("id")} if "id" in match else {},
        )

    @staticmethod
    def _from_search_result(result: Any) -> EvidenceItem | None:
        """Convert a ``SearchResult`` (or duck-typed equivalent) to ``EvidenceItem``."""
        snippet = getattr(result, "snippet", None)
        if snippet is None and isinstance(result, dict):
            snippet = result.get("snippet", "")
        snippet = (snippet or "").strip()
        if not snippet:
            return None

        score = getattr(result, "score", None)
        if score is None and isinstance(result, dict):
            score = result.get("score")
        score = float(score) if score is not None else 0.0

        title = getattr(result, "title", "")
        if not title and isinstance(result, dict):
            title = result.get("title", "")

        url = getattr(result, "url", "")
        if not url and isinstance(result, dict):
            url = result.get("url", "")

        source = getattr(result, "source", "")
        if not source and isinstance(result, dict):
            source = result.get("source", "")

        return EvidenceItem(
            content=snippet,
            score=score,
            title=str(title),
            url=str(url),
            source=str(source) or "web_search",
            source_type="web",
        )

    @staticmethod
    def _from_live_chunk(chunk: Any) -> EvidenceItem | None:
        """Convert an ephemeral RAG chunk result to an ``EvidenceItem``."""
        text = getattr(chunk, "text", None)
        if text is None and isinstance(chunk, dict):
            text = chunk.get("text", "")
        text = (text or "").strip()
        if not text:
            return None

        score = getattr(chunk, "score", None)
        if score is None and isinstance(chunk, dict):
            score = chunk.get("score")
        score = float(score) if score is not None else 0.0

        source_idx = getattr(chunk, "source_idx", None)
        if source_idx is None and isinstance(chunk, dict):
            source_idx = chunk.get("source_idx")
        chunk_idx = getattr(chunk, "chunk_idx", None)
        if chunk_idx is None and isinstance(chunk, dict):
            chunk_idx = chunk.get("chunk_idx")

        metadata: dict[str, object] = {}
        if source_idx is not None:
            metadata["source_idx"] = source_idx
        if chunk_idx is not None:
            metadata["chunk_idx"] = chunk_idx

        return EvidenceItem(
            content=text,
            score=score,
            source="live_page",
            source_type="live_page",
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    def _deduplicate(self, items: list[EvidenceItem]) -> list[EvidenceItem]:
        """Remove duplicates from *items*, keeping the higher-scored copy.

        Two passes:
        1. URL-based dedup — items with the same non-empty URL.
        2. Text-based dedup — items whose bigram-overlap exceeds threshold.
        """
        if self._dedup_url:
            items = self._dedup_by_url(items)
        if self._dedup_text:
            items = self._dedup_by_text(items)
        return items

    @staticmethod
    def _dedup_by_url(items: list[EvidenceItem]) -> list[EvidenceItem]:
        """Collapse items that share the same URL.

        For each unique URL, only the item with the highest score is kept.
        Items with an empty URL are always kept.
        """
        best_by_url: dict[str, EvidenceItem] = {}
        for item in items:
            if not item.url:
                # Keep all items without a URL (they won't be deduped here)
                continue
            existing = best_by_url.get(item.url)
            if existing is None or item.score > existing.score:
                best_by_url[item.url] = item

        # Rebuild the list: items without URL + best per URL
        seen_urls: set[str] = set()
        result: list[EvidenceItem] = []
        for item in items:
            if not item.url:
                result.append(item)
            elif item.url not in seen_urls:
                seen_urls.add(item.url)
                if item.url in best_by_url:
                    result.append(best_by_url[item.url])
        return result

    def _dedup_by_text(self, items: list[EvidenceItem]) -> list[EvidenceItem]:
        """Collapse items whose text content is near-duplicate.

        Uses bigram-overlap similarity.  If two items have a score above
        ``_ngram_threshold``, the lower-scored one is dropped.

        Only items whose content exceeds ``_TEXT_DEDUP_MIN_LENGTH`` characters
        are compared — short snippets are passed through unchanged since their
        bigram sets are often misleadingly similar by chance.
        """
        if len(items) < 2:
            return items

        # Split into long-enough (candidates for comparison) and short (always kept)
        long_items = [e for e in items if len(e.content) >= _TEXT_DEDUP_MIN_LENGTH]
        short_items = [e for e in items if len(e.content) < _TEXT_DEDUP_MIN_LENGTH]

        if len(long_items) < 2:
            return items  # Nothing meaningful to compare

        # Sort descending so higher-scored items survive
        sorted_items = sorted(long_items, key=lambda e: e.score, reverse=True)
        keep: list[EvidenceItem] = [sorted_items[0]]

        for candidate in sorted_items[1:]:
            is_dup = False
            for kept in keep:
                sim = self._bigram_similarity(candidate.content, kept.content)
                if sim >= self._ngram_threshold:
                    is_dup = True
                    break
            if not is_dup:
                keep.append(candidate)

        return keep + short_items

    # ------------------------------------------------------------------
    # Text similarity (character bigram overlap)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Freshness detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_freshness(question: str | None) -> bool:
        """Return ``True`` if *question* contains freshness keywords.

        This is used by the merger to boost web-sourced evidence scores
        when the user is asking for recent or time-sensitive information.
        """
        if not question:
            return False
        q = question.lower()
        for kw in _FRESHNESS_KEYWORDS:
            if kw in q:
                logger.debug("ContextMerger: freshness keyword %r found in question.", kw)
                return True
        return False

    # ------------------------------------------------------------------
    # Confidence evaluation
    # ------------------------------------------------------------------

    @staticmethod
    def compute_knowledge_confidence(
        matches: Sequence[dict[str, Any]] | None,
    ) -> float:
        """Return a single confidence score in ``[0, 1]`` for knowledge matches.

        The score is the highest similarity among the matches, or ``0.0``
        if there are no matches.

        This is used by ``SearchManager`` for confidence-based routing:
        if confidence < threshold, live search is triggered as a fallback.
        """
        if not matches:
            return 0.0
        best = 0.0
        for match in matches:
            sim = match.get("similarity", 0.0)
            if isinstance(sim, (int, float)):
                best = max(best, float(sim))
        return best

    @staticmethod
    def _bigram_similarity(a: str, b: str) -> float:
        """Jaccard similarity of character bigrams between *a* and *b*.

        Returns a float in ``[0, 1]`` where 1 means identical bigram sets.
        This is a cheap, language-agnostic way to detect near-duplicates.
        """
        if not a and not b:
            return 1.0
        if not a or not b:
            return 0.0

        def bigrams(s: str) -> set[str]:
            # Normalise whitespace and lowercase for comparison
            norm = re.sub(r"\s+", " ", s.strip().lower())
            return {norm[i : i + 2] for i in range(len(norm) - 1)}

        big_a = bigrams(a)
        big_b = bigrams(b)
        if not big_a and not big_b:
            return 1.0
        if not big_a or not big_b:
            return 0.0

        intersection = big_a & big_b
        union = big_a | big_b
        return len(intersection) / len(union)