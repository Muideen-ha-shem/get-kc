"""Abstract base class that every search provider must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import SearchResult


class SearchProvider(ABC):
    """Pluggable search-engine abstraction.

    Concrete implementations must override :meth:`search` and
    :attr:`provider_name`.  All other implementation details (HTTP clients,
    rate limits, credential loading, response parsing) are the provider's own
    concern and must not leak into this interface.

    Usage::

        class MyProvider(SearchProvider):
            @property
            def provider_name(self) -> str:
                return "MyEngine"

            def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
                ...
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable identifier for this provider (e.g. ``"Tavily"``)."""

    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Execute a live web search and return structured results.

        Args:
            query:       A natural-language search query.
            max_results: Maximum number of results to return. Providers may
                         return fewer results if the engine does not have
                         enough matches.

        Returns:
            A list of :class:`~services.search.models.SearchResult` objects,
            ordered by relevance (most relevant first).  An empty list is
            returned when no results are found.

        Raises:
            SearchProviderError: If the upstream API returns a non-recoverable
                error (e.g. authentication failure, quota exceeded).
        """


class SearchProviderError(RuntimeError):
    """Raised when a :class:`SearchProvider` encounters a non-recoverable error.

    Attributes:
        provider_name: The name of the provider that raised the error.
        original:      The underlying exception, if any.
    """

    def __init__(self, provider_name: str, message: str, original: Exception | None = None) -> None:
        super().__init__(f"[{provider_name}] {message}")
        self.provider_name = provider_name
        self.original = original
