"""Brave Search provider — second concrete implementation.

Brave Search (https://search.brave.com/search/api) provides an independent
search index free from Big-Tech tracking.

Required environment variable:
    BRAVE_SEARCH_API_KEY  —  Subscription key from
                             https://api.search.brave.com/app/subscriptions

No extra packages are required — the provider uses the ``httpx`` HTTP client
which is already in the project's requirements.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

import httpx

from ....shared.logging import get_logger
from ..models import SearchResult
from .base import SearchProvider, SearchProviderError

logger: logging.Logger = get_logger(__name__)

_PROVIDER_NAME = "Brave"
_BASE_URL = "https://api.search.brave.com/res/v1/web/search"
_DEFAULT_TIMEOUT_SECONDS = 15


class BraveSearchProvider(SearchProvider):
    """Search provider backed by the Brave Search Web Search API.

    Args:
        api_key:    Brave Search subscription key.
        country:    Optional ISO 3166-1 alpha-2 country code used to
                    localise results (e.g. ``"GB"``, ``"US"``).
                    Defaults to ``None`` (global results).
        language:   Preferred result language (e.g. ``"en"``).
                    Defaults to ``"en"``.
        timeout:    HTTP request timeout in seconds.  Defaults to 15 s.

    Raises:
        ValueError:  If ``api_key`` is empty or ``None``.
    """

    def __init__(
        self,
        api_key: str,
        country: str | None = None,
        language: str = "en",
        timeout: float = _DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if not api_key:
            raise ValueError("BraveSearchProvider requires a non-empty api_key.")

        self._api_key = api_key
        self._country = country
        self._language = language
        self._timeout = timeout
        logger.info("BraveSearchProvider initialised (country=%s, lang=%s).", country, language)

    # ------------------------------------------------------------------
    # SearchProvider interface
    # ------------------------------------------------------------------

    @property
    def provider_name(self) -> str:
        return _PROVIDER_NAME

    def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Execute a search via the Brave Search Web API.

        Args:
            query:       Natural-language search query.
            max_results: Maximum number of results (1–20).

        Returns:
            A list of :class:`SearchResult` objects.

        Raises:
            SearchProviderError: On HTTP errors or unexpected response shapes.
        """
        if not query or not query.strip():
            logger.warning("BraveSearchProvider.search called with an empty query.")
            return []

        count = max(1, min(max_results, 20))
        logger.info("BraveSearchProvider: searching for %r (count=%d).", query, count)

        params: dict[str, str | int] = {
            "q": query.strip(),
            "count": count,
            "result_filter": "web",
            "text_decorations": 0,   # plain text, no HTML decorations
        }
        if self._country:
            params["country"] = self._country
        if self._language:
            params["search_lang"] = self._language

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self._api_key,
        }

        try:
            response = httpx.get(
                _BASE_URL,
                params=params,
                headers=headers,
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "BraveSearchProvider: HTTP %d — %s", exc.response.status_code, exc, exc_info=True
            )
            raise SearchProviderError(
                provider_name=_PROVIDER_NAME,
                message=f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
                original=exc,
            ) from exc
        except httpx.RequestError as exc:
            logger.error("BraveSearchProvider: request error — %s", exc, exc_info=True)
            raise SearchProviderError(
                provider_name=_PROVIDER_NAME,
                message=f"Network error: {exc}",
                original=exc,
            ) from exc

        data: dict = response.json()
        web_results: list[dict] = data.get("web", {}).get("results", [])
        logger.info("BraveSearchProvider: received %d raw results.", len(web_results))

        return [self._parse_result(item) for item in web_results]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_result(item: dict) -> SearchResult:
        """Map a single Brave result dict to a :class:`SearchResult`."""
        url: str = item.get("url", "")
        domain: str = urlparse(url).netloc or url

        # Brave returns `description` as the snippet field
        snippet = item.get("description", "").strip() or "(no snippet)"

        return SearchResult(
            title=item.get("title", "").strip() or "(no title)",
            url=url,
            snippet=snippet,
            source=domain,
            score=None,  # Brave does not expose a numeric relevance score
        )
