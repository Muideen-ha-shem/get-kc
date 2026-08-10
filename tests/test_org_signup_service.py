"""Tests for OrgSignupService (Phase 28) — mocked AuthService/TenantService/
WorkspaceAdminService/ProfileService, asserting exact call sequencing and
the documented best-effort failure semantics."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.services.admin.admin_models import AdminWorkspace
from src.services.auth.auth_service import AuthError, AuthSession, AuthUser
from src.services.org_signup.org_signup_models import OrgSignupError
from src.services.org_signup.org_signup_service import OrgSignupService


def _session(user_id="u1", email="a@acme.com"):
    return AuthSession(
        access_token="access-1", refresh_token="refresh-1",
        user=AuthUser(id=user_id, email=email, full_name="Ada"),
    )


def _workspace(**overrides):
    base = {
        "id": "w1", "slug": "acme", "name": "Acme", "api_key": "raw-key", "host": None,
        "is_active": True, "owner_auth_user_id": "u1", "plan": "free",
    }
    base.update(overrides)
    return AdminWorkspace(**base)


@pytest.fixture()
def services():
    tenant_service = MagicMock()
    tenant_service.create_workspace.return_value = _workspace()
    workspace_admin_service = MagicMock()
    profile_service = MagicMock()
    return tenant_service, workspace_admin_service, profile_service


class TestSignUpOrganizationHappyPath:
    def test_full_sequence_creates_user_workspace_admin_and_profile(self, services):
        tenant_service, workspace_admin_service, profile_service = services
        service = OrgSignupService(
            tenant_service=tenant_service, workspace_admin_service=workspace_admin_service,
            profile_service=profile_service,
        )

        with patch("src.services.org_signup.org_signup_service.AuthService") as mock_auth_cls:
            admin_auth = MagicMock()
            admin_auth.admin_create_user.return_value = AuthUser(id="u1", email="a@acme.com", full_name="Ada")
            anon_auth = MagicMock()
            anon_auth.sign_in.return_value = _session()
            mock_auth_cls.side_effect = [admin_auth, anon_auth]

            result = service.sign_up_organization(
                full_name="Ada", email="a@acme.com", password="password123",
                org_name="Acme", slug="acme", plan="free",
            )

        admin_auth.admin_create_user.assert_called_once_with("a@acme.com", "password123", "Ada")
        anon_auth.sign_in.assert_called_once_with("a@acme.com", "password123")
        tenant_service.create_workspace.assert_called_once_with(
            "acme", "Acme", host=None, actor_auth_user_id="u1", owner_auth_user_id="u1", plan="free",
        )
        workspace_admin_service.add_admin.assert_called_once_with("w1", "u1")
        profile_service.get_or_create.assert_called_once_with(
            "u1", "a@acme.com", "Ada", access_token="access-1", workspace_id="w1"
        )
        assert result.workspace.id == "w1"
        assert result.session.access_token == "access-1"


class TestSignUpOrganizationDuplicateEmailRetry:
    def test_already_registered_falls_back_to_sign_in(self, services):
        tenant_service, workspace_admin_service, profile_service = services
        service = OrgSignupService(
            tenant_service=tenant_service, workspace_admin_service=workspace_admin_service,
            profile_service=profile_service,
        )

        with patch("src.services.org_signup.org_signup_service.AuthService") as mock_auth_cls:
            admin_auth = MagicMock()
            admin_auth.admin_create_user.side_effect = AuthError("Email address already registered")
            anon_auth = MagicMock()
            anon_auth.sign_in.return_value = _session()
            mock_auth_cls.side_effect = [admin_auth, anon_auth]

            result = service.sign_up_organization(
                full_name="Ada", email="a@acme.com", password="password123",
                org_name="Acme", slug="acme-2", plan="free",
            )

        assert result.session.access_token == "access-1"
        tenant_service.create_workspace.assert_called_once()

    def test_genuinely_wrong_password_raises_org_signup_error(self, services):
        tenant_service, workspace_admin_service, profile_service = services
        service = OrgSignupService(
            tenant_service=tenant_service, workspace_admin_service=workspace_admin_service,
            profile_service=profile_service,
        )

        with patch("src.services.org_signup.org_signup_service.AuthService") as mock_auth_cls:
            admin_auth = MagicMock()
            admin_auth.admin_create_user.side_effect = AuthError("Email address already registered")
            anon_auth = MagicMock()
            anon_auth.sign_in.side_effect = AuthError("Invalid email or password")
            mock_auth_cls.side_effect = [admin_auth, anon_auth]

            with pytest.raises(OrgSignupError):
                service.sign_up_organization(
                    full_name="Ada", email="a@acme.com", password="wrong-password",
                    org_name="Acme", slug="acme-2", plan="free",
                )

        tenant_service.create_workspace.assert_not_called()

    def test_other_auth_error_raises_immediately_without_retry(self, services):
        tenant_service, workspace_admin_service, profile_service = services
        service = OrgSignupService(
            tenant_service=tenant_service, workspace_admin_service=workspace_admin_service,
            profile_service=profile_service,
        )

        with patch("src.services.org_signup.org_signup_service.AuthService") as mock_auth_cls:
            admin_auth = MagicMock()
            admin_auth.admin_create_user.side_effect = AuthError("Password should be at least 6 characters")
            mock_auth_cls.return_value = admin_auth

            with pytest.raises(OrgSignupError):
                service.sign_up_organization(
                    full_name="Ada", email="a@acme.com", password="123",
                    org_name="Acme", slug="acme", plan="free",
                )

        tenant_service.create_workspace.assert_not_called()


class TestSignUpOrganizationDuplicateSlug:
    def test_duplicate_slug_raises_org_signup_error(self, services):
        tenant_service, workspace_admin_service, profile_service = services
        tenant_service.create_workspace.side_effect = ValueError("Workspace slug 'acme' already exists")
        service = OrgSignupService(
            tenant_service=tenant_service, workspace_admin_service=workspace_admin_service,
            profile_service=profile_service,
        )

        with patch("src.services.org_signup.org_signup_service.AuthService") as mock_auth_cls:
            admin_auth = MagicMock()
            admin_auth.admin_create_user.return_value = AuthUser(id="u1", email="a@acme.com", full_name="Ada")
            anon_auth = MagicMock()
            anon_auth.sign_in.return_value = _session()
            mock_auth_cls.side_effect = [admin_auth, anon_auth]

            with pytest.raises(OrgSignupError, match="already exists"):
                service.sign_up_organization(
                    full_name="Ada", email="a@acme.com", password="password123",
                    org_name="Acme", slug="acme", plan="free",
                )

        workspace_admin_service.add_admin.assert_not_called()


class TestSignUpOrganizationPartialFailure:
    def test_admin_assignment_failure_still_returns_valid_session(self, services):
        tenant_service, workspace_admin_service, profile_service = services
        workspace_admin_service.add_admin.side_effect = RuntimeError("db unavailable")
        service = OrgSignupService(
            tenant_service=tenant_service, workspace_admin_service=workspace_admin_service,
            profile_service=profile_service,
        )

        with patch("src.services.org_signup.org_signup_service.AuthService") as mock_auth_cls:
            admin_auth = MagicMock()
            admin_auth.admin_create_user.return_value = AuthUser(id="u1", email="a@acme.com", full_name="Ada")
            anon_auth = MagicMock()
            anon_auth.sign_in.return_value = _session()
            mock_auth_cls.side_effect = [admin_auth, anon_auth]

            result = service.sign_up_organization(
                full_name="Ada", email="a@acme.com", password="password123",
                org_name="Acme", slug="acme", plan="free",
            )

        assert result.session.access_token == "access-1"
        assert result.workspace.id == "w1"

    def test_profile_creation_failure_is_swallowed(self, services):
        tenant_service, workspace_admin_service, profile_service = services
        profile_service.get_or_create.side_effect = RuntimeError("profile write failed")
        service = OrgSignupService(
            tenant_service=tenant_service, workspace_admin_service=workspace_admin_service,
            profile_service=profile_service,
        )

        with patch("src.services.org_signup.org_signup_service.AuthService") as mock_auth_cls:
            admin_auth = MagicMock()
            admin_auth.admin_create_user.return_value = AuthUser(id="u1", email="a@acme.com", full_name="Ada")
            anon_auth = MagicMock()
            anon_auth.sign_in.return_value = _session()
            mock_auth_cls.side_effect = [admin_auth, anon_auth]

            result = service.sign_up_organization(
                full_name="Ada", email="a@acme.com", password="password123",
                org_name="Acme", slug="acme", plan="free",
            )

        assert result.session.access_token == "access-1"
