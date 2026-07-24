"""RAG sub-package — ephemeral retrieval over freshly fetched web pages.

Current members:
    EphemeralRAG  — ranks text chunks from live-fetched pages against a
                    question, for use by SearchManager.
"""

from .ephemeral_rag import EphemeralRAG, ChunkResult

__all__ = [
    "EphemeralRAG",
    "ChunkResult",
]
