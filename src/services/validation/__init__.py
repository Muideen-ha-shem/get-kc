"""Validation sub-package — post-generation citation cleanup.

Current members:
    CitationValidator  — removes duplicate and placeholder-URL citations
                          from ResponseGenerator's output.
"""

from .citation_validator import CitationValidator

__all__ = [
    "CitationValidator",
]
