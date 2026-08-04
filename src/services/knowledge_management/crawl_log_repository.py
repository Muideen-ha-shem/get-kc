"""CrawlLogRepository — raw persistence for `crawl_logs` (Phase 27).
Observability only — not a source of truth."""

from __future__ import annotations

from supabase import Client

from ...sb import get_client
from .km_models import CrawlLog

_TABLE = "crawl_logs"


class CrawlLogRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def log(self, crawl_job_id: str, url: str, status: str, message: str | None = None) -> CrawlLog:
        payload = {"crawl_job_id": crawl_job_id, "url": url, "status": status, "message": message}
        response = self._client.table(_TABLE).insert(payload).execute()
        return CrawlLog.from_row(response.data[0])

    def list_for_job(self, crawl_job_id: str) -> list[CrawlLog]:
        response = (
            self._client.table(_TABLE)
            .select("*")
            .eq("crawl_job_id", crawl_job_id)
            .order("created_at")
            .execute()
        )
        return [CrawlLog.from_row(row) for row in response.data]
