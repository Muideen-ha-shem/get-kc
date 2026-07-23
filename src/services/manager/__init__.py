"""Manager sub-package — orchestrates multi-source retrieval.

Current members:
    SearchManager  — receives a routing decision and coordinates the
                     appropriate retrievers, returning unified evidence.
"""

from .search_manager import SearchManager

__all__ = [
    "SearchManager",
]