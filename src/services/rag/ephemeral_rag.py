"""EphemeralRAG — lightweight, in-memory retrieval over freshly fetched web pages.

``SearchManager`` downloads raw HTML for the top live web-search results via
``PageFetcher`` and needs to turn that HTML into a handful of question-relevant
text chunks before handing them to ``ContextMerger``. This service does that
without persisting anything — it strips HTML, splits it into paragraphs
(reusing the same chunking helper as the ingestion pipeline), and scores
chunks by lexical word-overlap with the question, which is fast, free, and
works on every chunk from every page with no I/O.

Optionally, a :class:`~..rag.semantic_reranker.SemanticReranker` can be
injected to refine the ranking further: the cheap lexical pass first narrows
the field down to a bounded shortlist (``rerank_candidate_pool``), which is
then re-scored by embedding cosine similarity — bounding embedding-API cost
to a handful of calls per request instead of one per chunk on every page.
If no reranker is injected, or the reranker cannot produce a result (no
credentials, network failure, etc.), retrieval falls back to the lexical
ranking exactly as before — this is a strict, backward-compatible addition.
"""

from __future__ import annotations

import html as html_module
import logging
import re
from dataclasses import dataclass, field
from typing import Any

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
_DEFAULT_RERANK_CANDIDATE_POOL: int = 20


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
        semantic_reranker:    Optional :class:`~.semantic_reranker.SemanticReranker`.
                               When provided, the top ``rerank_candidate_pool``
                               lexically-scored chunks are re-scored by
                               embedding similarity before the final ``top_k``
                               is selected. When ``None`` (the default) or
                               when the reranker can't produce a result,
                               ranking is purely lexical — unchanged from
                               prior behaviour.
        rerank_candidate_pool: How many top lexical candidates to hand to
                               the semantic reranker. Bounds embedding-API
                               calls to a small shortlist regardless of how
                               many chunks were extracted. Ignored when no
                               ``semantic_reranker`` is set.

    Typical usage::

        rag = EphemeralRAG()
        chunks = rag.retrieve("What awards has the company won?", [html1, html2])

        # With semantic reranking:
        rag = EphemeralRAG(semantic_reranker=SemanticReranker())
        chunks = rag.retrieve("What awards has the company won?", [html1, html2])
    """

    def __init__(
        self,
        *,
        chunk_size: int = _DEFAULT_CHUNK_SIZE,
        max_chunks_per_page: int = _DEFAULT_MAX_CHUNKS_PER_PAGE,
        top_k: int = _DEFAULT_TOP_K,
        semantic_reranker: Any = None,
        rerank_candidate_pool: int = _DEFAULT_RERANK_CANDIDATE_POOL,
    ) -> None:
        self._chunk_size = chunk_size
        self._max_chunks_per_page = max_chunks_per_page
        self._top_k = top_k
        self._semantic_reranker = semantic_reranker
        self._rerank_candidate_pool = max(rerank_candidate_pool, top_k)

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
            Ranked semantically when a ``semantic_reranker`` was injected
            and succeeds; lexically otherwise.
        """
        query_terms = self._terms(question)
        if not query_terms or not pages:
            return []

        candidates: list[ChunkResult] = []
        for source_idx, page_html in enumerate(pages):
            text = self._extract_text(page_html)
            if not text:
                continue

            chunks = split_into_semantic_chunks(text, max_chunk_size=self._chunk_size)
            for chunk_idx, chunk_text in enumerate(chunks[: self._max_chunks_per_page]):
                score = self._score(query_terms, chunk_text)
                if score <= 0.0:
                    continue
                candidates.append(
                    ChunkResult(
                        text=chunk_text,
                        score=score,
                        source_idx=source_idx,
                        chunk_idx=chunk_idx,
                    )
                )

        if not candidates:
            logger.info(
                "EphemeralRAG.retrieve: %d pages -> 0 candidate chunks -> 0 returned.",
                len(pages),
            )
            return []

        candidates.sort(key=lambda c: c.score, reverse=True)
        shortlist = candidates[: self._rerank_candidate_pool]

        if self._semantic_reranker is not None:
            semantic_results = self._semantic_rank(question, shortlist)
            if semantic_results is not None:
                logger.info(
                    "EphemeralRAG.retrieve: %d pages -> %d candidate chunks -> "
                    "%d returned (semantic reranking).",
                    len(pages),
                    len(candidates),
                    len(semantic_results),
                )
                return semantic_results
            logger.warning(
                "EphemeralRAG.retrieve: semantic reranking unavailable — "
                "falling back to lexical ranking."
            )

        top_results = shortlist[: self._top_k]
        logger.info(
            "EphemeralRAG.retrieve: %d pages -> %d candidate chunks -> %d returned (lexical).",
            len(pages),
            len(candidates),
            len(top_results),
        )
        return top_results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _semantic_rank(
        self, question: str, shortlist: list[ChunkResult]
    ) -> list[ChunkResult] | None:
        """Re-score *shortlist* with the injected semantic reranker.

        Returns ``None`` (never raises) if the reranker is unavailable or
        fails, so the caller can fall back to the lexical shortlist as-is.
        """
        texts = [c.text for c in shortlist]
        try:
            ranked = self._semantic_reranker.rank(question, texts, top_k=self._top_k)
        except Exception as exc:
            logger.warning(
                "EphemeralRAG: semantic reranker raised %s — falling back to lexical.", exc
            )
            return None

        if ranked is None:
            return None

        return [
            ChunkResult(
                text=shortlist[index].text,
                score=score,
                source_idx=shortlist[index].source_idx,
                chunk_idx=shortlist[index].chunk_idx,
                metadata={"ranking": "semantic"},
            )
            for index, score in ranked
        ]

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
