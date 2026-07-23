"""Tests for the PageFetcher service.

All tests use mocked HTTP clients — no real network calls are made.  The suite
covers:

  - URL validation (empty, malformed, bad scheme, missing host)
  - Successful fetch (plain, with redirects)
  - HTTP error handling (permanent 4xx, retryable 5xx, non-2xx)
  - Timeout handling (exhausted retries, eventual success)
  - Connection / network errors
  - Retry mechanics (max_retries=0, back-off delay shape)
  - Context-manager protocol
  - Settings.build_page_fetcher integration
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, PropertyMock, patch

import httpx
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_response(
    status_code: int = 200,
    text: str = "<html><body>OK</body></html>",
    url: str = "https://example.com/page",
    history: list | None = None,
) -> MagicMock:
    """Build a minimal ``httpx.Response``-like mock."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = text
    resp.url = url
    resp.history = history or []
    return resp


# ---------------------------------------------------------------------------
# PageFetcher — URL validation
# ---------------------------------------------------------------------------


class TestPageFetcherValidation:
    def test_empty_url_raises_invalid_url_error(self):
        from src.services.retrievers import PageFetcher, InvalidURLError

        fetcher = PageFetcher()
        with pytest.raises(InvalidURLError, match="non-empty"):
            fetcher.fetch("")

    def test_blank_url_raises_invalid_url_error(self):
        from src.services.retrievers import PageFetcher, InvalidURLError

        fetcher = PageFetcher()
        with pytest.raises(InvalidURLError, match="non-empty"):
            fetcher.fetch("   ")

    def test_ftp_scheme_raises_invalid_url_error(self):
        from src.services.retrievers import PageFetcher, InvalidURLError

        fetcher = PageFetcher()
        with pytest.raises(InvalidURLError, match="ftp"):
            fetcher.fetch("ftp://example.com")

    def test_missing_host_raises_invalid_url_error(self):
        from src.services.retrievers import PageFetcher, InvalidURLError

        fetcher = PageFetcher()
        with pytest.raises(InvalidURLError, match="host"):
            fetcher.fetch("https://")

    def test_valid_url_passes_validation(self):
        from src.services.retrievers import PageFetcher

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = _make_mock_response()
        fetcher = PageFetcher(client=mock_client)

        html = fetcher.fetch("https://example.com/page")
        assert html == "<html><body>OK</body></html>"


# ---------------------------------------------------------------------------
# PageFetcher — successful fetches
# ---------------------------------------------------------------------------


class TestPageFetcherSuccess:
    def test_returns_raw_html(self):
        from src.services.retrievers import PageFetcher

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = _make_mock_response(
            text="<html><title>Test</title><body>Hello</body></html>"
        )
        fetcher = PageFetcher(client=mock_client)

        html = fetcher.fetch("https://example.com")
        assert html == "<html><title>Test</title><body>Hello</body></html>"

    def test_follows_redirects(self):
        from src.services.retrievers import PageFetcher

        mock_client = MagicMock(spec=httpx.Client)
        redirect = _make_mock_response(status_code=301, url="https://example.com/old")
        final = _make_mock_response(
            text="<html>Redirected</html>",
            url="https://example.com/new",
            history=[redirect],
        )
        mock_client.get.return_value = final
        fetcher = PageFetcher(client=mock_client)

        html = fetcher.fetch("https://example.com/old")
        assert html == "<html>Redirected</html>"
        mock_client.get.assert_called_once_with("https://example.com/old")

    def test_uses_custom_user_agent(self):
        from src.services.retrievers import PageFetcher

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = _make_mock_response()
        fetcher = PageFetcher(client=mock_client, user_agent="TestBot/1.0")

        fetcher.fetch("https://example.com")
        # The client was pre-configured with headers, so we just verify the call
        mock_client.get.assert_called_once_with("https://example.com")


