"""Routing sub-package — decides which knowledge sources to query.

Current members:
    SourceRouter  — routes a user question to one or more knowledge sources.
"""

from .source_router import SourceRouter, RoutingDecision

__all__ = [
    "SourceRouter",
    "RoutingDecision",
]