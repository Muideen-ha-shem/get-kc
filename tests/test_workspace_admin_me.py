"""Tests for GET /workspace-admins/me and its supporting repository/service
methods (Phase 28) — lets a signed-in user discover which workspace(s)
they administer."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.deps import get_current_user_required
from src.services.admin.admin_models import AdminWorkspace
from src.services.admin.workspace_admin_repository import WorkspaceAdminRepository
from src.services.admin.workspace_admin_service import WorkspaceAdminService
from src.services.auth.auth_service import AuthUser


class TestWorkspaceAdminRepositoryListForAuthUserId:
    def test_returns_rows_for_user_across_workspaces(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "wa1", "workspace_id": "w1", "auth_user_id": "u1"},
            {"id": "wa2", "workspace_id": "w2", "auth_user_id": "u1"},
        ]
        repo = WorkspaceAdminRepository(client=client)

        rows = repo.list_for_auth_user_id("u1")

        assert [r["workspace_id"] for r in rows] == ["w1", "w2"]


class TestWorkspaceAdminServiceListWorkspaceIds:
    def test_extracts_workspace_ids(self):
        repo = MagicMock()
        repo.list_for_auth_user_id.return_value = [
            {"workspace_id": "w1"}, {"workspace_id": "w2"},
        ]
        service = WorkspaceAdminService(repository=repo)

        assert service.list_workspace_ids_for_admin("u1") == ["w1", "w2"]


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


class TestWorkspaceAdminsMeRoute:
    def test_returns_empty_list_for_non_admin(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: AuthUser(id="u1", email="a@b.com")
        with patch(
            "src.api.routes.workspace_admins._workspace_admin_service.list_workspace_ids_for_admin",
            return_value=[],
        ):
            response = client.get("/workspace-admins/me")

        assert response.status_code == 200
        assert response.json() == {"workspaces": []}

    def test_returns_workspace_details_for_admin(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: AuthUser(id="u1", email="a@b.com")
        with patch(
            "src.api.routes.workspace_admins._workspace_admin_service.list_workspace_ids_for_admin",
            return_value=["w1"],
        ), patch(
            "src.api.routes.workspace_admins._workspace_repository.get_by_id",
            return_value=AdminWorkspace(id="w1", slug="acme", name="Acme"),
        ):
            response = client.get("/workspace-admins/me")

        assert response.status_code == 200
        assert response.json() == {"workspaces": [{"id": "w1", "slug": "acme", "name": "Acme"}]}

    def test_requires_authentication(self, client):
        response = client.get("/workspace-admins/me")
        assert response.status_code == 401
