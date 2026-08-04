"""DocumentRepository — raw persistence for `knowledge_documents` (Phase 27)."""

from __future__ import annotations

from datetime import datetime, timezone

from supabase import Client

from ...sb import get_client
from .km_models import KnowledgeDocument

_TABLE = "knowledge_documents"


class DocumentRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def create(
        self, workspace_id: str, source_id: str, parent_url: str | None = None, title: str | None = None
    ) -> KnowledgeDocument:
        payload = {"workspace_id": workspace_id, "source_id": source_id, "parent_url": parent_url, "title": title}
        response = self._client.table(_TABLE).insert(payload).execute()
        return KnowledgeDocument.from_row(response.data[0])

    def get(self, document_id: str) -> KnowledgeDocument | None:
        response = self._client.table(_TABLE).select("*").eq("id", document_id).limit(1).execute()
        if not response.data:
            return None
        return KnowledgeDocument.from_row(response.data[0])

    def list_for_source(self, source_id: str) -> list[KnowledgeDocument]:
        response = (
            self._client.table(_TABLE).select("*").eq("source_id", source_id).order("created_at", desc=True).execute()
        )
        return [KnowledgeDocument.from_row(row) for row in response.data]

    def list_for_workspace(self, workspace_id: str) -> list[KnowledgeDocument]:
        response = (
            self._client.table(_TABLE)
            .select("*")
            .eq("workspace_id", workspace_id)
            .is_("archived_at", "null")
            .execute()
        )
        return [KnowledgeDocument.from_row(row) for row in response.data]

    def update_status(self, document_id: str, status: str, error_message: str | None = None) -> KnowledgeDocument:
        payload = {
            "status": status,
            "error_message": error_message,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        response = self._client.table(_TABLE).update(payload).eq("id", document_id).execute()
        return KnowledgeDocument.from_row(response.data[0])

    def set_counts(self, document_id: str, chunk_count: int, char_count: int) -> KnowledgeDocument:
        response = (
            self._client.table(_TABLE)
            .update({"chunk_count": chunk_count, "char_count": char_count})
            .eq("id", document_id)
            .execute()
        )
        return KnowledgeDocument.from_row(response.data[0])

    def archive(self, document_id: str) -> KnowledgeDocument:
        response = (
            self._client.table(_TABLE)
            .update({"status": "archived", "archived_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", document_id)
            .execute()
        )
        return KnowledgeDocument.from_row(response.data[0])
