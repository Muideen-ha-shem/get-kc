"""scheduler_service (Phase 27) — config-only this phase.

`knowledge_sources.schedule` is stored and `trigger_recrawl` always works
manually; there is no cron/timer loop actually executing daily/weekly/
monthly crawls automatically — no scheduler infrastructure exists
anywhere in this codebase, and adding one is out of scope for "ingestion
only" (see the plan's locked decision). `due_sources` is a pure,
already-correct query — a future phase just needs to call it on a timer.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .crawl_service import CrawlService
from .km_models import CrawlJob, KnowledgeSource
from .source_repository import SourceRepository

_SCHEDULE_INTERVALS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
    "monthly": timedelta(days=30),
}


class SchedulerService:
    def __init__(
        self,
        source_repository: SourceRepository | None = None,
        crawl_service: CrawlService | None = None,
    ) -> None:
        self._sources = source_repository or SourceRepository()
        self._crawl_service = crawl_service or CrawlService()

    def due_sources(self, workspace_id: str, now: datetime | None = None) -> list[KnowledgeSource]:
        """Pure query: which website sources are due for a recrawl given
        their schedule and last_crawled_at. Not called by any timer this
        phase — see module docstring."""
        now = now or datetime.now(timezone.utc)
        due: list[KnowledgeSource] = []
        for source in self._sources.list_for_workspace(workspace_id):
            if source.source_type != "website" or source.schedule == "manual" or source.status == "paused":
                continue
            interval = _SCHEDULE_INTERVALS.get(source.schedule)
            if interval is None:
                continue
            if source.last_crawled_at is None:
                due.append(source)
                continue
            last_crawled = datetime.fromisoformat(source.last_crawled_at.replace("Z", "+00:00"))
            if now - last_crawled >= interval:
                due.append(source)
        return due

    def trigger_recrawl(self, source_id: str) -> CrawlJob:
        return self._crawl_service.start_crawl(source_id)
