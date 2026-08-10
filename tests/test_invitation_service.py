"""Tests for InvitationService (Phase 28) — mocked repository/AuthService/
AgentService/WorkspaceAdminService/ProfileService."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.services.auth.auth_service import AuthUser
from src.services.org_signup.invitation_models import WorkspaceInvitation
from src.services.org_signup.invitation_service import InvitationError, InvitationService


def _invitation(**overrides) -> WorkspaceInvitation:
    base = {
        "id": "i1", "workspace_id": "w1", "email": "teammate@acme.com", "role": "agent",
        "department": "Support", "invited_by": "u1", "status": "pending",
        "created_at": None, "accepted_at": None,
    }
    base.update(overrides)
    return WorkspaceInvitation(**base)


class TestCreateInvitation:
    def test_creates_row_and_sends_invite_email(self):
        repo = MagicMock()
        repo.create.return_value = _invitation()
        service = InvitationService(repository=repo)

        with patch("src.services.org_signup.invitation_service.AuthService") as mock_auth_cls:
            mock_auth_instance = MagicMock()
            mock_auth_cls.return_value = mock_auth_instance

            invitation = service.create_invitation(
                "w1", "teammate@acme.com", "agent", "Support", "u1", redirect_to="https://x/accept-invite"
            )

        repo.create.assert_called_once_with("w1", "teammate@acme.com", "agent", "Support", "u1")
        mock_auth_instance.admin_invite_user.assert_called_once_with(
            "teammate@acme.com", redirect_to="https://x/accept-invite"
        )
        assert invitation.id == "i1"

    def test_duplicate_pending_invite_raises_value_error(self):
        repo = MagicMock()
        repo.create.side_effect = ValueError("An invite is already pending for teammate@acme.com")
        service = InvitationService(repository=repo)

        with pytest.raises(ValueError, match="already pending"):
            service.create_invitation("w1", "teammate@acme.com", "agent", "Support", "u1")

    def test_invite_email_failure_does_not_prevent_row_creation(self):
        from src.services.auth.auth_service import AuthError

        repo = MagicMock()
        repo.create.return_value = _invitation()
        service = InvitationService(repository=repo)

        with patch("src.services.org_signup.invitation_service.AuthService") as mock_auth_cls:
            mock_auth_instance = MagicMock()
            mock_auth_instance.admin_invite_user.side_effect = AuthError("email service unavailable")
            mock_auth_cls.return_value = mock_auth_instance

            invitation = service.create_invitation("w1", "teammate@acme.com", "agent", "Support", "u1")

        assert invitation.id == "i1"


class TestListAndRevoke:
    def test_list_pending_delegates_to_repository(self):
        repo = MagicMock()
        repo.list_for_workspace.return_value = [_invitation()]
        service = InvitationService(repository=repo)

        result = service.list_pending("w1")

        assert len(result) == 1
        repo.list_for_workspace.assert_called_once_with("w1")

    def test_revoke_delegates_to_repository(self):
        repo = MagicMock()
        service = InvitationService(repository=repo)

        service.revoke("i1", "w1")

        repo.revoke.assert_called_once_with("i1", "w1")


class TestAcceptInvitation:
    def test_agent_invitation_creates_agent_row(self):
        repo = MagicMock()
        repo.find_pending_by_email.return_value = _invitation(role="agent", department="Sales")
        repo.mark_accepted.return_value = _invitation(role="agent", status="accepted")
        agent_service = MagicMock()
        workspace_admin_service = MagicMock()
        profile_service = MagicMock()
        service = InvitationService(
            repository=repo, workspace_admin_service=workspace_admin_service,
            agent_service=agent_service, profile_service=profile_service,
        )

        with patch("src.services.org_signup.invitation_service.AuthService") as mock_auth_cls, \
             patch("src.services.org_signup.invitation_service.get_admin_client") as mock_get_admin:
            mock_auth_instance = MagicMock()
            mock_auth_instance.get_user.return_value = AuthUser(
                id="u2", email="teammate@acme.com", full_name="Teammate"
            )
            mock_auth_cls.return_value = mock_auth_instance
            mock_admin_client = MagicMock()
            mock_get_admin.return_value = mock_admin_client

            result = service.accept_invitation("recovery-token", "new-password123")

        mock_admin_client.auth.admin.update_user_by_id.assert_called_once_with(
            "u2", {"password": "new-password123"}
        )
        agent_service.get_or_create.assert_called_once_with(
            "u2", "teammate@acme.com", "Teammate", "w1", department="Sales"
        )
        workspace_admin_service.add_admin.assert_not_called()
        repo.mark_accepted.assert_called_once_with("i1")
        # Regression guard for the same live-confirmed cross-tenant leak as
        # OrgSignupService: invite_user_by_email also provisions auth.users
        # up front, firing the trigger that creates a blank profile row
        # before this invitation's workspace is known.
        profile_service.set_workspace_id.assert_called_once_with(
            "u2", "w1", access_token="recovery-token"
        )
        assert result.status == "accepted"

    def test_workspace_admin_invitation_creates_admin_row(self):
        repo = MagicMock()
        repo.find_pending_by_email.return_value = _invitation(role="workspace_admin", department=None)
        repo.mark_accepted.return_value = _invitation(role="workspace_admin", status="accepted")
        agent_service = MagicMock()
        workspace_admin_service = MagicMock()
        profile_service = MagicMock()
        service = InvitationService(
            repository=repo, workspace_admin_service=workspace_admin_service,
            agent_service=agent_service, profile_service=profile_service,
        )

        with patch("src.services.org_signup.invitation_service.AuthService") as mock_auth_cls, \
             patch("src.services.org_signup.invitation_service.get_admin_client"):
            mock_auth_instance = MagicMock()
            mock_auth_instance.get_user.return_value = AuthUser(
                id="u2", email="teammate@acme.com", full_name="Teammate"
            )
            mock_auth_cls.return_value = mock_auth_instance

            service.accept_invitation("recovery-token", "new-password123")

        workspace_admin_service.add_admin.assert_called_once_with("w1", "u2")
        agent_service.get_or_create.assert_not_called()

    def test_invalid_token_raises_invitation_error(self):
        repo = MagicMock()
        service = InvitationService(repository=repo)

        with patch("src.services.org_signup.invitation_service.AuthService") as mock_auth_cls:
            mock_auth_instance = MagicMock()
            mock_auth_instance.get_user.return_value = None
            mock_auth_cls.return_value = mock_auth_instance

            with pytest.raises(InvitationError, match="invalid or has expired"):
                service.accept_invitation("bad-token", "new-password123")

        repo.find_pending_by_email.assert_not_called()

    def test_no_pending_invitation_raises_invitation_error(self):
        repo = MagicMock()
        repo.find_pending_by_email.return_value = None
        service = InvitationService(repository=repo)

        with patch("src.services.org_signup.invitation_service.AuthService") as mock_auth_cls, \
             patch("src.services.org_signup.invitation_service.get_admin_client"):
            mock_auth_instance = MagicMock()
            mock_auth_instance.get_user.return_value = AuthUser(
                id="u2", email="nobody@acme.com", full_name=None
            )
            mock_auth_cls.return_value = mock_auth_instance

            with pytest.raises(InvitationError, match="No pending invitation"):
                service.accept_invitation("recovery-token", "new-password123")

    def test_profile_creation_failure_is_swallowed(self):
        repo = MagicMock()
        repo.find_pending_by_email.return_value = _invitation(role="agent", department="Sales")
        repo.mark_accepted.return_value = _invitation(role="agent", status="accepted")
        agent_service = MagicMock()
        profile_service = MagicMock()
        profile_service.get_or_create.side_effect = RuntimeError("profile write failed")
        service = InvitationService(
            repository=repo, agent_service=agent_service, profile_service=profile_service,
        )

        with patch("src.services.org_signup.invitation_service.AuthService") as mock_auth_cls, \
             patch("src.services.org_signup.invitation_service.get_admin_client"):
            mock_auth_instance = MagicMock()
            mock_auth_instance.get_user.return_value = AuthUser(
                id="u2", email="teammate@acme.com", full_name="Teammate"
            )
            mock_auth_cls.return_value = mock_auth_instance

            result = service.accept_invitation("recovery-token", "new-password123")

        assert result.status == "accepted"
