"""preview_service (Phase 27) — read-only inspection of a document's
extracted content, generated chunks, metadata, and embedding status."""

from __future__ import annotations

from typing import Any

from supabase import Client

from ...sb import get_client
from .document_repository import DocumentRepository


class PreviewService:
    def __init__(self, client: Client | None = None, document_repository: DocumentRepository | None = None) -> None:
        self._client = client or get_client()
        self._documents = document_repository or DocumentRepository()

    def get_document_preview(self, document_id: str) -> dict[str, Any]:
        document = self._documents.get(document_id)
        if document is None:
            raise ValueError(f"Unknown document: {document_id}")

        response = (
            self._client.table("documentation_chunks")
            .select("id,chunk_content,product,category,source_type")
            .eq("knowledge_document_id", document_id)
            .execute()
        )
        chunks = response.data or []

        return {
            "document": document,
            "chunk_count": len(chunks),
            "chunks": chunks,
            "embedding_status": document.status,
            "metadata": {
                "parent_url": document.parent_url,
                "title": document.title,
                "char_count": document.char_count,
            },
        }
