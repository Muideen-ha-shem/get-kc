"""Routing sub-package — decides which knowledge sources to query.

Current members:
    SourceRouter   — routes a user question to one or more knowledge sources
                     (knowledge base vs. live web).
    ProductRouter  — classifies a question against named products (e.g.
                     SPIDIFY, ZivaAIRA) to scope knowledge-base retrieval.
"""

from .source_router import SourceRouter, RoutingDecision
from .product_router import ProductRouter, ProductMatch

__all__ = [
    "SourceRouter",
    "RoutingDecision",
    "ProductRouter",
    "ProductMatch",
]
