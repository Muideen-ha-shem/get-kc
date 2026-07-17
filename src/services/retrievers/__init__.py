"""Retrievers sub-package — services that fetch raw remote content.

Current members:
    PageFetcher  — downloads raw HTML from a URL without parsing it.
"""

from .exceptions import (
    FetchConnectionError,
    FetchHTTPError,
    FetchTimeoutError,
    InvalidURLError,
    PageFetcherError,
)
from .page_fetcher import PageFetcher

__all__ = [
    "PageFetcher",
    # Exceptions — exported so callers can import from one place
    "PageFetcherError",
    "InvalidURLError",
    "FetchTimeoutError",
    "FetchConnectionError",
    "FetchHTTPError",
]
