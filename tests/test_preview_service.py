"""Tests for PreviewService (Phase 27)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.services.knowledge_management.preview_service import PreviewService


class TestPreviewService:
    def test_get_document_preview_returns_chunks_and_metadata(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": 1, "chunk_content": "chunk a", "product": "SPIDIFY", "category": None, "source_type": "website"}
        ]
        documents = MagicMock()
        documents.get.return_value = MagicMock(
            id="d1", parent_url="https://x.com", title="Page", char_count=100, status="ready"
        )
        service = PreviewService(client=client, document_repository=documents)

        preview = service.get_document_preview("d1")

        assert preview["chunk_count"] == 1
        assert preview["chunks"][0]["chunk_content"] == "chunk a"
        assert preview["embedding_status"] == "ready"
        assert preview["metadata"]["parent_url"] == "https://x.com"

    def test_unknown_document_raises(self):
        documents = MagicMock()
        documents.get.return_value = None
        service = PreviewService(document_repository=documents)

        with pytest.raises(ValueError, match="Unknown document"):
            service.get_document_preview("missing")
