"""Tests for UploadService/extract_text (Phase 27) — mocked parsers per
file type, confirms original bytes are never persisted."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.services.knowledge_management.km_models import KnowledgeSource
from src.services.knowledge_management.upload_service import UploadService, extract_text


def _source(**overrides) -> KnowledgeSource:
    base = {
        "id": "s1", "workspace_id": "w1", "source_type": "pdf", "name": "Handbook",
        "status": "pending", "collection_id": None, "config": None, "product": None,
        "schedule": "manual", "last_crawled_at": None, "last_indexed_at": None,
        "created_at": None, "updated_at": None, "archived_at": None,
    }
    base.update(overrides)
    return KnowledgeSource(**base)


class TestExtractText:
    def test_txt_decodes_directly(self):
        assert extract_text("notes.txt", b"hello world") == "hello world"

    def test_markdown_decodes_directly(self):
        assert extract_text("readme.md", b"# Title\n\nBody") == "# Title\n\nBody"

    def test_pdf_uses_pypdf(self):
        with patch("src.services.knowledge_management.upload_service.PdfReader") as mock_reader_cls:
            page = MagicMock()
            page.extract_text.return_value = "Page text"
            mock_reader_cls.return_value.pages = [page]

            result = extract_text("doc.pdf", b"%PDF-fake-bytes")

        assert result == "Page text"

    def test_docx_uses_python_docx(self):
        with patch("src.services.knowledge_management.upload_service.DocxDocument") as mock_doc_cls:
            para = MagicMock(text="Paragraph one")
            mock_doc_cls.return_value.paragraphs = [para]

            result = extract_text("doc.docx", b"fake-docx-bytes")

        assert result == "Paragraph one"

    def test_unsupported_extension_raises(self):
        with pytest.raises(ValueError, match="Unsupported file type"):
            extract_text("archive.zip", b"whatever")


class TestUploadService:
    def test_ingest_upload_never_persists_original_bytes(self):
        sources = MagicMock()
        sources.get.return_value = _source(source_type="txt")
        documents = MagicMock()
        documents.create.return_value = MagicMock(id="d1")
        documents.get.return_value = MagicMock(id="d1", status="ready")
        service = UploadService(source_repository=sources, document_repository=documents)

        with patch("src.services.knowledge_management.upload_service.ingest_document") as mock_ingest:
            service.ingest_upload("s1", "notes.txt", b"the actual file bytes")

        # The raw bytes never appear in any call — only the decoded text does.
        call_kwargs = mock_ingest.call_args.kwargs
        assert call_kwargs["raw_text"] == "the actual file bytes"
        assert "content_bytes" not in call_kwargs
        assert call_kwargs["clean"] is False

    def test_unknown_source_raises(self):
        sources = MagicMock()
        sources.get.return_value = None
        service = UploadService(source_repository=sources)

        with pytest.raises(ValueError, match="Unknown source"):
            service.ingest_upload("s1", "notes.txt", b"data")

    def test_successful_ingest_marks_source_ready(self):
        """Regression guard: ingest_document only updates the DOCUMENT's
        status — nothing previously updated the SOURCE, leaving every
        upload source stuck at 'pending' forever even after a fully
        successful ingest (live-confirmed bug)."""
        sources = MagicMock()
        sources.get.return_value = _source(source_type="txt")
        documents = MagicMock()
        documents.create.return_value = MagicMock(id="d1")
        documents.get.return_value = MagicMock(id="d1", status="ready")
        service = UploadService(source_repository=sources, document_repository=documents)

        with patch("src.services.knowledge_management.upload_service.ingest_document"):
            service.ingest_upload("s1", "notes.txt", b"data")

        sources.mark_indexed.assert_called_once_with("s1")
        sources.set_status.assert_called_once_with("s1", "ready")

    def test_failed_ingest_marks_source_failed(self):
        sources = MagicMock()
        sources.get.return_value = _source(source_type="txt")
        documents = MagicMock()
        documents.create.return_value = MagicMock(id="d1")
        documents.get.return_value = MagicMock(id="d1", status="failed")
        service = UploadService(source_repository=sources, document_repository=documents)

        with patch("src.services.knowledge_management.upload_service.ingest_document"):
            service.ingest_upload("s1", "notes.txt", b"data")

        sources.mark_indexed.assert_not_called()
        sources.set_status.assert_called_once_with("s1", "failed")
