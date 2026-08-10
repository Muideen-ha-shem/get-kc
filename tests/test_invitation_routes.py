"""Integration tests for /workspaces/{workspace_id}/invitations (Phase 28)
— dependency-override pattern, 403 for a workspace_admin of a *different*
workspace, mirrors test_knowledge_management_routes.py's style exactly."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.deps import get_current_user_required, require_workspace_admin
from src.services.auth.auth_service import AuthUser
from src.services.org_signup.invitation_models import WorkspaceInvitation

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


def _invitation(**overrides) -> WorkspaceInvitation:
    base = {
        "id": "i1", "workspace_id": "w1", "email": "teammate@acme.com", "role": "agent",
        "department": "Support", "invited_by": "admin-1", "status": "pending",
        "created_at": None, "accepted_at": None,
    }
    base.update(overrides)
    return WorkspaceInvitation(**base)


class TestAuthorization:
    def test_create_invitation_401s_with_no_auth(self, client):
        response = client.post(
            "/workspaces/w1/invitations", json={"email": "teammate@acme.com", "role": "agent"}
        )
        assert response.status_code == 401

    def test_list_invitations_403s_for_non_admin(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: AuthUser(id="u2", email="x@x.com")
        with patch("src.api.deps._platform_admin_service.is_super_admin", return_value=False), \
             patch("src.api.deps._workspace_admin_service.is_workspace_admin", return_value=False):
            response = client.get("/workspaces/w1/invitations")
        assert response.status_code == 403


class TestCreateInvitation:
    def test_create_invitation_succeeds(self, client):
        _authenticate()
        with patch(
            "src.api.routes.invitations._invitation_service.create_invitation",
            return_value=_invitation(),
        ) as mock_create:
            response = client.post(
                "/workspaces/w1/invitations",
                json={"email": "teammate@acme.com", "role": "agent", "department": "Support"},
            )

        assert response.status_code == 200
        assert response.json()["email"] == "teammate@acme.com"
        mock_create.assert_called_once()
        assert mock_create.call_args.args == ("w1", "teammate@acme.com", "agent", "Support", "admin-1")
        assert mock_create.call_args.kwargs["redirect_to"].endswith("/accept-invite")

    def test_duplicate_pending_invite_returns_409(self, client):
        _authenticate()
        with patch(
            "src.api.routes.invitations._invitation_service.create_invitation",
            side_effect=ValueError("An invite is already pending for teammate@acme.com"),
        ):
            response = client.post(
                "/workspaces/w1/invitations",
                json={"email": "teammate@acme.com", "role": "agent"},
            )

        assert response.status_code == 409

    def test_invalid_department_rejected_by_schema(self, client):
        _authenticate()
        response = client.post(
            "/workspaces/w1/invitations",
            json={"email": "teammate@acme.com", "role": "agent", "department": "Not A Real Department"},
        )

        assert response.status_code == 422


class TestListAndRevoke:
    def test_list_invitations(self, client):
        _authenticate()
        with patch(
            "src.api.routes.invitations._invitation_service.list_pending", return_value=[_invitation()]
        ):
            response = client.get("/workspaces/w1/invitations")

        assert response.status_code == 200
        assert response.json()[0]["id"] == "i1"

    def test_revoke_invitation(self, client):
        _authenticate()
        with patch("src.api.routes.invitations._invitation_service.revoke") as mock_revoke:
            response = client.delete("/workspaces/w1/invitations/i1")

        assert response.status_code == 200
        mock_revoke.assert_called_once_with("i1", "w1")
