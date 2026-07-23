from __future__ import annotations

from typing import Any

from ...chunk import split_into_semantic_chunks
from ...infrastructure.database.supabase import get_client
from ...api.services.embeddings import embed_document


class DocumentService:
    """Coordinates the document ingestion pipeline from raw text to embeddings."""

    def ingest_text(self, text: str, parent_url: str = "Unknown URL") -> list[dict[str, Any]]:
        chunks = split_into_semantic_chunks(text)
        sb_client = get_client()
        inserted: list[dict[str, Any]] = []

        for chunk in chunks:
            embedding = embed_document(chunk)
            payload = {
                "parent_url": parent_url,
                "chunk_content": chunk,
                "embedding": embedding,
            }
            response = sb_client.table("documentation_chunks").insert(payload).execute()
            inserted.append({"chunk": chunk, "response": response})

        return inserted
