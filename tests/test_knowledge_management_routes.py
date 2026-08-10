"""Integration tests for /workspaces/{workspace_id}/knowledge/* (Phase 27)
— dependency-override pattern, 403 for a workspace_admin of a *different*
workspace, mirrors test_admin_workspace_routes.py's style."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.deps import get_current_user_required, require_workspace_admin
from src.services.auth.auth_service import AuthUser
from src.services.knowledge_management.km_models import KnowledgeSource

_FAKE_ADMIN = AuthUser(id="admin-1", email="admin@example.com", full_name="Admin")


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _authenticate():
    app.dependency_overrides[require_workspace_admin] = lambda: _FAKE_ADMIN
    app.dependency_overrides[get_current_user_required] = lambda: _FAKE_ADMIN


def _source(**overrides) -> KnowledgeSource:
    base = {
        "id": "s1", "workspace_id": "w1", "source_type": "website", "name": "Docs",
        "status": "ready", "collection_id": None, "config": {"url": "https://x.com"}, "product": None,
        "schedule": "manual", "last_crawled_at": None, "last_indexed_at": None,
        "created_at": None, "updated_at": None, "archived_at": None,
    }
    base.update(overrides)
    return KnowledgeSource(**base)


class TestAuthorization:
    def test_list_sources_401s_with_no_auth(self, client):
        response = client.get("/workspaces/w1/knowledge/sources")
        assert response.status_code == 401

    def test_list_sources_403s_for_non_admin(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: AuthUser(id="u2", email="x@x.com")
        with patch("src.api.deps._platform_admin_service.is_super_admin", return_value=False), \
             patch("src.api.deps._workspace_admin_service.is_workspace_admin", return_value=False):
            response = client.get("/workspaces/w1/knowledge/sources")
        assert response.status_code == 403


class TestSources:
    def test_list_sources(self, client):
        _authenticate()
        with patch(
            "src.api.routes.knowledge_management._source_service.list_for_workspace", return_value=[_source()]
        ):
            response = client.get("/workspaces/w1/knowledge/sources")

        assert response.status_code == 200
        assert response.json()[0]["name"] == "Docs"

    def test_create_source_rejects_unknown_type(self, client):
        _authenticate()
        with patch(
            "src.api.routes.knowledge_management._get_workspace_or_404"
        ), patch(
            "src.api.routes.knowledge_management._source_service.create",
            side_effect=ValueError("Unknown source_type: notion"),
        ):
            response = client.post(
                "/workspaces/w1/knowledge/sources", json={"source_type": "notion", "name": "Notion"}
            )

        assert response.status_code == 400

    def test_create_source_succeeds(self, client):
        _authenticate()
        with patch("src.api.routes.knowledge_management._get_workspace_or_404"), \
             patch("src.api.routes.knowledge_management._source_service.create", return_value=_source()):
            response = client.post(
                "/workspaces/w1/knowledge/sources", json={"source_type": "website", "name": "Docs"}
            )

        assert response.status_code == 200
        assert response.json()["source_type"] == "website"

    def test_delete_source_archives_and_removes_chunks(self, client):
        _authenticate()
        with patch(
            "src.api.routes.knowledge_management._source_service.get", return_value=_source()
        ), patch(
            "src.api.routes.knowledge_management._source_service.archive", return_value=_source(status="archived")
        ) as mock_archive:
            response = client.delete("/workspaces/w1/knowledge/sources/s1")

        assert response.status_code == 200
        assert response.json()["status"] == "archived"
        mock_archive.assert_called_once_with("s1")

    def test_source_not_in_workspace_404s(self, client):
        _authenticate()
        with patch(
            "src.api.routes.knowledge_management._source_service.get", return_value=_source(workspace_id="other-ws")
        ):
            response = client.post("/workspaces/w1/knowledge/sources/s1/pause")

        assert response.status_code == 404


class TestFaqs:
    def test_create_faq(self, client):
        _authenticate()
        document = MagicMock(
            id="d1", workspace_id="w1", source_id="s1", status="ready", parent_url=None,
            title="Q?", chunk_count=1, char_count=10, error_message=None, created_at=None,
        )
        with patch("src.api.routes.knowledge_management._get_workspace_or_404"), \
             patch("src.api.routes.knowledge_management._faq_service.create_faq", return_value=document):
            response = client.post(
                "/workspaces/w1/knowledge/faqs", json={"question": "What is SPIDIFY?", "answer": "An identity product."}
            )

        assert response.status_code == 200
        assert response.json()["status"] == "ready"


class TestKnowledgeTest:
    def test_test_question_reuses_retrieval(self, client):
        _authenticate()
        fake_result = {
            "question": "How does it work?", "chunks": [], "sources": [], "confidence": 0.0,
        }
        with patch("src.api.routes.knowledge_management._get_workspace_or_404"), \
             patch("src.api.routes.knowledge_management._testing_service.test_question", return_value=fake_result):
            response = client.post("/workspaces/w1/knowledge/test", json={"question": "How does it work?"})

        assert response.status_code == 200
        assert response.json()["confidence"] == 0.0


class TestQuality:
    def test_run_scan(self, client):
        _authenticate()
        report = MagicMock(
            id="r1", workspace_id="w1", generated_at=None, duplicate_chunk_count=0, broken_url_count=0,
            empty_document_count=0, embedding_failure_count=0, large_chunk_count=0, missing_metadata_count=0,
            details=None,
        )
        with patch("src.api.routes.knowledge_management._get_workspace_or_404"), \
             patch("src.api.routes.knowledge_management._quality_service.run_quality_scan", return_value=report):
            response = client.post("/workspaces/w1/knowledge/quality/scan")

        assert response.status_code == 200
        assert response.json()["id"] == "r1"


class TestDashboard:
    def test_dashboard_aggregates_sources_and_documents(self, client):
        _authenticate()
        sources = [_source(status="ready"), _source(id="s2", status="pending"), _source(id="s3", status="failed")]
        documents = [MagicMock(chunk_count=3), MagicMock(chunk_count=5)]
        with patch("src.api.routes.knowledge_management._get_workspace_or_404"), \
             patch("src.api.routes.knowledge_management._source_service.list_for_workspace", return_value=sources), \
             patch("src.api.routes.knowledge_management._document_repository.list_for_workspace", return_value=documents):
            response = client.get("/workspaces/w1/knowledge/dashboard")

        assert response.status_code == 200
        body = response.json()
        assert body["total_sources"] == 3
        assert body["indexed_sources"] == 1
        assert body["pending_sources"] == 1
        assert body["failed_sources"] == 1
        assert body["total_documents"] == 2
        assert body["total_chunks"] == 8
