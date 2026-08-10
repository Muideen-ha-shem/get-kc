"""Tests for TestingService (Phase 27) — confirms it calls the real,
unmodified KnowledgeService.retrieve_context, no new retrieval logic."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.services.knowledge_management.testing_service import TestingService


class TestTestingService:
    def test_calls_existing_knowledge_service_retrieve_context(self):
        knowledge_service = MagicMock()
        knowledge_service.retrieve_context.return_value = (
            [{"chunk_content": "SPIDIFY verifies identity.", "similarity": 0.87, "parent_url": "https://x.com", "product": "SPIDIFY"}],
            [0.87],
            ["https://x.com"],
        )
        service = TestingService(knowledge_service=knowledge_service)

        result = service.test_question("How does identity verification work?", "w1", ["SPIDIFY"])

        knowledge_service.retrieve_context.assert_called_once_with(
            "How does identity verification work?", product_filter=["SPIDIFY"], workspace_id="w1"
        )
        assert result["confidence"] == 0.87
        assert result["chunks"][0]["content"] == "SPIDIFY verifies identity."
        assert result["sources"] == ["https://x.com"]

    def test_no_matches_gives_zero_confidence(self):
        knowledge_service = MagicMock()
        knowledge_service.retrieve_context.return_value = ([], [], [])
        service = TestingService(knowledge_service=knowledge_service)

        result = service.test_question("anything", "w1")

        assert result["confidence"] == 0.0
        assert result["chunks"] == []
