"""Search service package — live web search via pluggable providers."""

from .models import SearchResult
from .providers.base import SearchProvider
from .providers.tavily import TavilySearchProvider
from .providers.brave import BraveSearchProvider
from .search_service import SearchService

__all__ = [
    "SearchResult",
    "SearchProvider",
    "TavilySearchProvider",
    "BraveSearchProvider",
    "SearchService",
]
