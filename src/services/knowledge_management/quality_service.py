"""quality_service (Phase 27) — knowledge-quality diagnostics.

Six checks, each a fresh query against already-persisted tables — no
second pipeline, no caching.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from supabase import Client

from ...sb import get_client
from .km_models import QualityReport
from .quality_report_repository import QualityReportRepository

_LARGE_CHUNK_THRESHOLD = 1200  # 2x the chunker's normal max_chunk_size=600


class QualityService:
    def __init__(
        self, client: Client | None = None, repository: QualityReportRepository | None = None
    ) -> None:
        self._client = client or get_client()
        self._repo = repository or QualityReportRepository()

    def run_quality_scan(self, workspace_id: str) -> QualityReport:
        chunks_response = (
            self._client.table("documentation_chunks")
            .select("id,chunk_content,product,category,parent_url")
            .eq("workspace_id", workspace_id)
            .execute()
        )
        chunks: list[dict[str, Any]] = chunks_response.data or []

        content_counts = Counter(c["chunk_content"] for c in chunks)
        duplicate_chunk_count = sum(count - 1 for count in content_counts.values() if count > 1)
        large_chunk_count = sum(1 for c in chunks if len(c.get("chunk_content") or "") > _LARGE_CHUNK_THRESHOLD)
        missing_metadata_count = sum(1 for c in chunks if not c.get("product") and not c.get("category"))

        documents_response = (
            self._client.table("knowledge_documents")
            .select("id,chunk_count,parent_url")
            .eq("workspace_id", workspace_id)
            .is_("archived_at", "null")
            .execute()
        )
        documents: list[dict[str, Any]] = documents_response.data or []
        empty_document_count = sum(1 for d in documents if (d.get("chunk_count") or 0) == 0)

        failed_docs_response = (
            self._client.table("knowledge_documents")
            .select("id", count="exact")
            .eq("workspace_id", workspace_id)
            .eq("status", "failed")
            .execute()
        )
        embedding_failure_count = failed_docs_response.count or 0

        sources_response = (
            self._client.table("knowledge_sources")
            .select("id", count="exact")
            .eq("workspace_id", workspace_id)
            .eq("status", "failed")
            .execute()
        )
        broken_url_count = sources_response.count or 0

        report = self._repo.create(
            workspace_id=workspace_id,
            duplicate_chunk_count=duplicate_chunk_count,
            broken_url_count=broken_url_count,
            empty_document_count=empty_document_count,
            embedding_failure_count=embedding_failure_count,
            large_chunk_count=large_chunk_count,
            missing_metadata_count=missing_metadata_count,
            details={"total_chunks_scanned": len(chunks), "total_documents_scanned": len(documents)},
        )
        return report

    def latest_report(self, workspace_id: str) -> QualityReport | None:
        return self._repo.latest_for_workspace(workspace_id)