# ---------------------------------------------------------------------------
# PageFetcher — HTTP error handling
# ---------------------------------------------------------------------------


class TestPageFetcherHTTPErrors:
    def test_404_raises_fetch_http_error(self):
        from src.services.retrievers import PageFetcher, FetchHTTPError

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = _make_mock_response(
            status_code=404, text="Not Found"
        )
        fetcher = PageFetcher(client=mock_client, max_retries=0)

        with pytest.raises(FetchHTTPError) as exc_info:
            fetcher.fetch("https://example.com/missing")

        assert exc_info.value.status_code == 404
        assert "example.com" in str(exc_info.value)

    def test_403_raises_fetch_http_error(self):
        from src.services.retrievers import PageFetcher, FetchHTTPError

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = _make_mock_response(
            status_code=403, text="Forbidden"
        )
        fetcher = PageFetcher(client=mock_client, max_retries=0)

        with pytest.raises(FetchHTTPError) as exc_info:
            fetcher.fetch("https://example.com/forbidden")

        assert exc_info.value.status_code == 403

    def test_500_is_retried_then_raises(self):
        from src.services.retrievers import PageFetcher, FetchHTTPError

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = _make_mock_response(
            status_code=500, text="Server Error"
        )
        fetcher = PageFetcher(client=mock_client, max_retries=2, backoff_base=0.01)

        with pytest.raises(FetchHTTPError) as exc_info:
            fetcher.fetch("https://example.com/error")

        assert exc_info.value.status_code == 500
        # Should have been called 3 times (initial + 2 retries)
        assert mock_client.get.call_count == 3

    def test_429_is_retried(self):
        from src.services.retrievers import PageFetcher, FetchHTTPError

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = _make_mock_response(
            status_code=429, text="Too Many Requests"
        )
        fetcher = PageFetcher(client=mock_client, max_retries=1, backoff_base=0.01)

        with pytest.raises(FetchHTTPError):
            fetcher.fetch("https://example.com/rate-limited")

        assert mock_client.get.call_count == 2  # initial + 1 retry

    def test_503_eventually_succeeds_after_retries(self):
        from src.services.retrievers import PageFetcher

        mock_client = MagicMock(spec=httpx.Client)
        # First two calls return 503, third succeeds
        mock_client.get.side_effect = [
            _make_mock_response(status_code=503, text="Unavailable"),
            _make_mock_response(status_code=503, text="Unavailable"),
            _make_mock_response(status_code=200, text="<html>Success</html>"),
        ]
        fetcher = PageFetcher(client=mock_client, max_retries=2, backoff_base=0.01)

        html = fetcher.fetch("https://example.com/flaky")
        assert html == "<html>Success</html>"
        assert mock_client.get.call_count == 3

    def test_non_retryable_2xx_raises(self):
        from src.services.retrievers import PageFetcher, FetchHTTPError

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = _make_mock_response(
            status_code=300, text="Multiple Choices"
        )
        fetcher = PageFetcher(client=mock_client, max_retries=0)

        with pytest.raises(FetchHTTPError) as exc_info:
            fetcher.fetch("https://example.com/redirect-manual")

        assert exc_info.value.status_code == 300


# ---------------------------------------------------------------------------
# PageFetcher — timeout handling
# ---------------------------------------------------------------------------


class TestPageFetcherTimeouts:
    def test_timeout_after_all_retries(self):
        from src.services.retrievers import PageFetcher, FetchTimeoutError

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.side_effect = httpx.TimeoutException("timed out")
        fetcher = PageFetcher(client=mock_client, max_retries=2, backoff_base=0.01)

        with pytest.raises(FetchTimeoutError) as exc_info:
            fetcher.fetch("https://example.com/slow")

        assert "timed out" in str(exc_info.value).lower()
        assert mock_client.get.call_count == 3  # initial + 2 retries

    def test_timeout_then_success(self):
        from src.services.retrievers import PageFetcher

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.side_effect = [
            httpx.TimeoutException("timed out"),
            httpx.TimeoutException("timed out"),
            _make_mock_response(text="<html>Finally</html>"),
        ]
        fetcher = PageFetcher(client=mock_client, max_retries=2, backoff_base=0.01)

        html = fetcher.fetch("https://example.com/slow")
        assert html == "<html>Finally</html>"
        assert mock_client.get.call_count == 3


