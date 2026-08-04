"""Tests for SourceService (Phase 27) — CRUD, pause/resume, product
validation, archive deletes chunks."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.services.knowledge_management.km_models import KnowledgeDocument, KnowledgeSource
from src.services.knowledge_management.source_service import SourceService


def _source(**overrides) -> KnowledgeSource:
    base = {
        "id": "s1", "workspace_id": "w1", "source_type": "website", "name": "Docs site",
        "status": "pending", "collection_id": None, "config": {"url": "https://x.com"},
        "product": None, "schedule": "manual", "last_crawled_at": None, "last_indexed_at": None,
        "created_at": None, "updated_at": None, "archived_at": None,
    }
    base.update(overrides)
    return KnowledgeSource(**base)


class TestSourceServiceCreate:
    def test_rejects_unknown_source_type(self):
        repo = MagicMock()
        service = SourceService(repository=repo)

        with pytest.raises(ValueError, match="Unknown source_type"):
            service.create("w1", "notion", "Notion docs")

        repo.create.assert_not_called()

    def test_rejects_unknown_product(self):
        repo = MagicMock()
        service = SourceService(repository=repo)

        with pytest.raises(ValueError, match="Unknown product_id"):
            service.create("w1", "website", "Docs", product="NotAProduct")

        repo.create.assert_not_called()

    def test_accepts_known_source_type_and_product(self):
        repo = MagicMock()
        repo.create.return_value = _source(product="SPIDIFY")
        service = SourceService(repository=repo)

        source = service.create("w1", "website", "Docs", product="SPIDIFY")

        assert source.product == "SPIDIFY"


class TestSourceServicePauseResume:
    def test_pause_sets_paused_status(self):
        repo = MagicMock()
        service = SourceService(repository=repo)

        service.pause("s1")

        repo.set_status.assert_called_once_with("s1", "paused")

    def test_resume_sets_pending_status(self):
        repo = MagicMock()
        service = SourceService(repository=repo)

        service.resume("s1")

        repo.set_status.assert_called_once_with("s1", "pending")


class TestSourceServiceArchive:
    def test_archive_deletes_chunks_and_archives_documents(self):
        repo = MagicMock()
        repo.archive.return_value = _source(status="archived")
        document_repo = MagicMock()
        document_repo.list_for_source.return_value = [
            KnowledgeDocument(id="d1", workspace_id="w1", source_id="s1", status="ready"),
            KnowledgeDocument(id="d2", workspace_id="w1", source_id="s1", status="ready"),
        ]
        client = MagicMock()
        service = SourceService(repository=repo, document_repository=document_repo, client=client)

        result = service.archive("s1")

        assert result.status == "archived"
        client.table.return_value.delete.return_value.in_.assert_called_once_with(
            "knowledge_document_id", ["d1", "d2"]
        )
        assert document_repo.archive.call_count == 2
        repo.archive.assert_called_once_with("s1")

    def test_archive_with_no_documents_skips_chunk_delete(self):
        repo = MagicMock()
        repo.archive.return_value = _source(status="archived")
        document_repo = MagicMock()
        document_repo.list_for_source.return_value = []
        client = MagicMock()
        service = SourceService(repository=repo, document_repository=document_repo, client=client)

        service.archive("s1")

        client.table.return_value.delete.assert_not_called()
