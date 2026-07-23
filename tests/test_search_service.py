"""Tests for the Live Search Service layer.

All tests use mocks/stubs — no real HTTP calls are made.  The test suite
covers:
  - SearchResult dataclass behaviour
  - SearchProvider ABC enforcement
  - TavilySearchProvider: happy path, empty response, API error
  - BraveSearchProvider: happy path, HTTP error, network error
  - SearchService: validation, delegation, error propagation
  - Settings.build_search_service: provider selection priority
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

# ---------------------------------------------------------------------------
# SearchResult
# ---------------------------------------------------------------------------


class TestSearchResult:
    def test_required_fields_are_stored(self):
        from src.services.search.models import SearchResult

        r = SearchResult(title="T", url="https://example.com", snippet="S", source="example.com")
        assert r.title == "T"
        assert r.url == "https://example.com"
        assert r.snippet == "S"
        assert r.source == "example.com"
        assert r.score is None

    def test_optional_score(self):
        from src.services.search.models import SearchResult

        r = SearchResult(title="T", url="u", snippet="s", source="src", score=0.87)
        assert r.score == pytest.approx(0.87)

    def test_to_dict_keys(self):
        from src.services.search.models import SearchResult

        r = SearchResult(title="T", url="u", snippet="s", source="src", score=0.5)
        d = r.to_dict()
        assert set(d.keys()) == {"title", "url", "snippet", "source", "score"}

    def test_immutability(self):
        from src.services.search.models import SearchResult

        r = SearchResult(title="T", url="u", snippet="s", source="src")
        with pytest.raises((AttributeError, TypeError)):
            r.title = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SearchProvider ABC
# ---------------------------------------------------------------------------


class TestSearchProviderABC:
    def test_cannot_instantiate_abstract_base(self):
        from src.services.search.providers.base import SearchProvider

        with pytest.raises(TypeError):
            SearchProvider()  # type: ignore[abstract]

    def test_concrete_must_implement_all_abstracts(self):
        from src.services.search.providers.base import SearchProvider

        class Incomplete(SearchProvider):
            pass  # Missing both abstracts

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_valid_concrete_can_be_instantiated(self):
        from src.services.search.providers.base import SearchProvider

        class ValidProvider(SearchProvider):
            @property
            def provider_name(self) -> str:
                return "Valid"

            def search(self, query, max_results=10):
                return []

        p = ValidProvider()
        assert p.provider_name == "Valid"
        assert p.search("test") == []


# ---------------------------------------------------------------------------
# SearchProviderError
# ---------------------------------------------------------------------------


class TestSearchProviderError:
    def test_message_format(self):
        from src.services.search.providers.base import SearchProviderError

        err = SearchProviderError("Tavily", "quota exceeded")
        assert "Tavily" in str(err)
        assert "quota exceeded" in str(err)

    def test_original_preserved(self):
        from src.services.search.providers.base import SearchProviderError

        original = ValueError("upstream")
        err = SearchProviderError("Brave", "bad request", original=original)
        assert err.original is original


# ---------------------------------------------------------------------------
# TavilySearchProvider
# ---------------------------------------------------------------------------


class TestTavilySearchProvider:
    """Tests for TavilySearchProvider.

    Since tavily-python may not be installed, we mock the tavily module
    in sys.modules so that the lazy ``from tavily import TavilyClient``
    inside ``__init__`` resolves to our fake.
    """

    def _tavily_sys_patch(self, mock_client=None):
        """Context manager that installs a fake 'tavily' module in sys.modules."""
        fake_tavily = MagicMock()
        if mock_client is not None:
            fake_tavily.TavilyClient.return_value = mock_client
        return patch.dict("sys.modules", {"tavily": fake_tavily})

    def _make_provider(self, api_key="test-key", mock_client=None):
        """Construct TavilySearchProvider with sys.modules-patched tavily."""
        from src.services.search.providers.tavily import TavilySearchProvider

        with self._tavily_sys_patch(mock_client=mock_client):
            provider = TavilySearchProvider(api_key=api_key)
            if mock_client is not None:
                provider._client = mock_client
        return provider

    def test_provider_name(self):
        from src.services.search.providers.tavily import TavilySearchProvider

        with self._tavily_sys_patch():
            p = TavilySearchProvider(api_key="k")
        assert p.provider_name == "Tavily"

    def test_empty_api_key_raises_value_error(self):
        from src.services.search.providers.tavily import TavilySearchProvider

        with self._tavily_sys_patch():
            with pytest.raises(ValueError, match="api_key"):
                TavilySearchProvider(api_key="")

    def test_import_error_if_tavily_missing(self):
        """Provider raises ImportError with install hint when tavily is absent."""
        with patch.dict("sys.modules", {"tavily": None}):
            from src.services.search.providers import tavily as tavily_mod
            import importlib
            with pytest.raises((ImportError, AttributeError)):
                importlib.reload(tavily_mod)
                tavily_mod.TavilySearchProvider(api_key="k")

    def test_search_happy_path(self):
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [
                {"title": "Alpha", "url": "https://alpha.io", "content": "About Alpha.", "score": 0.9},
                {"title": "Beta", "url": "https://beta.io", "content": "About Beta.", "score": 0.7},
            ]
        }
        provider = self._make_provider(mock_client=mock_client)

        results = provider.search("what is alpha?", max_results=5)

        mock_client.search.assert_called_once_with(
            query="what is alpha?",
            search_depth="basic",
            max_results=5,
            include_answer=False,
            include_raw_content=False,
        )
        assert len(results) == 2
        assert results[0].title == "Alpha"
        assert results[0].url == "https://alpha.io"
        assert results[0].snippet == "About Alpha."
        assert results[0].source == "alpha.io"
        assert results[0].score == pytest.approx(0.9)

    def test_search_empty_query_returns_empty_list(self):
        mock_client = MagicMock()
        provider = self._make_provider(mock_client=mock_client)

        results = provider.search("")
        assert results == []
        mock_client.search.assert_not_called()

    def test_search_empty_results(self):
        mock_client = MagicMock()
        mock_client.search.return_value = {"results": []}
        provider = self._make_provider(mock_client=mock_client)

        assert provider.search("no results query") == []

    def test_search_api_error_raises_provider_error(self):
        from src.services.search.providers.base import SearchProviderError

        mock_client = MagicMock()
        mock_client.search.side_effect = RuntimeError("rate limit exceeded")
        provider = self._make_provider(mock_client=mock_client)

        with pytest.raises(SearchProviderError) as exc_info:
            provider.search("query")

        assert "Tavily" in str(exc_info.value)
        assert exc_info.value.original is not None

    def test_max_results_capped_at_20(self):
        mock_client = MagicMock()
        mock_client.search.return_value = {"results": []}
        provider = self._make_provider(mock_client=mock_client)

        provider.search("q", max_results=50)
        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs["max_results"] == 20

    def test_result_missing_title_uses_fallback(self):
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [{"url": "https://x.com", "content": "Some content.", "score": 0.5}]
        }
        provider = self._make_provider(mock_client=mock_client)
        results = provider.search("q")
        assert results[0].title == "(no title)"


# ---------------------------------------------------------------------------
# BraveSearchProvider
# ---------------------------------------------------------------------------


class TestBraveSearchProvider:
    def test_provider_name(self):
        from src.services.search.providers.brave import BraveSearchProvider

        p = BraveSearchProvider(api_key="k")
        assert p.provider_name == "Brave"

    def test_empty_api_key_raises_value_error(self):
        from src.services.search.providers.brave import BraveSearchProvider

        with pytest.raises(ValueError, match="api_key"):
            BraveSearchProvider(api_key="")

    def test_search_happy_path(self):
        from src.services.search.providers.brave import BraveSearchProvider

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "web": {
                "results": [
                    {"title": "Gamma", "url": "https://gamma.io", "description": "Gamma desc."},
                    {"title": "Delta", "url": "https://delta.io", "description": "Delta desc."},
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("src.services.search.providers.brave.httpx.get", return_value=mock_response) as mock_get:
            provider = BraveSearchProvider(api_key="brave-key")
            results = provider.search("test query", max_results=5)

        mock_get.assert_called_once()
        params = mock_get.call_args.kwargs["params"]
        assert params["q"] == "test query"
        assert params["count"] == 5

        assert len(results) == 2
        assert results[0].title == "Gamma"
        assert results[0].snippet == "Gamma desc."
        assert results[0].source == "gamma.io"
        assert results[0].score is None  # Brave doesn't expose scores

    def test_search_empty_query_returns_empty(self):
        from src.services.search.providers.brave import BraveSearchProvider

        with patch("src.services.search.providers.brave.httpx.get") as mock_get:
            provider = BraveSearchProvider(api_key="k")
            results = provider.search("   ")
            assert results == []
            mock_get.assert_not_called()

    def test_search_http_error_raises_provider_error(self):
        import httpx
        from src.services.search.providers.base import SearchProviderError
        from src.services.search.providers.brave import BraveSearchProvider

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        http_error = httpx.HTTPStatusError("401", request=MagicMock(), response=mock_response)
        mock_response.raise_for_status.side_effect = http_error

        with patch("src.services.search.providers.brave.httpx.get", return_value=mock_response):
            provider = BraveSearchProvider(api_key="bad-key")
            with pytest.raises(SearchProviderError) as exc_info:
                provider.search("query")

        assert "Brave" in str(exc_info.value)

    def test_search_network_error_raises_provider_error(self):
        import httpx
        from src.services.search.providers.base import SearchProviderError
        from src.services.search.providers.brave import BraveSearchProvider

        with patch(
            "src.services.search.providers.brave.httpx.get",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            provider = BraveSearchProvider(api_key="k")
            with pytest.raises(SearchProviderError) as exc_info:
                provider.search("query")

        assert exc_info.value.provider_name == "Brave"

    def test_max_results_clamped_to_1_20(self):
        from src.services.search.providers.brave import BraveSearchProvider

        mock_response = MagicMock()
        mock_response.json.return_value = {"web": {"results": []}}
        mock_response.raise_for_status = MagicMock()

        with patch("src.services.search.providers.brave.httpx.get", return_value=mock_response) as mock_get:
            BraveSearchProvider(api_key="k").search("q", max_results=999)
            params = mock_get.call_args.kwargs["params"]
            assert params["count"] == 20


# ---------------------------------------------------------------------------
# SearchService
# ---------------------------------------------------------------------------


class TestSearchService:
    def _make_stub_provider(self, results=None, name="StubProvider", raises=None):
        from src.services.search.providers.base import SearchProvider

        class StubProvider(SearchProvider):
            @property
            def provider_name(self):
                return name

            def search(self, query, max_results=10):
                if raises:
                    raise raises
                return results or []

        return StubProvider()

    def test_none_provider_raises_value_error(self):
        from src.services.search.search_service import SearchService

        with pytest.raises(ValueError):
            SearchService(provider=None)  # type: ignore[arg-type]

    def test_provider_name_exposed(self):
        from src.services.search.search_service import SearchService

        provider = self._make_stub_provider(name="MyEngine")
        svc = SearchService(provider=provider)
        assert svc.provider_name == "MyEngine"

    def test_empty_query_raises_value_error(self):
        from src.services.search.search_service import SearchService

        svc = SearchService(provider=self._make_stub_provider())
        with pytest.raises(ValueError, match="non-empty"):
            svc.search("   ")

    def test_search_delegates_to_provider(self):
        from src.services.search.models import SearchResult
        from src.services.search.search_service import SearchService

        expected = [SearchResult("T", "u", "s", "src")]
        svc = SearchService(provider=self._make_stub_provider(results=expected))
        results = svc.search("some query")
        assert results == expected

    def test_search_strips_query_before_delegating(self):
        from src.services.search.providers.base import SearchProvider
        from src.services.search.search_service import SearchService

        received_queries: list[str] = []

        class Spy(SearchProvider):
            @property
            def provider_name(self):
                return "Spy"

            def search(self, query, max_results=10):
                received_queries.append(query)
                return []

        svc = SearchService(provider=Spy())
        svc.search("  hello world  ")
        assert received_queries == ["hello world"]

    def test_default_max_results_used_when_not_overridden(self):
        from src.services.search.providers.base import SearchProvider
        from src.services.search.search_service import SearchService

        limits_seen: list[int] = []

        class Spy(SearchProvider):
            @property
            def provider_name(self):
                return "Spy"

            def search(self, query, max_results=10):
                limits_seen.append(max_results)
                return []

        svc = SearchService(provider=Spy(), max_results=7)
        svc.search("q")
        assert limits_seen == [7]

    def test_per_call_max_results_overrides_default(self):
        from src.services.search.providers.base import SearchProvider
        from src.services.search.search_service import SearchService

        limits_seen: list[int] = []

        class Spy(SearchProvider):
            @property
            def provider_name(self):
                return "Spy"

            def search(self, query, max_results=10):
                limits_seen.append(max_results)
                return []

        svc = SearchService(provider=Spy(), max_results=7)
        svc.search("q", max_results=3)
        assert limits_seen == [3]

    def test_provider_error_propagates(self):
        from src.services.search.providers.base import SearchProviderError
        from src.services.search.search_service import SearchService

        err = SearchProviderError("StubProvider", "quota exceeded")
        svc = SearchService(provider=self._make_stub_provider(raises=err))
        with pytest.raises(SearchProviderError):
            svc.search("q")

    def test_unexpected_error_wrapped_as_provider_error(self):
        from src.services.search.providers.base import SearchProviderError
        from src.services.search.search_service import SearchService

        svc = SearchService(provider=self._make_stub_provider(raises=RuntimeError("unexpected")))
        with pytest.raises(SearchProviderError) as exc_info:
            svc.search("q")
        assert exc_info.value.original is not None

    def test_search_to_dicts_returns_serialisable_list(self):
        from src.services.search.models import SearchResult
        from src.services.search.search_service import SearchService

        results = [SearchResult("T", "u", "s", "src", score=0.5)]
        svc = SearchService(provider=self._make_stub_provider(results=results))
        dicts = svc.search_to_dicts("q")
        assert isinstance(dicts, list)
        assert dicts[0]["title"] == "T"
        assert dicts[0]["score"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Settings.build_search_service
# ---------------------------------------------------------------------------


class TestSettingsBuildSearchService:
    def test_tavily_preferred_over_brave(self):
        from src.config.settings import Settings

        fake_tavily = MagicMock()
        settings = Settings(tavily_api_key="tav-key", brave_search_api_key="brave-key")
        with patch.dict("sys.modules", {"tavily": fake_tavily}):
            svc = settings.build_search_service()
        assert svc.provider_name == "Tavily"

    def test_brave_used_when_tavily_absent(self):
        from src.config.settings import Settings

        settings = Settings(brave_search_api_key="brave-key")
        svc = settings.build_search_service()
        assert svc.provider_name == "Brave"

    def test_no_keys_raises_runtime_error(self):
        from src.config.settings import Settings

        settings = Settings()
        with pytest.raises(RuntimeError, match="TAVILY_API_KEY"):
            settings.build_search_service()
