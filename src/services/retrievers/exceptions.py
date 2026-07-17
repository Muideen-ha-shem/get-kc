"""Custom exceptions for the PageFetcher service.

All HTTP-client-specific exceptions are caught inside ``PageFetcher`` and
re-raised as one of the classes defined here.  Callers therefore never need
to import ``httpx`` or know which HTTP client is in use.

Hierarchy::

    PageFetcherError          (base — always catch this one in broad handlers)
    ├── InvalidURLError       — URL failed validation before any network call
    ├── FetchTimeoutError     — request timed out (possibly after retries)
    ├── FetchConnectionError  — network-level failure (DNS, refused, etc.)
    └── FetchHTTPError        — server responded with an error status code
"""

from __future__ import annotations


class PageFetcherError(RuntimeError):
    """Base class for all PageFetcher failures.

    Attributes:
        url:      The URL that was being fetched when the error occurred.
        original: The underlying low-level exception, if any.
    """

    def __init__(self, message: str, url: str = "", original: Exception | None = None) -> None:
        super().__init__(message)
        self.url = url
        self.original = original


class InvalidURLError(PageFetcherError):
    """Raised when the supplied URL fails validation before any network call.

    This covers empty strings, missing schemes, non-HTTP/S protocols, and
    structurally malformed URLs.

    Example::

        raise InvalidURLError("URL must use http or https.", url="ftp://example.com")
    """


class FetchTimeoutError(PageFetcherError):
    """Raised when the HTTP request times out (after all retry attempts).

    Attributes:
        elapsed: Total elapsed time in seconds across all attempts, if known.
    """

    def __init__(
        self,
        message: str,
        url: str = "",
        original: Exception | None = None,
        elapsed: float | None = None,
    ) -> None:
        super().__init__(message, url=url, original=original)
        self.elapsed = elapsed


class FetchConnectionError(PageFetcherError):
    """Raised on network-level failures such as DNS resolution errors,
    connection refused, or TLS handshake failures (after all retry attempts).
    """


class FetchHTTPError(PageFetcherError):
    """Raised when the server responds with an HTTP error status code.

    Attributes:
        status_code: The HTTP response status code (e.g. 404, 500).
        response_text: First 500 characters of the response body, for
                       diagnostics.  Never contains full page content.
    """

    def __init__(
        self,
        message: str,
        url: str = "",
        original: Exception | None = None,
        status_code: int = 0,
        response_text: str = "",
    ) -> None:
        super().__init__(message, url=url, original=original)
        self.status_code = status_code
        self.response_text = response_text
