"""SemanticReranker — embedding-based relevance scoring for text chunks.

``EphemeralRAG`` ranks live-page chunks by cheap lexical word-overlap first
(no I/O, works on hundreds of chunks instantly), then hands its top
candidates to this component to be re-scored by actual semantic similarity
(cosine similarity over Gemini embeddings) — a classic two-stage
retrieve-then-rerank pattern that bounds embedding-API cost/latency to a
small shortlist instead of every chunk on every page.

This is a best-effort enhancement, not a hard dependency: any failure to
embed the question or a chunk (missing API key, network error, rate limit)
returns ``None`` rather than raising, so callers fall back to their existing
lexical ranking and retrieval keeps working exactly as it did before this
component existed.

An optional ``cache`` (a ``TTLCache``-like object, see ``shared.cache``)
avoids re-embedding text that's already been seen — the same live page can
resurface across different questions/search results within a session, and
without caching each occurrence costs a fresh embedding call even though
the content, and therefore its embedding, is identical.
"""

from __future__ import annotations

import hashlib
import logging
import math
from typing import Any, Callable, Sequence

from ...shared.logging import get_logger

logger: logging.Logger = get_logger(__name__)

EmbedFn = Callable[[str], Sequence[float]]


class SemanticReranker:
    """Ranks text against a question using embedding cosine similarity.

    Args:
        embed_fn: A callable ``str -> Sequence[float]`` returning an
            embedding vector. Defaults to
            :func:`src.api.services.embeddings.embed_query` (Gemini,
            imported lazily so this module has no hard dependency on
            network/credentials at import time). Inject a stub for tests or
            to swap embedding providers.
        cache: An optional ``TTLCache``-like object (``get``/``set``) keyed
            by a hash of the embedded text. When given, identical text is
            never embedded twice for the lifetime of the cache entry.

    Typical usage::

        reranker = SemanticReranker()
        ranked = reranker.rank("What awards has the company won?", chunks, top_k=6)
        if ranked is None:
            ...  # fall back to lexical ranking
        else:
            for index, score in ranked:
                print(chunks[index], score)
    """

    def __init__(self, embed_fn: EmbedFn | None = None, *, cache: Any = None) -> None:
        self._embed_fn: EmbedFn = embed_fn or self._default_embed_fn
        self._cache: Any = cache
        logger.info(
            "SemanticReranker ready (embed_fn=%s, cache=%s).",
            getattr(self._embed_fn, "__name__", type(self._embed_fn).__name__),
            type(self._cache).__name__ if self._cache else "None",
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def rank(
        self,
        question: str,
        chunks: Sequence[str],
        *,
        top_k: int | None = None,
    ) -> list[tuple[int, float]] | None:
        """Rank *chunks* by cosine similarity to *question*.

        Args:
            question: The user's natural-language question.
            chunks:   Candidate text chunks to score.
            top_k:    If given, truncate the result to the top-K entries.

        Returns:
            A list of ``(index, score)`` tuples — indices into *chunks* —
            sorted by score descending. Returns ``None`` (never an empty
            list for "unavailable") if embeddings could not be computed at
            all, so callers can distinguish "semantically ranked, no
            matches above zero are still valid" from "semantic ranking
            unavailable, use your fallback." An empty *chunks* sequence
            also returns ``None`` since there is nothing to rank.
        """
        if not question or not question.strip() or not chunks:
            return None

        try:
            question_vec = self._embed(question)
        except Exception as exc:
            logger.warning(
                "SemanticReranker: failed to embed question — %s. Caller should fall back.",
                exc,
            )
            return None

        if not question_vec:
            logger.warning("SemanticReranker: embedding call returned an empty vector for the question.")
            return None

        scored: list[tuple[int, float]] = []
        for idx, chunk in enumerate(chunks):
            if not chunk or not chunk.strip():
                continue
            try:
                chunk_vec = self._embed(chunk)
            except Exception as exc:
                logger.warning("SemanticReranker: failed to embed chunk %d — %s. Skipping.", idx, exc)
                continue
            score = self._cosine_similarity(question_vec, chunk_vec)
            scored.append((idx, score))

        if not scored:
            logger.warning("SemanticReranker: no chunks could be embedded — caller should fall back.")
            return None

        scored.sort(key=lambda pair: pair[1], reverse=True)
        if top_k is not None:
            scored = scored[:top_k]

        logger.info(
            "SemanticReranker: ranked %d/%d chunks (top_k=%s).",
            len(scored),
            len(chunks),
            top_k,
        )
        return scored

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _embed(self, text: str) -> Sequence[float]:
        """Embed *text*, transparently using the cache if one was injected."""
        if self._cache is None:
            return self._embed_fn(text)

        cache_key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        vec = self._embed_fn(text)
        self._cache.set(cache_key, vec)
        return vec

    @staticmethod
    def _default_embed_fn(text: str) -> Sequence[float]:
        from ...api.services.embeddings import embed_query

        return embed_query(text)

    @staticmethod
    def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        similarity = dot / (norm_a * norm_b)
        # Embeddings are near-unit vectors, but clamp defensively against
        # floating-point drift pushing marginally outside [-1, 1].
        return max(0.0, min(1.0, similarity))
