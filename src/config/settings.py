import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    """Simple centralized settings container for runtime configuration."""

    supabase_url: str | None = None
    supabase_key: str | None = None
    groq_api_key: str | None = None
    google_api_key: str | None = None
    # Live web search providers (at least one must be set to use SearchService)
    tavily_api_key: str | None = None
    brave_search_api_key: str | None = None

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            supabase_url=os.getenv("SUPABASE_URL"),
            supabase_key=os.getenv("SUPABASE_KEY"),
            groq_api_key=os.getenv("GROQ_API_KEY"),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            brave_search_api_key=os.getenv("BRAVE_SEARCH_API_KEY"),
        )

    def build_search_service(self):  # noqa: ANN201 — avoids a circular import
        """Construct a :class:`~services.search.SearchService` from available credentials.

        Provider priority:
            1. Tavily  (if ``TAVILY_API_KEY`` is present)
            2. Brave   (if ``BRAVE_SEARCH_API_KEY`` is present)

        Returns:
            A configured :class:`~services.search.SearchService` instance.

        Raises:
            RuntimeError: If no search-provider credentials are configured.
        """
        from ..services.search import SearchService, TavilySearchProvider, BraveSearchProvider

        if self.tavily_api_key:
            provider = TavilySearchProvider(api_key=self.tavily_api_key)
        elif self.brave_search_api_key:
            provider = BraveSearchProvider(api_key=self.brave_search_api_key)
        else:
            raise RuntimeError(
                "No search provider credentials found. "
                "Set TAVILY_API_KEY or BRAVE_SEARCH_API_KEY in your environment."
            )

        return SearchService(provider=provider)

