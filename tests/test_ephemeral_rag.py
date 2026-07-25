"""Tests for EphemeralRAG — lexical baseline behaviour and the optional
semantic reranking integration. No network calls; the semantic reranker is
a mock/stub in every test.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.services.rag.ephemeral_rag import EphemeralRAG, ChunkResult


_PAGE_1 = "<html><body><p>The company won three innovation awards in 2026.</p></body></html>"
_PAGE_2 = "<html><body><p>Our office is located in Lagos, Nigeria.</p></body></html>"


# ---------------------------------------------------------------------------
# Lexical baseline (no semantic_reranker injected — must match prior behaviour)
# ---------------------------------------------------------------------------


class TestEphemeralRagLexical:
    def test_empty_pages_returns_empty(self):
        rag = EphemeralRAG()
        assert rag.retrieve("question", []) == []

    def test_empty_question_returns_empty(self):
        rag = EphemeralRAG()
        assert rag.retrieve("", [_PAGE_1]) == []

    def test_relevant_chunk_is_returned(self):
        rag = EphemeralRAG()
        results = rag.retrieve("innovation awards", [_PAGE_1, _PAGE_2])

        assert len(results) >= 1
        assert "awards" in results[0].text.lower()
        assert results[0].score > 0.0

    def test_no_overlap_returns_empty(self):
        rag = EphemeralRAG()
        results = rag.retrieve("xyzzy quux nonexistent", [_PAGE_1, _PAGE_2])
        assert results == []

    def test_results_sorted_by_score_descending(self):
        rag = EphemeralRAG()
        results = rag.retrieve("company awards office Lagos", [_PAGE_1, _PAGE_2])
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_top_k_caps_results(self):
        many_pages_html = "".join(f"<p>Topic sentence about awards number {i}.</p>" for i in range(30))
        rag = EphemeralRAG(top_k=3)
        results = rag.retrieve("awards", [f"<html><body>{many_pages_html}</body></html>"])
        assert len(results) <= 3

    def test_source_idx_and_chunk_idx_populated(self):
        rag = EphemeralRAG()
        results = rag.retrieve("awards", [_PAGE_1])
        assert results
        assert results[0].source_idx == 0
        assert results[0].chunk_idx >= 0


# ---------------------------------------------------------------------------
# Semantic reranker integration
# ---------------------------------------------------------------------------


class TestEphemeralRagSemanticIntegration:
    def test_uses_semantic_reranker_scores_when_available(self):
        mock_reranker = MagicMock()
        # Reverse the lexical order: pretend the second-ranked lexical chunk
        # is actually the most semantically relevant.
        mock_reranker.rank.return_value = [(0, 0.99)]

        rag = EphemeralRAG(semantic_reranker=mock_reranker, top_k=1)
        results = rag.retrieve("awards", [_PAGE_1])

        assert len(results) == 1
        assert results[0].score == 0.99
        assert results[0].metadata.get("ranking") == "semantic"
        mock_reranker.rank.assert_called_once()

    def test_falls_back_to_lexical_when_reranker_returns_none(self):
        mock_reranker = MagicMock()
        mock_reranker.rank.return_value = None

        rag = EphemeralRAG(semantic_reranker=mock_reranker, top_k=5)
        results = rag.retrieve("awards", [_PAGE_1])

        assert results  # lexical fallback still finds the relevant chunk
        assert all(r.metadata.get("ranking") != "semantic" for r in results)

    def test_falls_back_to_lexical_when_reranker_raises(self):
        mock_reranker = MagicMock()
        mock_reranker.rank.side_effect = RuntimeError("embedding API down")

        rag = EphemeralRAG(semantic_reranker=mock_reranker, top_k=5)
        results = rag.retrieve("awards", [_PAGE_1])

        assert results  # did not propagate the exception
        assert all(r.metadata.get("ranking") != "semantic" for r in results)

    def test_no_semantic_reranker_never_calls_rank(self):
        rag = EphemeralRAG()  # semantic_reranker=None by default
        # Nothing to assert on a call, but this documents/locks in that the
        # default constructor path is purely lexical — no reranker attribute
        # is invoked.
        assert rag._semantic_reranker is None
        results = rag.retrieve("awards", [_PAGE_1])
        assert results

    def test_semantic_reranker_receives_lexical_shortlist_texts(self):
        mock_reranker = MagicMock()
        mock_reranker.rank.return_value = [(0, 0.5)]

        rag = EphemeralRAG(semantic_reranker=mock_reranker, top_k=1)
        rag.retrieve("awards", [_PAGE_1])

        call_args = mock_reranker.rank.call_args
        question_arg = call_args.args[0]
        chunks_arg = call_args.args[1]
        assert question_arg == "awards"
        assert isinstance(chunks_arg, list)
        assert all(isinstance(c, str) for c in chunks_arg)

    def test_rerank_candidate_pool_is_at_least_top_k(self):
        rag = EphemeralRAG(top_k=10, rerank_candidate_pool=3)
        assert rag._rerank_candidate_pool == 10
