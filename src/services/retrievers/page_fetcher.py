"""PageFetcher — raw HTML retrieval service.

This module is the *only* component responsible for downloading web pages.
It deliberately does **not** parse, clean, extract text from, or summarise
the HTML it retrieves.  Its single responsibility is::

    html: str = fetcher.fetch(url)

Design decisions
----------------
* ``httpx`` is already in the project's requirements — no new dependency is
  introduced.
* The HTTP client is injected at construction time so tests can pass a mock
  without making real network calls.
* Retry logic lives entirely in this class; the caller never sees transient
  failures as long as retries succeed.
* Only transient failures are retried.  ``4xx`` responses (except 429) are
  considered permanent and are not retried.
* Exponential back-off with jitter is used between retry attempts.
"""

from __future__ import annotations

import logging
import time
import random
from urllib.parse import urlparse

import httpx

from ...shared.logging import get_logger
from .exceptions import (
    FetchConnectionError,
    FetchHTTPError,
    FetchTimeoutError,
    InvalidURLError,
    PageFetcherError,
)

logger: logging.Logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants / defaults
# ---------------------------------------------------------------------------

_DEFAULT_TIMEOUT: float = 15.0          # seconds
_DEFAULT_MAX_RETRIES: int = 3
_DEFAULT_BACKOFF_BASE: float = 1.0      # seconds — doubles on each retry
_DEFAULT_BACKOFF_MAX: float = 30.0      # seconds — cap on back-off delay
_DEFAULT_USER_AGENT: str = (
    "Mozilla/5.0 (compatible; EnterpriseKnowledgeFetcher/1.0; +https://ha-shem.com/bot)"
)

# HTTP status codes that are considered *transient* and should be retried.
_RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({429, 500, 502, 503, 504})

# Allowed URL schemes.
_ALLOWED_SCHEMES: frozenset[str] = frozenset({"http", "https"})


# ---------------------------------------------------------------------------
# PageFetcher
# ---------------------------------------------------------------------------


