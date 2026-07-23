"""Tests for SearchManager.

All tests use mocked retrievers — no network calls or database access.
"""

from __future__ import annotations

from unittest.mock import MagicMock

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
        mock_search.search.assert_called_once()

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