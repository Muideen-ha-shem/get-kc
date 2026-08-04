"""Tests for ingestion_service.ingest_document (Phase 27) — the shared
ingestion core used by crawl/upload/faq paths."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.services.knowledge_management.ingestion_service import ingest_document


class TestIngestDocument:
    def test_happy_path_writes_chunks_with_full_metadata(self):
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.return_value.data = [{"id": 1}]
        document_repo = MagicMock()
        version_repo = MagicMock()

        with patch(
            "src.services.knowledge_management.ingestion_service.split_into_semantic_chunks",
            return_value=["chunk one", "chunk two"],
        ), patch(
            "src.services.knowledge_management.ingestion_service.embed_document", return_value=[0.1] * 768
        ), patch(
            "src.services.knowledge_management.ingestion_service.intensive_clean_markdown", side_effect=lambda t: t
        ):
            ingest_document(
                workspace_id="w1", document_id="d1", raw_text="raw content",
                parent_url="https://x.com/page", product="SPIDIFY", category="Docs", source_type="website",
                client=client, document_repository=document_repo, document_version_repository=version_repo,
            )

        assert client.table.return_value.insert.call_count == 2
        first_payload = client.table.return_value.insert.call_args_list[0].args[0]
        assert first_payload["workspace_id"] == "w1"
        assert first_payload["knowledge_document_id"] == "d1"
        assert first_payload["product"] == "SPIDIFY"
        assert first_payload["source_type"] == "website"

        document_repo.set_counts.assert_called_once_with("d1", 2, len("chunk one") + len("chunk two"))
        document_repo.update_status.assert_any_call("d1", "ready")
        version_repo.record_version.assert_called_once()

    def test_empty_content_marks_failed_without_embedding(self):
        client = MagicMock()
        document_repo = MagicMock()
        version_repo = MagicMock()

        with patch(
            "src.services.knowledge_management.ingestion_service.split_into_semantic_chunks", return_value=[]
        ), patch(
            "src.services.knowledge_management.ingestion_service.intensive_clean_markdown", return_value=""
        ):
            ingest_document(
                workspace_id="w1", document_id="d1", raw_text="",
                client=client, document_repository=document_repo, document_version_repository=version_repo,
            )

        document_repo.update_status.assert_any_call("d1", "failed", error_message="No content extracted")
        client.table.return_value.insert.assert_not_called()

    def test_clean_false_skips_cleaner(self):
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.return_value.data = [{"id": 1}]
        document_repo = MagicMock()
        version_repo = MagicMock()

        with patch(
            "src.services.knowledge_management.ingestion_service.split_into_semantic_chunks", return_value=["a"]
        ) as mock_split, patch(
            "src.services.knowledge_management.ingestion_service.embed_document", return_value=[0.1]
        ), patch(
            "src.services.knowledge_management.ingestion_service.intensive_clean_markdown"
        ) as mock_clean:
            ingest_document(
                workspace_id="w1", document_id="d1", raw_text="plain text", clean=False,
                client=client, document_repository=document_repo, document_version_repository=version_repo,
            )

        mock_clean.assert_not_called()
        mock_split.assert_called_once_with("plain text")

    def test_embedding_failure_marks_document_failed_not_raised(self):
        client = MagicMock()
        document_repo = MagicMock()
        version_repo = MagicMock()

        with patch(
            "src.services.knowledge_management.ingestion_service.split_into_semantic_chunks", return_value=["a"]
        ), patch(
            "src.services.knowledge_management.ingestion_service.intensive_clean_markdown", side_effect=lambda t: t
        ), patch(
            "src.services.knowledge_management.ingestion_service.embed_document",
            side_effect=RuntimeError("embedding API down"),
        ):
            ingest_document(
                workspace_id="w1", document_id="d1", raw_text="text",
                client=client, document_repository=document_repo, document_version_repository=version_repo,
            )

        document_repo.update_status.assert_any_call("d1", "failed", error_message="embedding API down")
