"""Business services package for the AI support platform."""

from .documents.document_service import DocumentService
from .knowledge.knowledge_service import KnowledgeService
from .support.support_service import SupportService
from .search.search_service import SearchService
from .retrievers.page_fetcher import PageFetcher
from .retrievers.exceptions import (
    PageFetcherError,
    InvalidURLError,
    FetchTimeoutError,
    FetchConnectionError,
    FetchHTTPError,
)

__all__ = [
    "DocumentService",
    "KnowledgeService",
    "SupportService",
    "SearchService",
    "PageFetcher",
    "PageFetcherError",
    "InvalidURLError",
    "FetchTimeoutError",
    "FetchConnectionError",
    "FetchHTTPError",
]
