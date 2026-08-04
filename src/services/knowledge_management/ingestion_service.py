"""ingestion_service — the one shared ingestion core (Phase 27).

Both crawl_service and upload_service (and faq_service) call
``ingest_document`` — this is the single place chunking/embedding/writing
to `documentation_chunks` happens, satisfying "no duplicate ingestion
logic". Reuses the existing cleaner/chunker/embedder unmodified:
``intensive_clean_markdown`` (src/intensive_cleaner.py),
``split_into_semantic_chunks`` (src/chunk.py), ``embed_document``
(src/api/services/embeddings.py).
"""

from __future__ import annotations

import hashlib
import logging

from supabase import Client

from ...api.services.embeddings import embed_document
from ...chunk import split_into_semantic_chunks
from ...intensive_cleaner import intensive_clean_markdown
from ...sb import get_client
from ...shared.logging import get_logger
from .document_repository import DocumentRepository
from .document_version_repository import DocumentVersionRepository

logger: logging.Logger = get_logger(__name__)

_DOCUMENTATION_CHUNKS = "documentation_chunks"


def ingest_document(
    *,
    workspace_id: str,
    document_id: str,
    raw_text: str,
    parent_url: str | None = None,
    product: str | None = None,
    category: str | None = None,
    source_type: str | None = None,
    clean: bool = True,
    client: Client | None = None,
    document_repository: DocumentRepository | None = None,
    document_version_repository: DocumentVersionRepository | None = None,
) -> None:
    """Cleans (optionally), chunks, embeds, and writes *raw_text* into
    `documentation_chunks`, updating the `knowledge_documents` row's
    status/counts throughout. Never raises — a failure is recorded on the
    document row (`status='failed'`, `error_message`) rather than
    propagated, since this is called from a background thread (crawl) or
    a request handler that must still return a clean response (upload/FAQ).
    """
    client = client or get_client()
    document_repository = document_repository or DocumentRepository()
    document_version_repository = document_version_repository or DocumentVersionRepository()

    try:
        document_repository.update_status(document_id, "processing")
        text = intensive_clean_markdown(raw_text) if clean else raw_text
        chunks = split_into_semantic_chunks(text)

        if not chunks:
            document_repository.update_status(document_id, "failed", error_message="No content extracted")
            return

        document_repository.update_status(document_id, "embedding")
        chunk_count = 0
        char_count = 0
        for chunk in chunks:
            embedding = embed_document(chunk)
            client.table(_DOCUMENTATION_CHUNKS).insert({
                "parent_url": parent_url or "Unknown URL",
                "chunk_content": chunk,
                "embedding": embedding,
                "product": product,
                "category": category,
                "source_type": source_type,
                "workspace_id": workspace_id,
                "knowledge_document_id": document_id,
            }).execute()
            chunk_count += 1
            char_count += len(chunk)

        document_repository.set_counts(document_id, chunk_count, char_count)
        document_repository.update_status(document_id, "ready")
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        document_version_repository.record_version(document_id, content_hash, chunk_count)
    except Exception as exc:
        logger.warning("ingest_document: failed for document %s — %s", document_id, exc)
        document_repository.update_status(document_id, "failed", error_message=str(exc))
