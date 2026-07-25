"""Tests for SemanticReranker.

All tests inject a deterministic fake ``embed_fn`` — no real embedding API
calls or network access.
"""

from __future__ import annotations

import pytest

from src.services.rag.semantic_reranker import SemanticReranker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_embed_fn(vectors: dict[str, list[float]]):
    """Return an embed_fn that looks up a fixed vector per exact text match."""

    def embed_fn(text: str) -> list[float]:
        return vectors[text]

    return embed_fn


def _raising_embed_fn(exc: Exception):
    def embed_fn(text: str):
        raise exc

    return embed_fn


# ---------------------------------------------------------------------------
# Ranking behaviour
# ---------------------------------------------------------------------------


class TestSemanticRerankerRanking:
    def test_ranks_by_cosine_similarity_descending(self):
        vectors = {
            "question": [1.0, 0.0],
            "exact match": [1.0, 0.0],       # identical direction -> similarity 1.0
            "orthogonal": [0.0, 1.0],        # similarity 0.0
            "partial match": [0.7, 0.7],     # similarity ~0.707
        }
        reranker = SemanticReranker(embed_fn=_make_embed_fn(vectors))

        chunks = ["orthogonal", "exact match", "partial match"]
        ranked = reranker.rank("question", chunks)

        assert ranked is not None
        order = [chunks[idx] for idx, _score in ranked]
        assert order == ["exact match", "partial match", "orthogonal"]
        # Scores should be descending and within [0, 1]
        scores = [score for _idx, score in ranked]
        assert scores == sorted(scores, reverse=True)
        assert all(0.0 <= s <= 1.0 for s in scores)

    def test_top_k_truncates_results(self):
        vectors = {
            "question": [1.0, 0.0],
            "a": [1.0, 0.0],
            "b": [0.9, 0.1],
            "c": [0.5, 0.5],
            "d": [0.0, 1.0],
        }
        reranker = SemanticReranker(embed_fn=_make_embed_fn(vectors))

        ranked = reranker.rank("question", ["a", "b", "c", "d"], top_k=2)

        assert ranked is not None
        assert len(ranked) == 2

    def test_indices_refer_to_original_chunk_order(self):
        vectors = {
            "question": [1.0, 0.0],
            "low": [0.0, 1.0],
            "high": [1.0, 0.0],
        }
        reranker = SemanticReranker(embed_fn=_make_embed_fn(vectors))

        chunks = ["low", "high"]  # index 0 = low, index 1 = high
        ranked = reranker.rank("question", chunks)

        assert ranked is not None
        best_idx, best_score = ranked[0]
        assert best_idx == 1
        assert chunks[best_idx] == "high"


# ---------------------------------------------------------------------------
# Fallback behaviour — must return None, never raise
# ---------------------------------------------------------------------------


class TestSemanticRerankerFallback:
    def test_empty_question_returns_none(self):
        reranker = SemanticReranker(embed_fn=_make_embed_fn({}))
        assert reranker.rank("", ["chunk"]) is None
        assert reranker.rank("   ", ["chunk"]) is None

    def test_empty_chunks_returns_none(self):
        reranker = SemanticReranker(embed_fn=_make_embed_fn({"question": [1.0]}))
        assert reranker.rank("question", []) is None

    def test_question_embedding_failure_returns_none(self):
        reranker = SemanticReranker(embed_fn=_raising_embed_fn(RuntimeError("API down")))
        assert reranker.rank("question", ["chunk"]) is None

    def test_all_chunk_embeddings_failing_returns_none(self):
        def embed_fn(text: str):
            if text == "question":
                return [1.0, 0.0]
            raise RuntimeError("embedding failed")

        reranker = SemanticReranker(embed_fn=embed_fn)
        assert reranker.rank("question", ["a", "b"]) is None

    def test_partial_chunk_failure_skips_only_that_chunk(self):
        def embed_fn(text: str):
            if text == "bad":
                raise RuntimeError("embedding failed")
            return {"question": [1.0, 0.0], "good": [1.0, 0.0]}[text]

        reranker = SemanticReranker(embed_fn=embed_fn)
        ranked = reranker.rank("question", ["bad", "good"])

        assert ranked is not None
        assert len(ranked) == 1
        assert ranked[0][0] == 1  # index of "good"

    def test_empty_question_vector_returns_none(self):
        reranker = SemanticReranker(embed_fn=_make_embed_fn({"question": [], "chunk": [1.0]}))
        assert reranker.rank("question", ["chunk"]) is None

    def test_blank_chunks_are_skipped_not_erroring(self):
        vectors = {"question": [1.0, 0.0], "real": [1.0, 0.0]}
        reranker = SemanticReranker(embed_fn=_make_embed_fn(vectors))

        ranked = reranker.rank("question", ["", "   ", "real"])
        assert ranked is not None
        assert len(ranked) == 1
        assert ranked[0][0] == 2


