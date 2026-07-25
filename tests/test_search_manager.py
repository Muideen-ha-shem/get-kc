"""Tests for SearchManager.

All tests use mocked retrievers — no network calls or database access.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_knowledge_service(matches=None):
    """Return a mock knowledge service with ``retrieve_context``."""
    svc = MagicMock()
    svc.retrieve_context.return_value = (matches or [], [], [])
    return svc


def _make_mock_search_service(results=None):
    """Return a mock search service with ``search``."""
    svc = MagicMock()
    svc.search.return_value = results or []
    return svc


def _make_mock_page_fetcher(pages=None):
    """Return a mock page fetcher with ``fetch``."""
    fetcher = MagicMock()
    if pages:
        fetcher.fetch.side_effect = pages
    else:
        fetcher.fetch.return_value = "<html>mock page</html>"
    return fetcher


def _make_mock_ephemeral_rag(chunks=None):
    """Return a mock ephemeral RAG with ``retrieve``."""
    rag = MagicMock()
    rag.retrieve.return_value = chunks or []
    return rag


# ---------------------------------------------------------------------------
# SearchManager — construction
# ---------------------------------------------------------------------------


class TestSearchManagerConstruction:
    def test_default_construction(self):
        from src.services.manager.search_manager import SearchManager

        manager = SearchManager()
        assert manager._source_router is not None
        assert manager._context_merger is not None
        assert manager._live_search_max_results == 5
        assert manager._live_page_max_fetch == 3

    def test_custom_params(self):
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import SourceRouter
        from src.services.merger.context_merger import ContextMerger

        router = SourceRouter(knowledge_keywords=["custom"])
        merger = ContextMerger(max_evidence=20)

        manager = SearchManager(
            source_router=router,
            context_merger=merger,
            live_search_max_results=10,
            live_page_max_fetch=5,
        )
        assert manager._live_search_max_results == 10
        assert manager._live_page_max_fetch == 5


# ---------------------------------------------------------------------------
# SearchManager — retrieve with pre-computed routing decision
# ---------------------------------------------------------------------------


class TestSearchManagerWithDecision:
    def test_knowledge_only(self):
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision

        mock_kb = _make_mock_knowledge_service(matches=[
            {"chunk_content": "KB result", "similarity": 0.9, "parent_url": "https://kb.example.com"},
        ])
        manager = SearchManager(
            knowledge_service=mock_kb,
            search_service=_make_mock_search_service(),
            page_fetcher=_make_mock_page_fetcher(),
            ephemeral_rag=_make_mock_ephemeral_rag(),
        )

        decision = RoutingDecision(knowledge=True, web=False)
        evidence = manager.retrieve("test question", decision=decision)

        assert len(evidence) >= 1
        mock_kb.retrieve_context.assert_called_once_with("test question")

    def test_web_only(self):
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision
        from src.services.search.models import SearchResult

        mock_search = _make_mock_search_service(results=[
            SearchResult(title="R1", url="https://example.com/1", snippet="Web result 1", source="web", score=0.8),
        ])
        mock_fetcher = _make_mock_page_fetcher(pages=["<html>page 1</html>"])
        mock_rag = _make_mock_ephemeral_rag(chunks=[])

        manager = SearchManager(
            knowledge_service=_make_mock_knowledge_service(),
            search_service=mock_search,
            page_fetcher=mock_fetcher,
            ephemeral_rag=mock_rag,
        )

        decision = RoutingDecision(knowledge=False, web=True)
        evidence = manager.retrieve("latest news", decision=decision)

        assert len(evidence) >= 0  # May be 0 if RAG returns nothing
        mock_search.search.assert_called_once()
        # Page fetcher should have been called for the URL
        mock_fetcher.fetch.assert_called_once_with("https://example.com/1")

    def test_no_active_sources(self):
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision

        manager = SearchManager()
        decision = RoutingDecision(knowledge=False, web=False)
        evidence = manager.retrieve("anything", decision=decision)
        assert evidence == []


# ---------------------------------------------------------------------------
# SearchManager — retrieve with automatic routing
# ---------------------------------------------------------------------------


class TestSearchManagerAutoRoute:
    def test_knowledge_keyword_question(self):
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import SourceRouter

        mock_kb = _make_mock_knowledge_service(matches=[
            {"chunk_content": "About our services", "similarity": 0.85, "parent_url": "https://kb.example.com"},
        ])
        manager = SearchManager(
            source_router=SourceRouter(),
            knowledge_service=mock_kb,
            search_service=_make_mock_search_service(),
            page_fetcher=_make_mock_page_fetcher(),
            ephemeral_rag=_make_mock_ephemeral_rag(),
        )

        evidence = manager.retrieve("What services do you offer?")
        assert len(evidence) >= 1
        mock_kb.retrieve_context.assert_called_once()

    def test_web_keyword_question(self):
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import SourceRouter

        mock_search = _make_mock_search_service(results=[])
        manager = SearchManager(
            source_router=SourceRouter(),
            knowledge_service=_make_mock_knowledge_service(),
            search_service=mock_search,
            page_fetcher=_make_mock_page_fetcher(),
            ephemeral_rag=_make_mock_ephemeral_rag(),
        )

        evidence = manager.retrieve("What are the latest prices?")
        assert isinstance(evidence, list)
        # Search may be called multiple times due to confidence-based fallback
        assert mock_search.search.call_count >= 1

    def test_generic_question_defaults_to_knowledge(self):
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import SourceRouter

        mock_kb = _make_mock_knowledge_service(matches=[])
        manager = SearchManager(
            source_router=SourceRouter(),
            knowledge_service=mock_kb,
            search_service=_make_mock_search_service(),
            page_fetcher=_make_mock_page_fetcher(),
            ephemeral_rag=_make_mock_ephemeral_rag(),
        )

        # "hello" has no keywords, should default to knowledge=True
        evidence = manager.retrieve("Hello!")
        assert isinstance(evidence, list)
        mock_kb.retrieve_context.assert_called_once()


# ---------------------------------------------------------------------------
# SearchManager — error handling
# ---------------------------------------------------------------------------


class TestSearchManagerErrorHandling:
    def test_knowledge_service_raises_error(self):
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision

        mock_kb = MagicMock()
        mock_kb.retrieve_context.side_effect = RuntimeError("DB down")

        manager = SearchManager(
            knowledge_service=mock_kb,
            search_service=_make_mock_search_service(),
            page_fetcher=_make_mock_page_fetcher(),
            ephemeral_rag=_make_mock_ephemeral_rag(),
        )

        decision = RoutingDecision(knowledge=True, web=False)
        evidence = manager.retrieve("test", decision=decision)
        # Should gracefully handle the error and return empty
        assert evidence == []

    def test_search_service_raises_error(self):
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision

        mock_search = MagicMock()
        mock_search.search.side_effect = RuntimeError("API down")

        manager = SearchManager(
            knowledge_service=_make_mock_knowledge_service(),
            search_service=mock_search,
            page_fetcher=_make_mock_page_fetcher(),
            ephemeral_rag=_make_mock_ephemeral_rag(),
        )

        decision = RoutingDecision(knowledge=False, web=True)
        evidence = manager.retrieve("test", decision=decision)
        assert evidence == []

    def test_page_fetcher_raises_error(self):
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision
        from src.services.search.models import SearchResult

        mock_fetcher = MagicMock()
        mock_fetcher.fetch.side_effect = RuntimeError("Network error")

        manager = SearchManager(
            knowledge_service=_make_mock_knowledge_service(),
            search_service=_make_mock_search_service(results=[
                SearchResult(title="R", url="https://example.com", snippet="Snippet", source="web", score=0.8),
            ]),
            page_fetcher=mock_fetcher,
            ephemeral_rag=_make_mock_ephemeral_rag(),
        )

        decision = RoutingDecision(knowledge=False, web=True)
        # Should not crash even though page fetcher fails
        evidence = manager.retrieve("test", decision=decision)
        assert isinstance(evidence, list)


# ---------------------------------------------------------------------------
# SearchManager — evidence merging
# ---------------------------------------------------------------------------


class TestSearchManagerMerging:
    def test_evidence_contains_items_from_all_sources(self):
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision
        from src.services.search.models import SearchResult
        from src.services.merger.context_merger import EvidenceItem

        mock_kb = _make_mock_knowledge_service(matches=[
            {"chunk_content": "KB match", "similarity": 0.7, "parent_url": "https://kb.example.com"},
        ])
        mock_search = _make_mock_search_service(results=[
            SearchResult(title="Web", url="https://web.example.com", snippet="Web snippet", source="web", score=0.9),
        ])
        mock_fetcher = _make_mock_page_fetcher(pages=["<html>live page</html>"])
        mock_rag = _make_mock_ephemeral_rag(chunks=[
            EvidenceItem(content="RAG chunk", score=0.85),
        ])

        manager = SearchManager(
            knowledge_service=mock_kb,
            search_service=mock_search,
            page_fetcher=mock_fetcher,
            ephemeral_rag=mock_rag,
        )

        decision = RoutingDecision(knowledge=True, web=True)
        evidence = manager.retrieve("test", decision=decision)

        # Should have evidence from all sources merged
        assert len(evidence) >= 2  # KB + web (RAG returns EvidenceItems that merger passes through)

    def test_evidence_unique_urls(self):
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision
        from src.services.search.models import SearchResult

        # Same URL appears in both KB and web results — dedup should keep only the best
        mock_kb = _make_mock_knowledge_service(matches=[
            {"chunk_content": "KB same URL", "similarity": 0.6, "parent_url": "https://example.com/same"},
        ])
        mock_search = _make_mock_search_service(results=[
            SearchResult(title="Web", url="https://example.com/same", snippet="Web same URL", source="web", score=0.9),
        ])

        manager = SearchManager(
            knowledge_service=mock_kb,
            search_service=mock_search,
            page_fetcher=_make_mock_page_fetcher(),
            ephemeral_rag=_make_mock_ephemeral_rag(),
        )

        decision = RoutingDecision(knowledge=True, web=True)
        evidence = manager.retrieve("test", decision=decision)

        # Only one item should survive URL dedup since both point to the same URL
        urls = [e.url for e in evidence if e.url]
        unique_urls = set(urls)
        assert len(urls) == len(unique_urls), f"Duplicate URLs found: {urls}"


# ---------------------------------------------------------------------------
# SearchManager — source_ranker integration (Intelligent Source Ranking)
# ---------------------------------------------------------------------------


class TestSearchManagerSourceRanker:
    def test_source_ranker_not_injected_leaves_merged_evidence_unchanged(self):
        """Default behaviour (no source_ranker) must be identical to before
        this feature existed — this is the backward-compatibility guarantee."""
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision

        mock_kb = _make_mock_knowledge_service(matches=[
            {"chunk_content": "KB result", "similarity": 0.9, "parent_url": "https://kb.example.com"},
        ])
        manager = SearchManager(
            knowledge_service=mock_kb,
            search_service=_make_mock_search_service(),
            page_fetcher=_make_mock_page_fetcher(),
            ephemeral_rag=_make_mock_ephemeral_rag(),
        )
        assert manager._source_ranker is None

        decision = RoutingDecision(knowledge=True, web=False)
        evidence = manager.retrieve("test question", decision=decision)
        assert len(evidence) >= 1

    def test_source_ranker_is_applied_to_merged_evidence(self):
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision
        from src.services.merger.context_merger import EvidenceItem

        mock_kb = _make_mock_knowledge_service(matches=[
            {"chunk_content": "KB result", "similarity": 0.9, "parent_url": "https://kb.example.com"},
        ])
        sentinel_result = [EvidenceItem(content="ranked output", score=1.0)]
        mock_ranker = MagicMock()
        mock_ranker.rank.return_value = sentinel_result

        manager = SearchManager(
            knowledge_service=mock_kb,
            search_service=_make_mock_search_service(),
            page_fetcher=_make_mock_page_fetcher(),
            ephemeral_rag=_make_mock_ephemeral_rag(),
            source_ranker=mock_ranker,
        )

        decision = RoutingDecision(knowledge=True, web=False)
        evidence = manager.retrieve("test question", decision=decision)

        assert evidence == sentinel_result
        mock_ranker.rank.assert_called_once()
        call_kwargs = mock_ranker.rank.call_args.kwargs
        assert call_kwargs.get("question") == "test question"

    def test_source_ranker_not_called_when_no_evidence(self):
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision

        mock_ranker = MagicMock()
        manager = SearchManager(
            knowledge_service=_make_mock_knowledge_service(matches=[]),
            search_service=_make_mock_search_service(results=[]),
            page_fetcher=_make_mock_page_fetcher(),
            ephemeral_rag=_make_mock_ephemeral_rag(),
            source_ranker=mock_ranker,
        )

        decision = RoutingDecision(knowledge=True, web=False)
        manager.retrieve("test question", decision=decision)

        mock_ranker.rank.assert_not_called()

    def test_source_ranker_failure_falls_back_to_merged_evidence(self):
        """A broken ranking stage must never break the whole chat response."""
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision

        mock_kb = _make_mock_knowledge_service(matches=[
            {"chunk_content": "KB result", "similarity": 0.9, "parent_url": "https://kb.example.com"},
        ])
        mock_ranker = MagicMock()
        mock_ranker.rank.side_effect = RuntimeError("ranking exploded")

        manager = SearchManager(
            knowledge_service=mock_kb,
            search_service=_make_mock_search_service(),
            page_fetcher=_make_mock_page_fetcher(),
            ephemeral_rag=_make_mock_ephemeral_rag(),
            source_ranker=mock_ranker,
        )

        decision = RoutingDecision(knowledge=True, web=False)
        evidence = manager.retrieve("test question", decision=decision)

        # Falls back to the (unranked) merged evidence rather than raising
        assert len(evidence) >= 1


# ---------------------------------------------------------------------------
# SearchManager — semantic_reranker integration (Semantic Reranking)
# ---------------------------------------------------------------------------


class TestSearchManagerSemanticReranker:
    def test_semantic_reranker_passed_to_default_ephemeral_rag(self):
        from src.services.manager.search_manager import SearchManager

        mock_reranker = MagicMock()
        manager = SearchManager(semantic_reranker=mock_reranker)

        with patch("src.services.rag.ephemeral_rag.EphemeralRAG") as mock_rag_cls:
            manager._get_ephemeral_rag()

        mock_rag_cls.assert_called_once_with(semantic_reranker=mock_reranker)

    def test_semantic_reranker_ignored_when_ephemeral_rag_injected_directly(self):
        from src.services.manager.search_manager import SearchManager

        injected_rag = _make_mock_ephemeral_rag()
        mock_reranker = MagicMock()

        manager = SearchManager(ephemeral_rag=injected_rag, semantic_reranker=mock_reranker)

        assert manager._get_ephemeral_rag() is injected_rag
        mock_reranker.rank.assert_not_called()


# ---------------------------------------------------------------------------
# SearchManager — query_rewriter integration (Phase 13)
# ---------------------------------------------------------------------------


class TestSearchManagerQueryRewriter:
    """Note: these use a non-empty search result so SearchManager's existing
    "no evidence from any source" enterprise-fallback step (which retries
    web search once more) never triggers — keeping each search call
    single and the assertions unambiguous."""

    def test_no_rewriter_sends_original_question(self):
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision
        from src.services.search.models import SearchResult

        mock_search = _make_mock_search_service(results=[
            SearchResult(title="R", url="https://example.com", snippet="", source="web", score=0.9),
        ])
        manager = SearchManager(
            search_service=mock_search,
            page_fetcher=_make_mock_page_fetcher(),
            ephemeral_rag=_make_mock_ephemeral_rag(),
        )

        manager.retrieve("original question", decision=RoutingDecision(knowledge=False, web=True))
        mock_search.search.assert_called_once_with("original question", max_results=5)

    def test_rewriter_output_sent_to_search(self):
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision
        from src.services.search.models import SearchResult

        mock_rewriter = MagicMock()
        mock_rewriter.rewrite.return_value = "rewritten query site:example.com"
        mock_search = _make_mock_search_service(results=[
            SearchResult(title="R", url="https://example.com", snippet="", source="web", score=0.9),
        ])

        manager = SearchManager(
            search_service=mock_search,
            page_fetcher=_make_mock_page_fetcher(),
            ephemeral_rag=_make_mock_ephemeral_rag(),
            query_rewriter=mock_rewriter,
        )

        manager.retrieve("original question", decision=RoutingDecision(knowledge=False, web=True))

        mock_rewriter.rewrite.assert_called_once_with("original question")
        mock_search.search.assert_called_once_with("rewritten query site:example.com", max_results=5)

    def test_rewriter_failure_falls_back_to_original_question(self):
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision
        from src.services.search.models import SearchResult

        mock_rewriter = MagicMock()
        mock_rewriter.rewrite.side_effect = RuntimeError("rewrite exploded")
        mock_search = _make_mock_search_service(results=[
            SearchResult(title="R", url="https://example.com", snippet="", source="web", score=0.9),
        ])

        manager = SearchManager(
            search_service=mock_search,
            page_fetcher=_make_mock_page_fetcher(),
            ephemeral_rag=_make_mock_ephemeral_rag(),
            query_rewriter=mock_rewriter,
        )

        manager.retrieve("original question", decision=RoutingDecision(knowledge=False, web=True))
        mock_search.search.assert_called_once_with("original question", max_results=5)


# ---------------------------------------------------------------------------
# SearchManager — domain_filter integration (Phase 13)
# ---------------------------------------------------------------------------


class TestSearchManagerDomainFilter:
    def test_domain_filter_applied_to_urls_before_fetch(self):
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision
        from src.services.search.models import SearchResult

        mock_search = _make_mock_search_service(results=[
            SearchResult(title="Bad", url="https://blocked.example.com", snippet="", source="web", score=0.9),
            SearchResult(title="Good", url="https://allowed.example.com", snippet="", source="web", score=0.8),
        ])
        mock_domain_filter = MagicMock()
        mock_domain_filter.filter.return_value = ["https://allowed.example.com"]
        mock_fetcher = _make_mock_page_fetcher()

        manager = SearchManager(
            search_service=mock_search,
            page_fetcher=mock_fetcher,
            ephemeral_rag=_make_mock_ephemeral_rag(),
            domain_filter=mock_domain_filter,
        )

        manager.retrieve("test", decision=RoutingDecision(knowledge=False, web=True))

        mock_domain_filter.filter.assert_called_once_with(
            ["https://blocked.example.com", "https://allowed.example.com"]
        )
        mock_fetcher.fetch.assert_called_once_with("https://allowed.example.com")

    def test_domain_filter_failure_falls_back_to_unfiltered_urls(self):
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision
        from src.services.search.models import SearchResult

        mock_search = _make_mock_search_service(results=[
            SearchResult(title="R", url="https://example.com", snippet="", source="web", score=0.9),
        ])
        mock_domain_filter = MagicMock()
        mock_domain_filter.filter.side_effect = RuntimeError("filter exploded")
        mock_fetcher = _make_mock_page_fetcher()

        manager = SearchManager(
            search_service=mock_search,
            page_fetcher=mock_fetcher,
            ephemeral_rag=_make_mock_ephemeral_rag(),
            domain_filter=mock_domain_filter,
        )

        manager.retrieve("test", decision=RoutingDecision(knowledge=False, web=True))
        mock_fetcher.fetch.assert_called_once_with("https://example.com")

    def test_domain_filter_dropping_all_urls_skips_fetch(self):
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision
        from src.services.search.models import SearchResult

        mock_search = _make_mock_search_service(results=[
            SearchResult(title="R", url="https://example.com", snippet="", source="web", score=0.9),
        ])
        mock_domain_filter = MagicMock()
        mock_domain_filter.filter.return_value = []
        mock_fetcher = _make_mock_page_fetcher()

        manager = SearchManager(
            search_service=mock_search,
            page_fetcher=mock_fetcher,
            ephemeral_rag=_make_mock_ephemeral_rag(),
            domain_filter=mock_domain_filter,
        )

        manager.retrieve("test", decision=RoutingDecision(knowledge=False, web=True))
        mock_fetcher.fetch.assert_not_called()


# ---------------------------------------------------------------------------
# SearchManager — response_cache integration (Phase 14)
# ---------------------------------------------------------------------------


class TestSearchManagerResponseCache:
    def test_search_results_cached_across_calls(self):
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision
        from src.shared.cache import TTLCache

        mock_search = _make_mock_search_service(results=[])
        cache = TTLCache(ttl_seconds=60)

        manager = SearchManager(
            search_service=mock_search,
            page_fetcher=_make_mock_page_fetcher(),
            ephemeral_rag=_make_mock_ephemeral_rag(),
            response_cache=cache,
        )

        decision = RoutingDecision(knowledge=False, web=True)
        manager.retrieve("same question", decision=decision)
        manager.retrieve("same question", decision=decision)

        mock_search.search.assert_called_once()

    def test_fetched_pages_cached_across_calls(self):
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision
        from src.services.search.models import SearchResult
        from src.shared.cache import TTLCache

        mock_search = _make_mock_search_service(results=[
            SearchResult(title="R", url="https://example.com/page", snippet="", source="web", score=0.9),
        ])
        mock_fetcher = _make_mock_page_fetcher()
        cache = TTLCache(ttl_seconds=60)

        manager = SearchManager(
            search_service=mock_search,
            page_fetcher=mock_fetcher,
            ephemeral_rag=_make_mock_ephemeral_rag(),
            response_cache=cache,
        )

        decision = RoutingDecision(knowledge=False, web=True)
        manager.retrieve("q1", decision=decision)
        manager.retrieve("q2", decision=decision)  # different question, same URL surfaced

        # The page was only actually fetched once — the second retrieve()
        # hit the cache for the URL even though the question differed.
        mock_fetcher.fetch.assert_called_once_with("https://example.com/page")

    def test_no_cache_injected_fetches_every_time(self):
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision
        from src.services.search.models import SearchResult

        mock_search = _make_mock_search_service(results=[
            SearchResult(title="R", url="https://example.com", snippet="", source="web", score=0.9),
        ])
        manager = SearchManager(
            search_service=mock_search,
            page_fetcher=_make_mock_page_fetcher(),
            ephemeral_rag=_make_mock_ephemeral_rag(),
        )  # response_cache=None

        decision = RoutingDecision(knowledge=False, web=True)
        manager.retrieve("same question", decision=decision)
        manager.retrieve("same question", decision=decision)

        assert mock_search.search.call_count == 2


# ---------------------------------------------------------------------------
# SearchManager — concurrent page fetching (Phase 14)
# ---------------------------------------------------------------------------


class TestSearchManagerConcurrentFetching:
    def test_multiple_urls_all_fetched(self):
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision
        from src.services.search.models import SearchResult

        urls = [f"https://example.com/{i}" for i in range(4)]
        mock_search = _make_mock_search_service(results=[
            SearchResult(title=f"R{i}", url=u, snippet="", source="web", score=0.9) for i, u in enumerate(urls)
        ])

        fetch_calls = []

        def fetch(url):
            fetch_calls.append(url)
            return f"<html>{url}</html>"

        mock_fetcher = MagicMock()
        mock_fetcher.fetch.side_effect = fetch

        manager = SearchManager(
            search_service=mock_search,
            page_fetcher=mock_fetcher,
            ephemeral_rag=_make_mock_ephemeral_rag(),
            live_page_max_fetch=4,
        )

        manager.retrieve("test", decision=RoutingDecision(knowledge=False, web=True))

        assert sorted(fetch_calls) == sorted(urls)

    def test_page_order_preserved_despite_concurrency(self):
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision
        from src.services.search.models import SearchResult

        urls = [f"https://example.com/{i}" for i in range(3)]
        mock_search = _make_mock_search_service(results=[
            SearchResult(title=f"R{i}", url=u, snippet="", source="web", score=0.9) for i, u in enumerate(urls)
        ])

        # Slowest first, fastest last — if order were determined by
        # completion time rather than preserved explicitly, this would fail.
        import time as time_module

        def fetch(url):
            if url.endswith("/0"):
                time_module.sleep(0.05)
            return f"<html>content for {url}</html>"

        mock_fetcher = MagicMock()
        mock_fetcher.fetch.side_effect = fetch

        captured_pages = {}
        mock_rag = MagicMock()

        def capture_retrieve(question, pages):
            captured_pages["pages"] = pages
            return []

        mock_rag.retrieve.side_effect = capture_retrieve

        manager = SearchManager(
            search_service=mock_search,
            page_fetcher=mock_fetcher,
            ephemeral_rag=mock_rag,
            live_page_max_fetch=3,
        )

        manager.retrieve("test", decision=RoutingDecision(knowledge=False, web=True))

        assert captured_pages["pages"] == [
            "<html>content for https://example.com/0</html>",
            "<html>content for https://example.com/1</html>",
            "<html>content for https://example.com/2</html>",
        ]

    def test_concurrency_is_bounded_by_fetch_concurrency(self):
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision
        from src.services.search.models import SearchResult
        import threading
        import time as time_module

        urls = [f"https://example.com/{i}" for i in range(6)]
        mock_search = _make_mock_search_service(results=[
            SearchResult(title=f"R{i}", url=u, snippet="", source="web", score=0.9) for i, u in enumerate(urls)
        ])

        current_concurrent = 0
        max_concurrent_seen = 0
        lock = threading.Lock()

        def fetch(url):
            nonlocal current_concurrent, max_concurrent_seen
            with lock:
                current_concurrent += 1
                max_concurrent_seen = max(max_concurrent_seen, current_concurrent)
            time_module.sleep(0.03)
            with lock:
                current_concurrent -= 1
            return f"<html>{url}</html>"

        mock_fetcher = MagicMock()
        mock_fetcher.fetch.side_effect = fetch

        manager = SearchManager(
            search_service=mock_search,
            page_fetcher=mock_fetcher,
            ephemeral_rag=_make_mock_ephemeral_rag(),
            live_page_max_fetch=6,
            fetch_concurrency=2,
        )

        manager.retrieve("test", decision=RoutingDecision(knowledge=False, web=True))

        assert max_concurrent_seen <= 2

    def test_single_url_uses_sequential_path(self):
        """A single URL should use the plain synchronous call, matching prior behaviour exactly."""
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision
        from src.services.search.models import SearchResult

        mock_search = _make_mock_search_service(results=[
            SearchResult(title="R", url="https://example.com/only", snippet="", source="web", score=0.9),
        ])
        mock_fetcher = _make_mock_page_fetcher()

        manager = SearchManager(
            search_service=mock_search,
            page_fetcher=mock_fetcher,
            ephemeral_rag=_make_mock_ephemeral_rag(),
        )

        manager.retrieve("test", decision=RoutingDecision(knowledge=False, web=True))
        mock_fetcher.fetch.assert_called_once_with("https://example.com/only")

    def test_nested_event_loop_falls_back_to_sequential(self):
        """Calling retrieve() from a thread that already has a running event
        loop must not attempt to nest asyncio.run() — it should detect this
        upfront and fetch sequentially instead."""
        import asyncio

        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision
        from src.services.search.models import SearchResult

        urls = [f"https://example.com/{i}" for i in range(3)]
        mock_search = _make_mock_search_service(results=[
            SearchResult(title=f"R{i}", url=u, snippet="", source="web", score=0.9) for i, u in enumerate(urls)
        ])
        mock_fetcher = _make_mock_page_fetcher()
        mock_fetcher.fetch.side_effect = lambda url: f"<html>{url}</html>"

        manager = SearchManager(
            search_service=mock_search,
            page_fetcher=mock_fetcher,
            ephemeral_rag=_make_mock_ephemeral_rag(),
            live_page_max_fetch=3,
        )

        async def call_retrieve_from_within_a_running_loop():
            # manager.retrieve() is synchronous, but this coroutine is being
            # driven by asyncio.run() below, so the current thread has a
            # running loop for the whole (non-yielding) duration of this call.
            return manager.retrieve("test", decision=RoutingDecision(knowledge=False, web=True))

        # Must not raise (asyncio.run() cannot nest) — falls back to sequential.
        asyncio.run(call_retrieve_from_within_a_running_loop())

        assert mock_fetcher.fetch.call_count == 3

    def test_event_loop_already_running_detection(self):
        from src.services.manager.search_manager import SearchManager

        assert SearchManager._event_loop_already_running() is False

        import asyncio

        async def check():
            return SearchManager._event_loop_already_running()

        assert asyncio.run(check()) is True

    def test_asyncio_run_runtime_error_falls_back_without_leaking_coroutine(self):
        """Defensive branch: if asyncio.run() itself raises RuntimeError for
        some other reason (not the common nested-loop case, which is caught
        upfront), fall back to sequential rather than propagating."""
        from src.services.manager.search_manager import SearchManager
        from src.services.routing.source_router import RoutingDecision
        from src.services.search.models import SearchResult

        urls = [f"https://example.com/{i}" for i in range(3)]
        mock_search = _make_mock_search_service(results=[
            SearchResult(title=f"R{i}", url=u, snippet="", source="web", score=0.9) for i, u in enumerate(urls)
        ])
        mock_fetcher = _make_mock_page_fetcher()
        mock_fetcher.fetch.side_effect = lambda url: f"<html>{url}</html>"

        manager = SearchManager(
            search_service=mock_search,
            page_fetcher=mock_fetcher,
            ephemeral_rag=_make_mock_ephemeral_rag(),
            live_page_max_fetch=3,
        )

        def broken_asyncio_run(coro):
            coro.close()  # avoid an unawaited-coroutine warning from the test double itself
            raise RuntimeError("simulated asyncio.run failure")

        with patch("src.services.manager.search_manager.asyncio.run", side_effect=broken_asyncio_run):
            manager.retrieve("test", decision=RoutingDecision(knowledge=False, web=True))

        assert mock_fetcher.fetch.call_count == 3