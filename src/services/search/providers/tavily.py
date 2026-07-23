"""Tavily Search provider — first concrete implementation.

Tavily (https://tavily.com) is an AI-native search API that returns
structured, relevance-ranked results and is purpose-built for LLM workflows.

Required environment variable:
    TAVILY_API_KEY  —  API key from https://app.tavily.com

Install the optional dependency::

    pip install tavily-python>=0.5.0

If the package is not installed the provider will raise ``ImportError``
with a helpful message at instantiation time.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from ....shared.logging import get_logger
from ..models import SearchResult
from .base import SearchProvider, SearchProviderError

logger: logging.Logger = get_logger(__name__)

_PROVIDER_NAME = "Tavily"


class TavilySearchProvider(SearchProvider):
    """Search provider backed by the Tavily REST API.

    Args:
        api_key:        Tavily API key.  Must not be empty or ``None``.
        search_depth:   ``"basic"`` (faster, lower quota) or ``"advanced"``
                        (deeper crawl, higher quality).  Defaults to
                        ``"basic"``.

    Raises:
        ImportError:   If ``tavily-python`` is not installed.
        ValueError:    If ``api_key`` is empty or ``None``.
    """

    def __init__(self, api_key: str, search_depth: str = "basic") -> None:
        try:
            from tavily import TavilyClient  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "The 'tavily-python' package is required for TavilySearchProvider. "
                "Install it with: pip install 'tavily-python>=0.5.0'"
            ) from exc

        if not api_key:
            raise ValueError("TavilySearchProvider requires a non-empty api_key.")

        self._client = TavilyClient(api_key=api_key)
        self._search_depth = search_depth
        logger.info("TavilySearchProvider initialised (depth=%s).", search_depth)

    # ------------------------------------------------------------------
    # SearchProvider interface
    # ------------------------------------------------------------------

    @property
    def provider_name(self) -> str:
        return _PROVIDER_NAME

    def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Execute a search via the Tavily API.

        Args:
            query:       Natural-language search query.
            max_results: Maximum number of results (capped at 20 by Tavily).

        Returns:
            A list of :class:`SearchResult` ordered by Tavily's relevance score.

        Raises:
            SearchProviderError: On any API or network failure.
        """
        if not query or not query.strip():
            logger.warning("TavilySearchProvider.search called with an empty query.")
            return []

        logger.info("TavilySearchProvider: searching for %r (max_results=%d).", query, max_results)

        try:
            response: dict = self._client.search(
                query=query.strip(),
                search_depth=self._search_depth,
                max_results=min(max_results, 20),  # Tavily hard-cap
                include_answer=False,              # raw results only
                include_raw_content=False,         # no full page downloads
            )
        except Exception as exc:
            logger.error("TavilySearchProvider: API call failed — %s", exc, exc_info=True)
            raise SearchProviderError(
                provider_name=_PROVIDER_NAME,
                message=f"API call failed: {exc}",
                original=exc,
            ) from exc

        raw_results: list[dict] = response.get("results", [])
        logger.info("TavilySearchProvider: received %d raw results.", len(raw_results))

        return [self._parse_result(item) for item in raw_results]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_result(item: dict) -> SearchResult:
        """Map a single Tavily result dict to a :class:`SearchResult`."""
        url: str = item.get("url", "")
        domain: str = urlparse(url).netloc or url

        return SearchResult(
            title=item.get("title", "").strip() or "(no title)",
            url=url,
            snippet=item.get("content", "").strip() or "(no snippet)",
            source=domain,
            score=item.get("score"),
        )
