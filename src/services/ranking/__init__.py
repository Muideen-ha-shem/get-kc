"""Ranking sub-package — intelligent multi-signal ranking of merged evidence.

Current members:
    SourceRanker  — re-scores and trims ContextMerger's merged evidence
                    using relevance, source authority, freshness, and a
                    near-duplicate penalty.
"""

from .source_ranker import SourceRanker

__all__ = [
    "SourceRanker",
]
