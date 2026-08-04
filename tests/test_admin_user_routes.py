"""Integration tests for /admin/users*, /admin/agents* (Phase 26)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.deps import get_current_user_required, require_super_admin
from src.services.auth.auth_service import AuthUser

_FAKE_ADMIN = AuthUser(id="admin-1", email="admin@example.com", full_name="Admin")
_FAKE_NON_ADMIN = AuthUser(id="u2", email="customer@example.com", full_name="Customer")


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _authenticate_as_admin():
    app.dependency_overrides[require_super_admin] = lambda: _FAKE_ADMIN
    app.dependency_overrides[get_current_user_required] = lambda: _FAKE_ADMIN


def _authenticate_as_non_admin():
    app.dependency_overrides[get_current_user_required] = lambda: _FAKE_NON_ADMIN


class TestAuthorization:
    def test_list_users_401s_with_no_auth_at_all(self, client):
        response = client.get("/admin/users")
        assert response.status_code == 401

    def test_list_users_403s_for_authenticated_non_admin(self, client):
        _authenticate_as_non_admin()
        with patch("src.api.deps._platform_admin_service.is_super_admin", return_value=False):
            response = client.get("/admin/users")
        assert response.status_code == 403

    def test_list_agents_403s_for_authenticated_non_admin(self, client):
        _authenticate_as_non_admin()
        with patch("src.api.deps._platform_admin_service.is_super_admin", return_value=False):
            response = client.get("/admin/agents", params={"workspace_id": "w1"})
        assert response.status_code == 403


class TestUserManagement:
    def test_list_users_surfaces_service_role_error_as_500(self, client):
        _authenticate_as_admin()
        with patch(
            "src.api.routes.admin_users.AuthService.admin_list_users",
            side_effect=RuntimeError("Missing Supabase service-role credentials"),
        ):
            response = client.get("/admin/users")

        assert response.status_code == 500

    def test_list_users_succeeds(self, client):
        _authenticate_as_admin()
        fake_user = MagicMock(id="u2", email="customer@example.com", full_name="Customer")
        with patch("src.api.routes.admin_users.AuthService.admin_list_users", return_value=[fake_user]):
            response = client.get("/admin/users")

        assert response.status_code == 200
        assert response.json()[0]["email"] == "customer@example.com"

    def test_suspend_user_records_audit(self, client):
        _authenticate_as_admin()
        with patch("src.api.routes.admin_users.AuthService.admin_suspend_user", return_value=None), \
             patch("src.api.routes.admin_users._audit_service.record") as mock_record:
            response = client.post("/admin/users/u2/suspend")

        assert response.status_code == 200
        mock_record.assert_called_once_with("user.suspended", "admin-1", None, {"target_auth_user_id": "u2"})

    def test_assign_admin_role(self, client):
        _authenticate_as_admin()
        with patch("src.api.routes.admin_users._platform_admin_service.add_admin") as mock_add, \
             patch("src.api.routes.admin_users._audit_service.record"):
            response = client.post("/admin/users/u2/roles", json={"role": "admin"})

        assert response.status_code == 200
        mock_add.assert_called_once_with("u2")

    def test_assign_agent_role_requires_workspace_id(self, client):
        _authenticate_as_admin()
        response = client.post("/admin/users/u2/roles", json={"role": "agent"})
        assert response.status_code == 400

    def test_assign_agent_role_succeeds_with_workspace_id(self, client):
        _authenticate_as_admin()
        with patch("src.api.routes.admin_users._agent_service.get_or_create") as mock_get_or_create, \
             patch("src.api.routes.admin_users._audit_service.record"):
            response = client.post(
                "/admin/users/u2/roles",
                json={"role": "agent", "workspace_id": "w1", "name": "Ada", "email": "ada@x.com"},
            )

        assert response.status_code == 200
        mock_get_or_create.assert_called_once_with("u2", "ada@x.com", "Ada", "w1", department="General")


class TestAgentManagement:
    def test_list_agents(self, client):
        _authenticate_as_admin()
        agent = MagicMock(
            id="a1", workspace_id="w1", email="ada@x.com",
            department="Support", status="available", created_at=None,
        )
        agent.configure_mock(name="Ada")
        with patch("src.api.routes.admin_users._agent_service.list_by_workspace", return_value=[agent]):
            response = client.get("/admin/agents", params={"workspace_id": "w1"})

        assert response.status_code == 200
        assert response.json()[0]["name"] == "Ada"

    def test_delete_agent(self, client):
        _authenticate_as_admin()
        with patch("src.api.routes.admin_users._agent_service.delete") as mock_delete, \
             patch("src.api.routes.admin_users._audit_service.record"):
            response = client.delete("/admin/agents/a1")

        assert response.status_code == 200
        mock_delete.assert_called_once_with("a1")

    def test_update_agent_department(self, client):
        _authenticate_as_admin()
        agent = MagicMock(
            id="a1", workspace_id="w1", email="ada@x.com",
            department="Sales", status="available", created_at=None,
        )
        agent.configure_mock(name="Ada")
        with patch("src.api.routes.admin_users._agent_service.update_department", return_value=agent), \
             patch("src.api.routes.admin_users._audit_service.record"):
            response = client.patch("/admin/agents/a1/department", params={"department": "Sales"})

        assert response.status_code == 200
        assert response.json()["department"] == "Sales"

    def test_agent_performance_omits_satisfaction_score(self, client):
        _authenticate_as_admin()
        with patch(
            "src.api.routes.admin_users._escalation_repository.count_active_for_agent", return_value=2
        ), patch(
            "src.api.routes.admin_users._escalation_repository.list_resolved_today_for_agent", return_value=[]
        ):
            response = client.get("/admin/agents/a1/performance")

        assert response.status_code == 200
        body = response.json()
        assert body["active_chats"] == 2
        assert body["satisfaction_score"] is None
