"""crawl_service — website source crawling (Phase 27).

Reuses the existing crawler (`scripts/crawl.py::crawl_site`) completely
unmodified apart from the one additive `on_result` callback parameter.
Runs in a background daemon thread, mirroring
`ChatOrchestrator._trigger_background_learning`'s exact pattern — this
codebase has no task queue, and a multi-page Playwright crawl is too slow
for a synchronous request/response cycle.

Include/exclude path filtering happens here, in the callback — NOT inside
`crawl_site` — so the crawler itself stays untouched beyond the one new
parameter.
"""

from __future__ import annotations

import asyncio
import logging
import threading

from scripts.crawl import crawl_site

from ...shared.logging import get_logger
from .crawl_job_repository import CrawlJobRepository
from .crawl_log_repository import CrawlLogRepository
from .document_repository import DocumentRepository
from .ingestion_service import ingest_document
from .km_models import CrawlJob
from .source_repository import SourceRepository

logger: logging.Logger = get_logger(__name__)


def _path_matches(url: str, patterns: list[str]) -> bool:
    return any(pattern in url for pattern in patterns)


class CrawlService:
    def __init__(
        self,
        source_repository: SourceRepository | None = None,
        crawl_job_repository: CrawlJobRepository | None = None,
        crawl_log_repository: CrawlLogRepository | None = None,
        document_repository: DocumentRepository | None = None,
    ) -> None:
        self._sources = source_repository or SourceRepository()
        self._jobs = crawl_job_repository or CrawlJobRepository()
        self._logs = crawl_log_repository or CrawlLogRepository()
        self._documents = document_repository or DocumentRepository()

    def start_crawl(self, source_id: str) -> CrawlJob:
        source = self._sources.get(source_id)
        if source is None:
            raise ValueError(f"Unknown source: {source_id}")
        if source.source_type != "website":
            raise ValueError("Only website sources can be crawled")

        job = self._jobs.create(source.workspace_id, source_id)
        self._sources.set_status(source_id, "processing")

        thread = threading.Thread(target=self._run_crawl, args=(job.id, source), daemon=True, name="km-crawl")
        thread.start()
        logger.info("CrawlService: started background crawl job %s for source %s", job.id, source_id)
        return job

    def _run_crawl(self, job_id: str, source) -> None:
        self._jobs.set_running(job_id)
        config = source.config or {}
        url = config.get("url")
        max_depth = config.get("max_depth", 2)
        include_paths = config.get("include_paths") or []
        exclude_paths = config.get("exclude_paths") or []

        counters = {"discovered": 0, "ingested": 0}

        def on_result(result: dict) -> None:
            counters["discovered"] += 1
            page_url = result.get("url", "")
            try:
                if include_paths and not _path_matches(page_url, include_paths):
                    self._logs.log(job_id, page_url, "failed", "excluded by include_paths")
                    return
                if exclude_paths and _path_matches(page_url, exclude_paths):
                    self._logs.log(job_id, page_url, "failed", "excluded by exclude_paths")
                    return

                markdown = result.get("markdown") or ""
                if not markdown.strip():
                    self._logs.log(job_id, page_url, "failed", "empty content")
                    return

                self._logs.log(job_id, page_url, "fetched")
                document = self._documents.create(source.workspace_id, source.id, parent_url=page_url, title=page_url)
                ingest_document(
                    workspace_id=source.workspace_id,
                    document_id=document.id,
                    raw_text=markdown,
                    parent_url=page_url,
                    product=source.product,
                    source_type="website",
                )
                self._logs.log(job_id, page_url, "embedded")
                counters["ingested"] += 1
            except Exception as exc:  # noqa: BLE001 — callback runs inside the crawler's loop, must never propagate
                logger.warning("CrawlService: failed to ingest %s — %s", page_url, exc)
                self._logs.log(job_id, page_url, "failed", str(exc))
            finally:
                self._jobs.update_counters(job_id, counters["discovered"], counters["ingested"])

        try:
            asyncio.run(crawl_site(url, max_depth, on_result=on_result))
            self._jobs.complete(job_id)
            self._sources.mark_crawled(source.id)
            self._sources.mark_indexed(source.id)
            self._sources.set_status(source.id, "ready")
        except Exception as exc:
            logger.warning("CrawlService: crawl job %s failed — %s", job_id, exc)
            self._jobs.fail(job_id, str(exc))
            self._sources.set_status(source.id, "failed")
