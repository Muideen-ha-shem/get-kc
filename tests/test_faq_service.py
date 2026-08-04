"""Tests for FaqService (Phase 27)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.services.knowledge_management.faq_service import FaqService
from src.services.knowledge_management.km_models import KnowledgeSource


class TestFaqService:
    def test_create_faq_creates_source_and_document_then_ingests(self):
        sources = MagicMock()
        sources.create.return_value = KnowledgeSource(
            id="s1", workspace_id="w1", source_type="faq", name="What is SPIDIFY?", status="pending"
        )
        documents = MagicMock()
        documents.create.return_value = MagicMock(id="d1")
        documents.get.return_value = MagicMock(id="d1", status="ready")
        service = FaqService(source_repository=sources, document_repository=documents)

        with patch("src.services.knowledge_management.faq_service.ingest_document") as mock_ingest:
            service.create_faq("w1", "What is SPIDIFY?", "SPIDIFY verifies identity.", product="SPIDIFY")

        sources.create.assert_called_once_with(
            "w1", "faq", name="What is SPIDIFY?", collection_id=None, config=None, product="SPIDIFY", schedule="manual"
        )
        call_kwargs = mock_ingest.call_args.kwargs
        assert call_kwargs["raw_text"] == "Q: What is SPIDIFY?\nA: SPIDIFY verifies identity."
        assert call_kwargs["source_type"] == "faq"
        sources.set_status.assert_called_once_with("s1", "ready")
