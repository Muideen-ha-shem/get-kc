"""EphemeralRAG — lightweight, in-memory retrieval over freshly fetched web pages.

``SearchManager`` downloads raw HTML for the top live web-search results via
``PageFetcher`` and needs to turn that HTML into a handful of question-relevant
text chunks before handing them to ``ContextMerger``. This service does that
without persisting anything or calling an embedding API for throwaway,
one-shot content — it strips HTML, splits it into paragraphs (reusing the same
chunking helper as the ingestion pipeline), and ranks chunks by lexical
overlap with the question. That keeps live-page retrieval fast, dependency-free,
and proportionate to content that is used once and discarded.
"""

from __future__ import annotations

import html as html_module
import logging
import re
from dataclasses import dataclass, field

from ...chunk import split_into_semantic_chunks
from ...shared.logging import get_logger

logger: logging.Logger = get_logger(__name__)

_SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"[ \t\r\f\v]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")
_WORD_RE = re.compile(r"[a-z0-9]+")

_STOPWORDS: frozenset[str] = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "of", "to", "in", "on", "at", "for", "with", "and", "or", "but", "if",
    "as", "by", "from", "that", "this", "these", "those", "it", "its",
    "what", "when", "where", "who", "how", "why", "do", "does", "did",
    "can", "could", "will", "would", "should", "about", "into", "than",
})

_DEFAULT_CHUNK_SIZE: int = 600
_DEFAULT_MAX_CHUNKS_PER_PAGE: int = 20
_DEFAULT_TOP_K: int = 6


@dataclass(frozen=True)
class ChunkResult:
    """A single ranked text chunk extracted from a fetched page.

    Attributes:
        text:       The chunk's plain-text content.
        score:      Lexical-overlap relevance score in ``[0, 1]``.
        source_idx: Index of the source page (position in the ``pages`` list
                    passed to :meth:`EphemeralRAG.retrieve`).
        chunk_idx:  Index of this chunk within its source page.
    """

    text: str
    score: float
    source_idx: int
    chunk_idx: int
    metadata: dict[str, object] = field(default_factory=dict, compare=False)


class EphemeralRAG:
    """Ranks text chunks from freshly fetched HTML pages against a question.

    Args:
        chunk_size:           Max characters per chunk (paragraph-aware).
        max_chunks_per_page:  Cap on chunks considered per page, to bound
                               work on very long pages.
        top_k:                Maximum number of chunks returned overall.

    Typical usage::

        rag = EphemeralRAG()
        chunks = rag.retrieve("What awards has the company won?", [html1, html2])
    """

    def __init__(
        self,
        *,
        chunk_size: int = _DEFAULT_CHUNK_SIZE,
        max_chunks_per_page: int = _DEFAULT_MAX_CHUNKS_PER_PAGE,
        top_k: int = _DEFAULT_TOP_K,
    ) -> None:
        self._chunk_size = chunk_size
        self._max_chunks_per_page = max_chunks_per_page
        self._top_k = top_k

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve(self, question: str, pages: list[str]) -> list[ChunkResult]:
        """Extract and rank text chunks from *pages* relevant to *question*.

        Args:
            question: The user's natural-language question.
            pages:    Raw HTML strings, as returned by ``PageFetcher.fetch``.

        Returns:
            Up to ``top_k`` :class:`ChunkResult` objects, ordered by score
            descending. Empty if no page yields any overlapping content.
        """
        query_terms = self._terms(question)
        if not query_terms or not pages:
            return []

        results: list[ChunkResult] = []
        for source_idx, page_html in enumerate(pages):
            text = self._extract_text(page_html)
            if not text:
                continue

            chunks = split_into_semantic_chunks(text, max_chunk_size=self._chunk_size)
            for chunk_idx, chunk_text in enumerate(chunks[: self._max_chunks_per_page]):
                score = self._score(query_terms, chunk_text)
                if score <= 0.0:
                    continue
                results.append(
                    ChunkResult(
                        text=chunk_text,
                        score=score,
                        source_idx=source_idx,
                        chunk_idx=chunk_idx,
                    )
                )

        results.sort(key=lambda c: c.score, reverse=True)
        top_results = results[: self._top_k]

        logger.info(
            "EphemeralRAG.retrieve: %d pages -> %d candidate chunks -> top %d returned.",
            len(pages),
            len(results),
            len(top_results),
        )
        return top_results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text(page_html: str) -> str:
        """Strip tags/scripts/styles from raw HTML and normalise whitespace."""
        if not page_html:
            return ""
        text = _SCRIPT_STYLE_RE.sub(" ", page_html)
        text = _TAG_RE.sub("\n", text)
        text = html_module.unescape(text)
        text = _WHITESPACE_RE.sub(" ", text)
        text = _BLANK_LINES_RE.sub("\n\n", text)
        return text.strip()

    @classmethod
    def _terms(cls, text: str) -> set[str]:
        words = _WORD_RE.findall((text or "").lower())
        return {w for w in words if len(w) > 2 and w not in _STOPWORDS}

    @classmethod
    def _score(cls, query_terms: set[str], chunk_text: str) -> float:
        if not query_terms:
            return 0.0
        chunk_terms = cls._terms(chunk_text)
        if not chunk_terms:
            return 0.0
        overlap = len(query_terms & chunk_terms)
        return overlap / len(query_terms)
