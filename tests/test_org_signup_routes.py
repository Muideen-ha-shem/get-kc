"""Integration tests for the public /org-signup/* routes (Phase 28) —
no auth dependency anywhere in this file, mirrors test_phase20_routes.py's
patched-singleton pattern."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.services.admin.admin_models import AdminWorkspace
from src.services.auth.auth_service import AuthSession, AuthUser
from src.services.org_signup.invitation_models import WorkspaceInvitation
from src.services.org_signup.org_signup_models import OrgSignupError, OrgSignupResult


@pytest.fixture()
def client():
    return TestClient(app)


def _result():
    return OrgSignupResult(
        session=AuthSession(
            access_token="access-1", refresh_token="refresh-1",
            user=AuthUser(id="u1", email="a@acme.com", full_name="Ada"),
        ),
        workspace=AdminWorkspace(
            id="w1", slug="acme", name="Acme", api_key="raw-key", is_active=True,
            owner_auth_user_id="u1", plan="free",
        ),
    )


class TestSignUpOrganization:
    def test_signup_returns_session_workspace_and_api_key(self, client):
        with patch(
            "src.api.routes.org_signup._org_signup_service.sign_up_organization", return_value=_result()
        ):
            response = client.post(
                "/org-signup",
                json={
                    "full_name": "Ada", "email": "a@acme.com", "password": "password123",
                    "org_name": "Acme", "slug": "acme", "plan": "free",
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert body["access_token"] == "access-1"
        assert body["workspace"]["slug"] == "acme"
        assert body["api_key"] == "raw-key"

    def test_duplicate_slug_returns_409(self, client):
        with patch(
            "src.api.routes.org_signup._org_signup_service.sign_up_organization",
            side_effect=OrgSignupError("Workspace slug 'acme' already exists"),
        ):
            response = client.post(
                "/org-signup",
                json={
                    "full_name": "Ada", "email": "a@acme.com", "password": "password123",
                    "org_name": "Acme", "slug": "acme", "plan": "free",
                },
            )

        assert response.status_code == 409

    def test_invalid_slug_rejected_by_schema(self, client):
        response = client.post(
            "/org-signup",
            json={
                "full_name": "Ada", "email": "a@acme.com", "password": "password123",
                "org_name": "Acme", "slug": "Not A Valid Slug!", "plan": "free",
            },
        )

        assert response.status_code == 422

    def test_no_auth_required(self, client):
        """Confirms this route is genuinely public — no Authorization header sent."""
        with patch(
            "src.api.routes.org_signup._org_signup_service.sign_up_organization", return_value=_result()
        ):
            response = client.post(
                "/org-signup",
                json={
                    "full_name": "Ada", "email": "a@acme.com", "password": "password123",
                    "org_name": "Acme", "slug": "acme", "plan": "free",
                },
            )

        assert response.status_code != 401


class TestSlugAvailable:
    def test_taken_slug_returns_false(self, client):
        with patch(
            "src.api.routes.org_signup._workspace_repository.list_all",
            return_value=[AdminWorkspace(id="w1", slug="acme", name="Acme")],
        ):
            response = client.get("/org-signup/slug-available", params={"slug": "acme"})

        assert response.json() == {"available": False}

    def test_free_slug_returns_true(self, client):
        with patch("src.api.routes.org_signup._workspace_repository.list_all", return_value=[]):
            response = client.get("/org-signup/slug-available", params={"slug": "brand-new"})

        assert response.json() == {"available": True}


class TestAcceptInvite:
    def test_accept_invite_returns_session(self, client):
        invitation = WorkspaceInvitation(
            id="i1", workspace_id="w1", email="teammate@acme.com", role="agent",
            department="Support", invited_by="u1", status="accepted",
        )
        with patch(
            "src.api.routes.org_signup._invitation_service.accept_invitation", return_value=invitation
        ), patch("src.api.routes.org_signup.AuthService") as mock_auth_cls:
            mock_auth_instance = MagicMock()
            mock_auth_instance.sign_in.return_value = AuthSession(
                access_token="access-2", refresh_token="refresh-2",
                user=AuthUser(id="u2", email="teammate@acme.com", full_name="Teammate"),
            )
            mock_auth_cls.return_value = mock_auth_instance

            response = client.post(
                "/org-signup/accept-invite",
                json={"access_token": "recovery-token", "password": "new-password123"},
            )

        assert response.status_code == 200
        assert response.json()["access_token"] == "access-2"

    def test_invalid_token_returns_400(self, client):
        from src.services.org_signup.invitation_service import InvitationError

        with patch(
            "src.api.routes.org_signup._invitation_service.accept_invitation",
            side_effect=InvitationError("This invite link is invalid or has expired."),
        ):
            response = client.post(
                "/org-signup/accept-invite",
                json={"access_token": "bad-token", "password": "new-password123"},
            )

        assert response.status_code == 400
