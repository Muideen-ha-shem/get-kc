"""Merger sub-package — combines evidence from multiple retrievers.

Current members:
    EvidenceItem   — a single piece of evidence from any retriever.
    ContextMerger  — deduplicates, ranks, and merges evidence into a
                     unified context for the language model.
"""

from .context_merger import ContextMerger, EvidenceItem

__all__ = [
    "ContextMerger",
    "EvidenceItem",
]