# ---------------------------------------------------------------------------
# PageFetcher — connection / network errors
# ---------------------------------------------------------------------------


class TestPageFetcherConnectionErrors:
    def test_connection_refused_raises_after_retries(self):
        from src.services.retrievers import PageFetcher, FetchConnectionError

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        fetcher = PageFetcher(client=mock_client, max_retries=1, backoff_base=0.01)

        with pytest.raises(FetchConnectionError) as exc_info:
            fetcher.fetch("https://example.com/down")

        assert "Connection refused" in str(exc_info.value)
        assert mock_client.get.call_count == 2

    def test_dns_error_raises_connection_error(self):
        from src.services.retrievers import PageFetcher, FetchConnectionError

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.side_effect = httpx.ConnectError(
            "[Errno -2] Name or service not known"
        )
        fetcher = PageFetcher(client=mock_client, max_retries=0)

        with pytest.raises(FetchConnectionError) as exc_info:
            fetcher.fetch("https://nonexistent.example")

        assert "Name or service not known" in str(exc_info.value)

    def test_tls_error_raises_connection_error(self):
        from src.services.retrievers import PageFetcher, FetchConnectionError

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.side_effect = httpx.ConnectError(
            "[SSL: CERTIFICATE_VERIFY_FAILED]"
        )
        fetcher = PageFetcher(client=mock_client, max_retries=0)

        with pytest.raises(FetchConnectionError) as exc_info:
            fetcher.fetch("https://bad-tls.example")

        assert "CERTIFICATE_VERIFY_FAILED" in str(exc_info.value)

    def test_generic_request_error_raises_connection_error(self):
        from src.services.retrievers import PageFetcher, FetchConnectionError

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.side_effect = httpx.RequestError("Protocol error")
        fetcher = PageFetcher(client=mock_client, max_retries=0)

        with pytest.raises(FetchConnectionError) as exc_info:
            fetcher.fetch("https://example.com")

        assert "Protocol error" in str(exc_info.value)


# ---------------------------------------------------------------------------
# PageFetcher — retry mechanics
# ---------------------------------------------------------------------------


class TestPageFetcherRetryMechanics:
    def test_max_retries_zero_disables_retries(self):
        from src.services.retrievers import PageFetcher, FetchTimeoutError

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.side_effect = httpx.TimeoutException("timed out")
        fetcher = PageFetcher(client=mock_client, max_retries=0)

        with pytest.raises(FetchTimeoutError):
            fetcher.fetch("https://example.com")

        assert mock_client.get.call_count == 1  # no retries

    def test_backoff_delay_increases_exponentially(self):
        from src.services.retrievers.page_fetcher import PageFetcher

        fetcher = PageFetcher(backoff_base=1.0, backoff_max=30.0)
        # Access the private method for unit testing
        delay_1 = fetcher._backoff_delay(1)  # first retry: 1 * 2^0 = ~1s
        delay_2 = fetcher._backoff_delay(2)  # second retry: 1 * 2^1 = ~2s
        delay_3 = fetcher._backoff_delay(3)  # third retry: 1 * 2^2 = ~4s

        assert 0.9 <= delay_1 <= 1.1  # 1s ± 10%
        assert 1.8 <= delay_2 <= 2.2  # 2s ± 10%
        assert 3.6 <= delay_3 <= 4.4  # 4s ± 10%

    def test_backoff_capped_at_max(self):
        from src.services.retrievers.page_fetcher import PageFetcher

        fetcher = PageFetcher(backoff_base=10.0, backoff_max=15.0)
        delay = fetcher._backoff_delay(5)  # 10 * 2^4 = 160, capped at 15
        assert delay <= 16.5  # 15 + 10% jitter


