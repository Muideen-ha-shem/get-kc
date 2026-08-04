"""CrawlJobRepository — raw persistence for `crawl_jobs` (Phase 27)."""

from __future__ import annotations

from datetime import datetime, timezone

from supabase import Client

from ...sb import get_client
from .km_models import CrawlJob

_TABLE = "crawl_jobs"


class CrawlJobRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def create(self, workspace_id: str, source_id: str) -> CrawlJob:
        payload = {"workspace_id": workspace_id, "source_id": source_id}
        response = self._client.table(_TABLE).insert(payload).execute()
        return CrawlJob.from_row(response.data[0])

    def get(self, job_id: str) -> CrawlJob | None:
        response = self._client.table(_TABLE).select("*").eq("id", job_id).limit(1).execute()
        if not response.data:
            return None
        return CrawlJob.from_row(response.data[0])

    def list_for_source(self, source_id: str) -> list[CrawlJob]:
        response = (
            self._client.table(_TABLE).select("*").eq("source_id", source_id).order("created_at", desc=True).execute()
        )
        return [CrawlJob.from_row(row) for row in response.data]

    def set_running(self, job_id: str) -> None:
        self._client.table(_TABLE).update(
            {"status": "running", "started_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", job_id).execute()

    def update_counters(self, job_id: str, pages_discovered: int, pages_ingested: int) -> None:
        self._client.table(_TABLE).update(
            {"pages_discovered": pages_discovered, "pages_ingested": pages_ingested}
        ).eq("id", job_id).execute()

    def complete(self, job_id: str) -> None:
        self._client.table(_TABLE).update(
            {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", job_id).execute()

    def fail(self, job_id: str, error_message: str) -> None:
        self._client.table(_TABLE).update(
            {"status": "failed", "error_message": error_message, "completed_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", job_id).execute()
