"""Domain model for a single web search result."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SearchResult:
    """Represents a single structured result returned by a search provider.

    Attributes:
        title:   The page or article title as reported by the search engine.
        url:     The canonical URL of the result.
        snippet: A short excerpt that is relevant to the query.
        source:  Human-readable label for where the result came from
                 (e.g. the provider name or the website domain).
        score:   Optional relevance score in the range [0, 1] when available.
                 Defaults to ``None`` if the provider does not expose one.
    """

    title: str
    url: str
    snippet: str
    source: str
    score: float | None = field(default=None)

    def to_dict(self) -> dict[str, object]:
        """Serialise the result to a plain dictionary (JSON-safe)."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "score": self.score,
        }