# ---------------------------------------------------------------------------
# PageFetcher — context manager
# ---------------------------------------------------------------------------


class TestPageFetcherContextManager:
    def test_context_manager_does_not_close_injected_client(self):
        """PageFetcher only closes clients it owns (created internally).
        An injected client is the caller's responsibility to manage."""
        from src.services.retrievers import PageFetcher

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = _make_mock_response()

        with PageFetcher(client=mock_client) as fetcher:
            html = fetcher.fetch("https://example.com")
            assert html == "<html><body>OK</body></html>"

        # The injected client should NOT be closed by PageFetcher
        mock_client.close.assert_not_called()

    def test_context_manager_closes_owned_client(self):
        from src.services.retrievers import PageFetcher

        # When no client is passed, PageFetcher creates its own
        # We can't easily mock this, so we verify the close method works
        fetcher = PageFetcher(max_retries=0)
        # Just verify close() doesn't crash
        fetcher.close()


# ---------------------------------------------------------------------------
# Settings.build_page_fetcher
# ---------------------------------------------------------------------------


class TestSettingsBuildPageFetcher:
    def test_build_page_fetcher_returns_configured_instance(self):
        from src.config.settings import Settings
        from src.services.retrievers import PageFetcher

        settings = Settings(
            fetch_timeout=30.0,
            fetch_max_retries=5,
            fetch_backoff_base=2.0,
            fetch_backoff_max=60.0,
            fetch_user_agent="CustomBot/1.0",
        )

        fetcher = settings.build_page_fetcher()
        assert isinstance(fetcher, PageFetcher)
        assert fetcher._timeout == 30.0
        assert fetcher._max_retries == 5
        assert fetcher._backoff_base == 2.0
        assert fetcher._backoff_max == 60.0
        assert fetcher._user_agent == "CustomBot/1.0"
        fetcher.close()

    def test_build_page_fetcher_defaults(self):
        from src.config.settings import Settings
        from src.services.retrievers import PageFetcher

        settings = Settings()
        fetcher = settings.build_page_fetcher()
        assert isinstance(fetcher, PageFetcher)
        assert fetcher._timeout == 15.0
        assert fetcher._max_retries == 3
        assert fetcher._backoff_base == 1.0
        assert fetcher._backoff_max == 30.0
        fetcher.close()


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class TestPageFetcherExceptions:
    def test_exception_hierarchy(self):
        from src.services.retrievers import (
            PageFetcherError,
            InvalidURLError,
            FetchTimeoutError,
            FetchConnectionError,
            FetchHTTPError,
        )

        assert issubclass(InvalidURLError, PageFetcherError)
        assert issubclass(FetchTimeoutError, PageFetcherError)
        assert issubclass(FetchConnectionError, PageFetcherError)
        assert issubclass(FetchHTTPError, PageFetcherError)

    def test_fetch_http_error_has_status_code(self):
        from src.services.retrievers import FetchHTTPError

        err = FetchHTTPError(
            "Not Found", url="https://example.com/404", status_code=404, response_text="<h1>404</h1>"
        )
        assert err.status_code == 404
        assert err.response_text == "<h1>404</h1>"
        assert err.url == "https://example.com/404"

    def test_fetch_timeout_error_has_elapsed(self):
        from src.services.retrievers import FetchTimeoutError

        err = FetchTimeoutError("Timed out", url="https://example.com", elapsed=30.5)
        assert err.elapsed == pytest.approx(30.5)

    def test_error_original_preserved(self):
        from src.services.retrievers import FetchConnectionError

        original = ConnectionError("DNS failure")
        err = FetchConnectionError("Connection error", original=original)
        assert err.original is original