"""SourceService — CRUD + lifecycle over knowledge_sources (Phase 27).

`product` is validated against PRODUCT_REGISTRY.keys() — read-only import,
reuses Phase 26's ProductService validation pattern exactly. PRODUCT_REGISTRY
itself is never modified.
"""

from __future__ import annotations

from typing import Any

from supabase import Client

from ...sb import get_client
from ...shared.product_registry import PRODUCT_REGISTRY
from .document_repository import DocumentRepository
from .km_models import KnowledgeSource
from .source_repository import SourceRepository

SUPPORTED_SOURCE_TYPES: set[str] = {"website", "pdf", "docx", "pptx", "markdown", "txt", "faq"}


class SourceService:
    def __init__(
        self,
        repository: SourceRepository | None = None,
        document_repository: DocumentRepository | None = None,
        client: Client | None = None,
    ) -> None:
        self._repo = repository or SourceRepository()
        self._documents = document_repository or DocumentRepository()
        self._client = client or get_client()

    def list_for_workspace(self, workspace_id: str, include_archived: bool = False) -> list[KnowledgeSource]:
        return self._repo.list_for_workspace(workspace_id, include_archived=include_archived)

    def get(self, source_id: str) -> KnowledgeSource | None:
        return self._repo.get(source_id)

    def create(
        self,
        workspace_id: str,
        source_type: str,
        name: str,
        collection_id: str | None = None,
        config: dict[str, Any] | None = None,
        product: str | None = None,
        schedule: str = "manual",
    ) -> KnowledgeSource:
        if source_type not in SUPPORTED_SOURCE_TYPES:
            raise ValueError(f"Unknown source_type: {source_type}")
        if product is not None and product not in PRODUCT_REGISTRY:
            raise ValueError(f"Unknown product_id: {product}")
        return self._repo.create(workspace_id, source_type, name, collection_id, config, product, schedule)

    def update(self, source_id: str, **fields: Any) -> KnowledgeSource:
        return self._repo.update(source_id, **fields)

    def pause(self, source_id: str) -> KnowledgeSource:
        """Stops future (re)crawls/scheduling for this source. Existing
        chunks stay searchable — pausing is not archiving."""
        return self._repo.set_status(source_id, "paused")

    def resume(self, source_id: str) -> KnowledgeSource:
        """Un-pauses — the source becomes eligible for crawling/scheduling
        again. Uses 'pending' (not 'ready') since resuming doesn't itself
        mean content is freshly indexed; the next crawl/upload does."""
        return self._repo.set_status(source_id, "pending")

    def archive(self, source_id: str) -> KnowledgeSource:
        """Archiving removes the source's chunks from search — deletes the
        matching documentation_chunks rows (via knowledge_document_id) —
        while keeping the knowledge_sources/knowledge_documents rows for
        history. No retrieval RPC changes needed (see the plan's locked
        decision)."""
        documents = self._documents.list_for_source(source_id)
        document_ids = [d.id for d in documents]
        if document_ids:
            self._client.table("documentation_chunks").delete().in_(
                "knowledge_document_id", document_ids
            ).execute()
        for document in documents:
            self._documents.archive(document.id)
        return self._repo.archive(source_id)
