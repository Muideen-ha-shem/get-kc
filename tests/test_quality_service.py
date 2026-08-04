"""Tests for QualityService.run_quality_scan (Phase 27) — each of the six
diagnostics independently, via one combined scan (routing client.table()
calls by table name)."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.services.knowledge_management.quality_service import QualityService


class TestRunQualityScan:
    def test_all_six_diagnostics_computed_correctly(self):
        chunks = [
            {"id": 1, "chunk_content": "duplicate text", "product": None, "category": None, "parent_url": "u1"},
            {"id": 2, "chunk_content": "duplicate text", "product": None, "category": None, "parent_url": "u1"},
            {"id": 3, "chunk_content": "x" * 1300, "product": "SPIDIFY", "category": "Docs", "parent_url": "u2"},
        ]
        documents = [{"id": "d1", "chunk_count": 0, "parent_url": "u1"}, {"id": "d2", "chunk_count": 3, "parent_url": "u2"}]

        chunks_table = MagicMock()
        chunks_table.select.return_value.eq.return_value.execute.return_value.data = chunks

        documents_table = MagicMock()
        documents_table.select.return_value.eq.return_value.is_.return_value.execute.return_value.data = documents
        documents_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(count=1)

        sources_table = MagicMock()
        sources_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(count=2)

        client = MagicMock()
        tables = {
            "documentation_chunks": chunks_table,
            "knowledge_documents": documents_table,
            "knowledge_sources": sources_table,
        }
        client.table.side_effect = lambda name: tables[name]

        repo = MagicMock()
        repo.create.return_value = MagicMock()
        service = QualityService(client=client, repository=repo)

        service.run_quality_scan("w1")

        kwargs = repo.create.call_args.kwargs
        assert kwargs["duplicate_chunk_count"] == 1
        assert kwargs["large_chunk_count"] == 1
        assert kwargs["missing_metadata_count"] == 2
        assert kwargs["empty_document_count"] == 1
        assert kwargs["embedding_failure_count"] == 1
        assert kwargs["broken_url_count"] == 2

    def test_latest_report_delegates_to_repository(self):
        repo = MagicMock()
        service = QualityService(repository=repo)

        service.latest_report("w1")

        repo.latest_for_workspace.assert_called_once_with("w1")
