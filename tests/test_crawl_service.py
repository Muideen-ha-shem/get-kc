"""Tests for CrawlService (Phase 27) — mocked crawl_site, include/exclude
filtering, crawl_jobs/crawl_logs written."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.services.knowledge_management.crawl_service import CrawlService
from src.services.knowledge_management.km_models import CrawlJob, KnowledgeSource


def _source(**overrides) -> KnowledgeSource:
    base = {
        "id": "s1", "workspace_id": "w1", "source_type": "website", "name": "Docs",
        "status": "pending", "collection_id": None,
        "config": {"url": "https://x.com", "max_depth": 1}, "product": None, "schedule": "manual",
        "last_crawled_at": None, "last_indexed_at": None, "created_at": None, "updated_at": None, "archived_at": None,
    }
    base.update(overrides)
    return KnowledgeSource(**base)


class TestStartCrawl:
    def test_rejects_non_website_source(self):
        sources = MagicMock()
        sources.get.return_value = _source(source_type="pdf")
        service = CrawlService(source_repository=sources)

        with pytest.raises(ValueError, match="Only website sources"):
            service.start_crawl("s1")

    def test_unknown_source_raises(self):
        sources = MagicMock()
        sources.get.return_value = None
        service = CrawlService(source_repository=sources)

        with pytest.raises(ValueError, match="Unknown source"):
            service.start_crawl("s1")

    def test_creates_job_and_starts_background_thread(self):
        sources = MagicMock()
        sources.get.return_value = _source()
        jobs = MagicMock()
        jobs.create.return_value = CrawlJob(id="j1", workspace_id="w1", source_id="s1", status="pending")
        service = CrawlService(source_repository=sources, crawl_job_repository=jobs)

        with patch("threading.Thread") as mock_thread_cls:
            mock_thread = MagicMock()
            mock_thread_cls.return_value = mock_thread

            job = service.start_crawl("s1")

        assert job.id == "j1"
        sources.set_status.assert_called_once_with("s1", "processing")
        mock_thread_cls.assert_called_once()
        assert mock_thread_cls.call_args.kwargs["daemon"] is True
        mock_thread.start.assert_called_once()


class TestRunCrawlFiltering:
    def _run(self, source, crawl_results, jobs=None, logs=None, documents=None, sources=None):
        jobs = jobs or MagicMock()
        logs = logs or MagicMock()
        documents = documents or MagicMock()
        sources = sources or MagicMock()
        documents.create.return_value = MagicMock(id="d1")
        service = CrawlService(
            source_repository=sources, crawl_job_repository=jobs, crawl_log_repository=logs,
            document_repository=documents,
        )

        async def fake_crawl_site(url, max_depth, on_result=None):
            for result in crawl_results:
                on_result(result)

        with patch("src.services.knowledge_management.crawl_service.crawl_site", side_effect=fake_crawl_site), \
             patch("src.services.knowledge_management.crawl_service.ingest_document") as mock_ingest:
            service._run_crawl("j1", source)

        return jobs, logs, documents, mock_ingest

    def test_excludes_pages_not_matching_include_paths(self):
        source = _source(config={"url": "https://x.com", "include_paths": ["/docs/"]})
        results = [{"url": "https://x.com/docs/page1", "markdown": "content"}, {"url": "https://x.com/blog/post", "markdown": "content"}]

        jobs, logs, documents, mock_ingest = self._run(source, results)

        assert documents.create.call_count == 1
        assert mock_ingest.call_count == 1

    def test_excludes_pages_matching_exclude_paths(self):
        source = _source(config={"url": "https://x.com", "exclude_paths": ["/blog/"]})
        results = [{"url": "https://x.com/docs/page1", "markdown": "content"}, {"url": "https://x.com/blog/post", "markdown": "content"}]

        jobs, logs, documents, mock_ingest = self._run(source, results)

        assert documents.create.call_count == 1

    def test_empty_markdown_page_skipped(self):
        source = _source()
        results = [{"url": "https://x.com/empty", "markdown": "   "}]

        jobs, logs, documents, mock_ingest = self._run(source, results)

        documents.create.assert_not_called()
        mock_ingest.assert_not_called()

    def test_successful_crawl_marks_job_completed_and_source_ready(self):
        source = _source()
        results = [{"url": "https://x.com/page", "markdown": "content"}]
        jobs = MagicMock()
        sources = MagicMock()
        documents = MagicMock()
        logs = MagicMock()
        documents.create.return_value = MagicMock(id="d1")
        service = CrawlService(
            source_repository=sources, crawl_job_repository=jobs, crawl_log_repository=logs,
            document_repository=documents,
        )

        async def fake_crawl_site(url, max_depth, on_result=None):
            for result in results:
                on_result(result)

        with patch("src.services.knowledge_management.crawl_service.crawl_site", side_effect=fake_crawl_site), \
             patch("src.services.knowledge_management.crawl_service.ingest_document"):
            service._run_crawl("j1", source)

        jobs.complete.assert_called_once_with("j1")
        sources.set_status.assert_called_with("s1", "ready")

    def test_crawl_exception_marks_job_and_source_failed(self):
        source = _source()
        jobs = MagicMock()
        sources = MagicMock()
        service = CrawlService(source_repository=sources, crawl_job_repository=jobs)

        async def failing_crawl_site(url, max_depth, on_result=None):
            raise RuntimeError("network error")

        with patch("src.services.knowledge_management.crawl_service.crawl_site", side_effect=failing_crawl_site):
            service._run_crawl("j1", source)

        jobs.fail.assert_called_once()
        sources.set_status.assert_called_with("s1", "failed")
