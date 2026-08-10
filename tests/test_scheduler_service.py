"""Tests for SchedulerService.due_sources — pure query correctness
(Phase 27). No timer/cron calls this — config-only this phase."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from src.services.knowledge_management.km_models import KnowledgeSource
from src.services.knowledge_management.scheduler_service import SchedulerService


def _source(**overrides) -> KnowledgeSource:
    base = {
        "id": "s1", "workspace_id": "w1", "source_type": "website", "name": "Docs",
        "status": "ready", "collection_id": None, "config": {}, "product": None,
        "schedule": "daily", "last_crawled_at": None, "last_indexed_at": None,
        "created_at": None, "updated_at": None, "archived_at": None,
    }
    base.update(overrides)
    return KnowledgeSource(**base)


class TestDueSources:
    def test_manual_schedule_never_due(self):
        sources = MagicMock()
        sources.list_for_workspace.return_value = [_source(schedule="manual")]
        service = SchedulerService(source_repository=sources)

        assert service.due_sources("w1") == []

    def test_paused_source_never_due(self):
        sources = MagicMock()
        sources.list_for_workspace.return_value = [_source(status="paused")]
        service = SchedulerService(source_repository=sources)

        assert service.due_sources("w1") == []

    def test_never_crawled_source_is_due(self):
        sources = MagicMock()
        sources.list_for_workspace.return_value = [_source(last_crawled_at=None)]
        service = SchedulerService(source_repository=sources)

        assert len(service.due_sources("w1")) == 1

    def test_daily_source_due_after_interval_elapsed(self):
        two_days_ago = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        sources = MagicMock()
        sources.list_for_workspace.return_value = [_source(schedule="daily", last_crawled_at=two_days_ago)]
        service = SchedulerService(source_repository=sources)

        assert len(service.due_sources("w1")) == 1

    def test_daily_source_not_due_within_interval(self):
        one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        sources = MagicMock()
        sources.list_for_workspace.return_value = [_source(schedule="daily", last_crawled_at=one_hour_ago)]
        service = SchedulerService(source_repository=sources)

        assert service.due_sources("w1") == []

    def test_non_website_source_never_due(self):
        sources = MagicMock()
        sources.list_for_workspace.return_value = [_source(source_type="faq", schedule="daily", last_crawled_at=None)]
        service = SchedulerService(source_repository=sources)

        assert service.due_sources("w1") == []


class TestTriggerRecrawl:
    def test_delegates_to_crawl_service(self):
        crawl_service = MagicMock()
        service = SchedulerService(crawl_service=crawl_service)

        service.trigger_recrawl("s1")

        crawl_service.start_crawl.assert_called_once_with("s1")
