"""Query sub-package — pre-processing user questions before retrieval.

Current members:
    QueryRewriter  — deterministic rewriting of a natural-language question
                     into a concise, search-engine-friendly query.
"""

from .query_rewriter import QueryRewriter

__all__ = [
    "QueryRewriter",
]
