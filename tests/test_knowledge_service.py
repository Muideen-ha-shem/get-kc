"""Tests for KnowledgeService — the product_filter pass-through."""

from __future__ import annotations

from unittest.mock import patch


class TestKnowledgeServiceRetrieveContext:
    def test_passes_question_through(self):
        from src.services.knowledge.knowledge_service import KnowledgeService

        with patch(
            "src.services.knowledge.knowledge_service.legacy_retrieve_context",
            return_value=([], [], []),
        ) as mock_retrieve:
            KnowledgeService().retrieve_context("test question")

        mock_retrieve.assert_called_once_with(
            "test question", product_filter=None, match_count=3
        )

    def test_passes_product_filter_through(self):
        from src.services.knowledge.knowledge_service import KnowledgeService

        with patch(
            "src.services.knowledge.knowledge_service.legacy_retrieve_context",
            return_value=([], [], []),
        ) as mock_retrieve:
            KnowledgeService().retrieve_context("test question", product_filter=["SPIDIFY"])

        mock_retrieve.assert_called_once_with(
            "test question", product_filter=["SPIDIFY"], match_count=3
        )

    def test_returns_underlying_result_unchanged(self):
        from src.services.knowledge.knowledge_service import KnowledgeService

        expected = ([{"chunk_content": "x"}], [0.9], ["https://example.com"])
        with patch(
            "src.services.knowledge.knowledge_service.legacy_retrieve_context",
            return_value=expected,
        ):
            result = KnowledgeService().retrieve_context("test question")

        assert result == expected
