"""SearchService — the business-layer entry point for live web search.

This service owns the provider lifecycle and provides a single, stable
interface to the rest of the application regardless of which underlying
search engine is in use.  The concrete provider is injected at construction
time, making it trivial to swap implementations or inject mocks in tests.

Typical usage::

    from src.config.settings import Settings
    from src.services.search import SearchService, TavilySearchProvider

    settings = Settings.from_environment()
    provider = TavilySearchProvider(api_key=settings.tavily_api_key)
    service  = SearchService(provider=provider)

    results = service.search("What is LangGraph?")
    for r in results:
        print(r.title, r.url)
"""

from __future__ import annotations

import logging
from typing import Sequence

from ...shared.logging import get_logger
from .models import SearchResult
from .providers.base import SearchProvider, SearchProviderError

logger: logging.Logger = get_logger(__name__)


class SearchService:
    """Orchestrates live web searches through a pluggable :class:`SearchProvider`.

    Args:
        provider:    A concrete :class:`SearchProvider` implementation.
        max_results: Default maximum number of results to request from the
                     provider.  Individual callers may override this per call.

    Example::

        service = SearchService(provider=TavilySearchProvider(api_key="..."))
        results = service.search("how does RAG work?", max_results=5)
    """

    def __init__(self, provider: SearchProvider, max_results: int = 10) -> None:
        if provider is None:
            raise ValueError("SearchService requires a non-None provider.")
        self._provider = provider
        self._max_results = max_results
        logger.info(
            "SearchService ready (provider=%s, default_max=%d).",
            provider.provider_name,
            max_results,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def provider_name(self) -> str:
        """Name of the currently active search provider."""
        return self._provider.provider_name

    def search(self, query: str, max_results: int | None = None) -> list[SearchResult]:
        """Perform a live web search and return structured results.

        Args:
            query:       Natural-language search query.  Leading/trailing
                         whitespace is stripped before forwarding.
            max_results: Maximum number of results.  When omitted, the
                         service-level default is used.

        Returns:
            A (possibly empty) list of :class:`SearchResult` objects ordered
            by provider-defined relevance.

        Raises:
            ValueError:          If ``query`` is blank after stripping.
            SearchProviderError: If the underlying provider signals a
                                 non-recoverable API failure.
        """
        clean_query = (query or "").strip()
        if not clean_query:
            raise ValueError("search() requires a non-empty query string.")

        limit = max_results if max_results is not None else self._max_results

        logger.info(
            "SearchService.search: provider=%s, query=%r, max_results=%d.",
            self._provider.provider_name,
            clean_query,
            limit,
        )

        try:
            results: list[SearchResult] = self._provider.search(clean_query, max_results=limit)
        except SearchProviderError:
            # Re-raise directly — callers should handle provider errors explicitly.
            raise
        except Exception as exc:
            # Unexpected errors are wrapped so callers see a consistent type.
            logger.error(
                "SearchService.search: unexpected error from provider %s — %s",
                self._provider.provider_name,
                exc,
                exc_info=True,
            )
            raise SearchProviderError(
                provider_name=self._provider.provider_name,
                message=f"Unexpected error: {exc}",
                original=exc,
            ) from exc

        logger.info(
            "SearchService.search: returned %d results for query=%r.",
            len(results),
            clean_query,
        )
        return results

    def search_to_dicts(self, query: str, max_results: int | None = None) -> list[dict[str, object]]:
        """Convenience wrapper that serialises results to plain dictionaries.

        Useful when the caller needs JSON-serialisable output (e.g. MCP tools,
        API response schemas).

        Args:
            query:       See :meth:`search`.
            max_results: See :meth:`search`.

        Returns:
            A list of dicts, each with keys ``title``, ``url``, ``snippet``,
            ``source``, and ``score``.
        """
        return [r.to_dict() for r in self.search(query, max_results=max_results)]