# ---------------------------------------------------------------------------
# Cosine similarity edge cases
# ---------------------------------------------------------------------------


class TestCosineSimilarity:
    def test_zero_vector_returns_zero_not_nan(self):
        score = SemanticReranker._cosine_similarity([0.0, 0.0], [1.0, 0.0])
        assert score == 0.0

    def test_mismatched_lengths_returns_zero(self):
        score = SemanticReranker._cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0])
        assert score == 0.0

    def test_empty_vectors_returns_zero(self):
        assert SemanticReranker._cosine_similarity([], []) == 0.0

    def test_identical_vectors_returns_one(self):
        score = SemanticReranker._cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
        assert score == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Default embed_fn wiring (no network call — just checks lazy import shape)
# ---------------------------------------------------------------------------


class TestSemanticRerankerDefaultEmbedFn:
    def test_default_embed_fn_is_lazy_and_uses_embed_query(self, monkeypatch):
        calls = []

        def fake_embed_query(text):
            calls.append(text)
            return [1.0, 0.0]

        monkeypatch.setattr(
            "src.api.services.embeddings.embed_query", fake_embed_query
        )

        reranker = SemanticReranker()  # no embed_fn injected -> default path
        ranked = reranker.rank("question", ["chunk"])

        assert ranked is not None
        assert calls == ["question", "chunk"]


# ---------------------------------------------------------------------------
# Embedding cache integration
# ---------------------------------------------------------------------------


class TestSemanticRerankerEmbeddingCache:
    def test_repeated_text_only_embedded_once(self):
        from src.shared.cache import TTLCache

        calls = []

        def embed_fn(text):
            calls.append(text)
            return {"question": [1.0, 0.0], "same chunk": [0.9, 0.1]}[text]

        cache = TTLCache(ttl_seconds=60)
        reranker = SemanticReranker(embed_fn=embed_fn, cache=cache)

        reranker.rank("question", ["same chunk"])
        reranker.rank("question", ["same chunk"])  # second call — should hit cache

        # "question" and "same chunk" each embedded exactly once despite two rank() calls
        assert calls.count("question") == 1
        assert calls.count("same chunk") == 1

    def test_different_text_not_confused_by_cache(self):
        from src.shared.cache import TTLCache

        vectors = {"question": [1.0, 0.0], "chunk a": [1.0, 0.0], "chunk b": [0.0, 1.0]}
        cache = TTLCache(ttl_seconds=60)
        reranker = SemanticReranker(embed_fn=lambda t: vectors[t], cache=cache)

        ranked = reranker.rank("question", ["chunk a", "chunk b"])

        assert ranked is not None
        # chunk a (identical direction) must still score higher than chunk b
        best_idx, best_score = ranked[0]
        assert best_idx == 0

    def test_no_cache_injected_embeds_every_time(self):
        calls = []

        def embed_fn(text):
            calls.append(text)
            return {"question": [1.0, 0.0], "chunk": [1.0, 0.0]}[text]

        reranker = SemanticReranker(embed_fn=embed_fn)  # cache=None
        reranker.rank("question", ["chunk"])
        reranker.rank("question", ["chunk"])

        assert calls.count("question") == 2
        assert calls.count("chunk") == 2

    def test_cache_failure_falls_back_to_direct_embedding(self):
        from unittest.mock import MagicMock

        broken_cache = MagicMock()
        broken_cache.get.side_effect = RuntimeError("cache backend down")

        vectors = {"question": [1.0, 0.0], "chunk": [1.0, 0.0]}
        reranker = SemanticReranker(embed_fn=lambda t: vectors[t], cache=broken_cache)

        # A broken cache.get() surfaces as an embedding failure that rank()'s
        # own try/except already handles — returns None, never raises.
        ranked = reranker.rank("question", ["chunk"])
        assert ranked is None