class PageFetcher:
    """Downloads raw HTML from a URL.

    The fetcher validates the URL, performs an HTTP GET request with the
    configured timeout and follow-redirect settings, and returns the raw
    response body as a string.  It retries transient failures with
    exponential back-off.

    Args:
        client:        An ``httpx.Client``-compatible object.  When ``None``
                       (the default) a new ``httpx.Client`` is created
                       internally.  Pass a custom or mocked client to override
                       the HTTP transport layer entirely.
        timeout:       Request timeout in seconds.  Defaults to
                       ``_DEFAULT_TIMEOUT``.
        max_retries:   Maximum number of retry attempts for transient errors.
                       Set to ``0`` to disable retries.  Defaults to
                       ``_DEFAULT_MAX_RETRIES``.
        backoff_base:  Initial back-off delay in seconds.  The delay doubles
                       on each consecutive retry up to ``backoff_max``.
                       Defaults to ``_DEFAULT_BACKOFF_BASE``.
        backoff_max:   Upper bound on back-off delay in seconds.  Defaults to
                       ``_DEFAULT_BACKOFF_MAX``.
        user_agent:    Value for the ``User-Agent`` HTTP request header.
        follow_redirects: Whether to follow HTTP redirects.  Defaults to
                       ``True``.

    Raises:
        InvalidURLError:      If the URL fails validation before the request.
        FetchTimeoutError:    If all attempts time out.
        FetchConnectionError: If a network-level error persists after retries.
        FetchHTTPError:       If the server responds with a non-retryable error
                              status code.

    Example::

        fetcher = PageFetcher()
        html = fetcher.fetch("https://example.com/page")
    """

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        backoff_base: float = _DEFAULT_BACKOFF_BASE,
        backoff_max: float = _DEFAULT_BACKOFF_MAX,
        user_agent: str = _DEFAULT_USER_AGENT,
        follow_redirects: bool = True,
    ) -> None:
        self._owns_client = client is None
        self._client: httpx.Client = client or httpx.Client(
            timeout=httpx.Timeout(timeout),
            follow_redirects=follow_redirects,
            headers={"User-Agent": user_agent},
        )
        self._timeout = timeout
        self._max_retries = max(0, max_retries)
        self._backoff_base = backoff_base
        self._backoff_max = backoff_max
        self._user_agent = user_agent
        self._follow_redirects = follow_redirects

        logger.info(
            "PageFetcher initialised (timeout=%.1fs, max_retries=%d, follow_redirects=%s).",
            timeout,
            self._max_retries,
            follow_redirects,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch(self, url: str) -> str:
        """Download the raw HTML at *url* and return it as a string.

        Args:
            url: The fully-qualified URL to fetch.  Must use ``http`` or
                 ``https``.

        Returns:
            The raw response body as a UTF-8 string.  The caller is
            responsible for all subsequent parsing or processing.

        Raises:
            InvalidURLError:      The URL is empty, structurally malformed, or
                                  uses a non-HTTP/S scheme.
            FetchTimeoutError:    The request timed out on every attempt.
            FetchConnectionError: A network-level failure occurred on every
                                  attempt.
            FetchHTTPError:       The server returned a non-success, non-
                                  retryable HTTP status code.
        """
        self._validate_url(url)

        last_exc: Exception | None = None
        attempt = 0

        while attempt <= self._max_retries:
            if attempt > 0:
                delay = self._backoff_delay(attempt)
                logger.info(
                    "PageFetcher: retrying %r (attempt %d/%d) after %.2fs back-off.",
                    url,
                    attempt,
                    self._max_retries,
                    delay,
                )
                time.sleep(delay)

            logger.info("PageFetcher: GET %r (attempt %d).", url, attempt + 1)
            t_start = time.monotonic()

            try:
                response = self._client.get(url)
                elapsed = time.monotonic() - t_start

                # Log redirect chain if any
                if response.history:
                    hops = " → ".join(str(r.url) for r in response.history)
                    logger.info(
                        "PageFetcher: redirect chain for %r — %s → %s",
                        url,
                        hops,
                        response.url,
                    )

                logger.info(
                    "PageFetcher: %r → HTTP %d in %.3fs.",
                    url,
                    response.status_code,
                    elapsed,
                )

                # Permanent client errors — do not retry
                if response.status_code in {400, 401, 403, 404, 405, 410}:
                    raise FetchHTTPError(
                        f"HTTP {response.status_code} for {url!r}.",
                        url=url,
                        status_code=response.status_code,
                        response_text=response.text[:500],
                    )

                # Retryable server errors
                if response.status_code in _RETRYABLE_STATUS_CODES:
                    last_exc = FetchHTTPError(
                        f"HTTP {response.status_code} (transient) for {url!r}.",
                        url=url,
                        status_code=response.status_code,
                        response_text=response.text[:500],
                    )
                    attempt += 1
                    continue

                # Any other non-2xx
                if not (200 <= response.status_code < 300):
                    raise FetchHTTPError(
                        f"HTTP {response.status_code} for {url!r}.",
                        url=url,
                        status_code=response.status_code,
                        response_text=response.text[:500],
                    )

                # Success — return raw body
                return response.text

            except FetchHTTPError:
                # Permanent HTTP errors bubble up immediately.
                raise

            except httpx.TimeoutException as exc:
                elapsed = time.monotonic() - t_start
                logger.warning(
                    "PageFetcher: timeout fetching %r after %.3fs (attempt %d).",
                    url,
                    elapsed,
                    attempt + 1,
                )
                last_exc = FetchTimeoutError(
                    f"Request to {url!r} timed out after {elapsed:.1f}s.",
                    url=url,
                    original=exc,
                    elapsed=elapsed,
                )
                attempt += 1

            except httpx.ConnectError as exc:
                logger.warning(
                    "PageFetcher: connection error fetching %r (attempt %d) — %s.",
                    url,
                    attempt + 1,
                    exc,
                )
                last_exc = FetchConnectionError(
                    f"Connection error fetching {url!r}: {exc}",
                    url=url,
                    original=exc,
                )
                attempt += 1

            except httpx.RequestError as exc:
                # Other transport-level errors (e.g. TLS failure, protocol error)
                logger.warning(
                    "PageFetcher: request error fetching %r (attempt %d) — %s.",
                    url,
                    attempt + 1,
                    exc,
                )
                last_exc = FetchConnectionError(
                    f"Request error fetching {url!r}: {exc}",
                    url=url,
                    original=exc,
                )
                attempt += 1

        # All attempts exhausted — raise the last recorded error
        logger.error(
            "PageFetcher: all %d attempt(s) failed for %r.",
            self._max_retries + 1,
            url,
        )
        assert last_exc is not None  # loop invariant — always set on failure path
        raise last_exc

    def close(self) -> None:
        """Close the underlying HTTP client if it was created internally."""
        if self._owns_client:
            self._client.close()
            logger.debug("PageFetcher: HTTP client closed.")

    # ------------------------------------------------------------------
    # Context-manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "PageFetcher":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_url(url: str) -> None:
        """Raise :class:`InvalidURLError` if *url* is not a valid HTTP/S URL.

        Checks:
        1. The URL must be a non-empty string.
        2. It must be parseable by ``urllib.parse.urlparse``.
        3. The scheme must be ``http`` or ``https``.
        4. A non-empty host component must be present.
        """
        if not url or not url.strip():
            raise InvalidURLError("URL must be a non-empty string.", url=url)

        try:
            parsed = urlparse(url.strip())
        except Exception as exc:
            raise InvalidURLError(
                f"URL could not be parsed: {exc}", url=url, original=exc
            ) from exc

        if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
            raise InvalidURLError(
                f"URL scheme {parsed.scheme!r} is not allowed. "
                f"Only {sorted(_ALLOWED_SCHEMES)} are supported.",
                url=url,
            )

        if not parsed.netloc:
            raise InvalidURLError(
                f"URL {url!r} is missing a host component.",
                url=url,
            )

    def _backoff_delay(self, attempt: int) -> float:
        """Return an exponentially increasing delay with ±10 % jitter.

        Args:
            attempt: The 1-based retry attempt number (first retry = 1).

        Returns:
            A delay in seconds, clamped to ``[0, backoff_max]``.
        """
        raw_delay = self._backoff_base * (2 ** (attempt - 1))
        # ±10 % random jitter to spread retries across multiple clients
        jitter = raw_delay * 0.1 * (2 * random.random() - 1)
        return max(0.0, min(raw_delay + jitter, self._backoff_max))
