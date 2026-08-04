"""DocumentVersionRepository — raw persistence for `document_versions`
(Phase 27). Extension point for future incremental crawling — one row
written per (re)ingest, no diffing logic implemented yet."""

from __future__ import annotations

from supabase import Client

from ...sb import get_client
from .km_models import DocumentVersion

_TABLE = "document_versions"


class DocumentVersionRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def latest_version_number(self, document_id: str) -> int:
        response = (
            self._client.table(_TABLE)
            .select("version_number")
            .eq("document_id", document_id)
            .order("version_number", desc=True)
            .limit(1)
            .execute()
        )
        if not response.data:
            return 0
        return response.data[0]["version_number"]

    def record_version(self, document_id: str, content_hash: str | None, chunk_count: int) -> DocumentVersion:
        next_version = self.latest_version_number(document_id) + 1
        payload = {
            "document_id": document_id, "version_number": next_version,
            "content_hash": content_hash, "chunk_count": chunk_count,
        }
        response = self._client.table(_TABLE).insert(payload).execute()
        return DocumentVersion.from_row(response.data[0])

    def list_for_document(self, document_id: str) -> list[DocumentVersion]:
        response = (
            self._client.table(_TABLE)
            .select("*")
            .eq("document_id", document_id)
            .order("version_number", desc=True)
            .execute()
        )
        return [DocumentVersion.from_row(row) for row in response.data]
