"""faq_service — structured FAQ authoring (Phase 27).

Each FAQ becomes searchable through the existing RAG system by going
through the exact same `ingestion_service.ingest_document` core as
crawled pages and uploads — no separate FAQ search path.
"""

from __future__ import annotations

from .document_repository import DocumentRepository
from .ingestion_service import ingest_document
from .km_models import KnowledgeDocument
from .source_repository import SourceRepository


class FaqService:
    def __init__(
        self,
        source_repository: SourceRepository | None = None,
        document_repository: DocumentRepository | None = None,
    ) -> None:
        self._sources = source_repository or SourceRepository()
        self._documents = document_repository or DocumentRepository()

    def create_faq(
        self,
        workspace_id: str,
        question: str,
        answer: str,
        collection_id: str | None = None,
        product: str | None = None,
        category: str | None = None,
    ) -> KnowledgeDocument:
        source = self._sources.create(
            workspace_id, "faq", name=question[:80], collection_id=collection_id,
            config=None, product=product, schedule="manual",
        )
        document = self._documents.create(workspace_id, source.id, parent_url=None, title=question[:200])

        ingest_document(
            workspace_id=workspace_id,
            document_id=document.id,
            raw_text=f"Q: {question}\nA: {answer}",
            parent_url=None,
            product=product,
            category=category,
            source_type="faq",
            clean=False,
        )
        self._sources.set_status(source.id, "ready")
        return self._documents.get(document.id)
