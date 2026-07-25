"""RAG sub-package — ephemeral retrieval over freshly fetched web pages.

Current members:
    EphemeralRAG      — ranks text chunks from live-fetched pages against a
                         question, for use by SearchManager.
    SemanticReranker  — optional embedding-based re-scoring of a lexical
                         shortlist, injectable into EphemeralRAG.
"""

from .ephemeral_rag import EphemeralRAG, ChunkResult
from .semantic_reranker import SemanticReranker

__all__ = [
    "EphemeralRAG",
    "ChunkResult",
    "SemanticReranker",
]
