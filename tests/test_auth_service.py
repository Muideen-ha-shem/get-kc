"""Tests for AuthService — all Supabase calls mocked."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.services.auth.auth_service import AuthError, AuthService


def _mock_session_response(user_id="u1", email="a@b.com", full_name=None):
    response = MagicMock()
    response.user = MagicMock(id=user_id, email=email, user_metadata={"full_name": full_name} if full_name else {})
    response.session = MagicMock(access_token="access-1", refresh_token="refresh-1")
    return response


class TestSignUp:
    def test_returns_session_on_success(self):
        client = MagicMock()
        client.auth.sign_up.return_value = _mock_session_response(full_name="Ada")
        service = AuthService(client=client)

        session = service.sign_up("a@b.com", "password123", "Ada")

        assert session.access_token == "access-1"
        assert session.user.id == "u1"
        assert session.user.full_name == "Ada"
        call_args = client.auth.sign_up.call_args[0][0]
        assert call_args["options"]["data"]["full_name"] == "Ada"

    def test_no_session_means_email_confirmation_required(self):
        client = MagicMock()
        response = _mock_session_response()
        response.session = None
        client.auth.sign_up.return_value = response
        service = AuthService(client=client)

        with pytest.raises(AuthError):
            service.sign_up("a@b.com", "password123")

    def test_supabase_exception_wrapped_as_auth_error(self):
        client = MagicMock()
        client.auth.sign_up.side_effect = RuntimeError("already registered")
        service = AuthService(client=client)

        with pytest.raises(AuthError):
            service.sign_up("a@b.com", "password123")


class TestSignIn:
    def test_returns_session_on_success(self):
        client = MagicMock()
        client.auth.sign_in_with_password.return_value = _mock_session_response()
        service = AuthService(client=client)

        session = service.sign_in("a@b.com", "password123")

        assert session.user.email == "a@b.com"
        client.auth.sign_in_with_password.assert_called_once_with(
            {"email": "a@b.com", "password": "password123"}
        )

    def test_bad_credentials_raise_auth_error_not_leaking_details(self):
        client = MagicMock()
        client.auth.sign_in_with_password.side_effect = RuntimeError("invalid_grant")
        service = AuthService(client=client)

        with pytest.raises(AuthError, match="Invalid email or password"):
            service.sign_in("a@b.com", "wrong")


class TestSignOut:
    def test_calls_admin_sign_out_with_global_scope(self):
        client = MagicMock()
        service = AuthService(client=client)

        service.sign_out("token-123")

        client.auth.admin.sign_out.assert_called_once_with("token-123", "global")

    def test_failure_is_swallowed_not_raised(self):
        client = MagicMock()
        client.auth.admin.sign_out.side_effect = RuntimeError("needs service_role key")
        service = AuthService(client=client)

        service.sign_out("token-123")  # must not raise


class TestPasswordReset:
    def test_calls_reset_password_for_email(self):
        client = MagicMock()
        service = AuthService(client=client)

        service.request_password_reset("a@b.com")

        client.auth.reset_password_for_email.assert_called_once_with("a@b.com", None)

    def test_with_redirect_to(self):
        client = MagicMock()
        service = AuthService(client=client)

        service.request_password_reset("a@b.com", redirect_to="https://app.example.com/reset")

        client.auth.reset_password_for_email.assert_called_once_with(
            "a@b.com", {"redirect_to": "https://app.example.com/reset"}
        )

    def test_failure_wrapped_as_auth_error(self):
        client = MagicMock()
        client.auth.reset_password_for_email.side_effect = RuntimeError("boom")
        service = AuthService(client=client)

        with pytest.raises(AuthError):
            service.request_password_reset("a@b.com")


class TestGetUser:
    def test_valid_token_returns_user(self):
        client = MagicMock()
        response = MagicMock()
        response.user = MagicMock(id="u1", email="a@b.com", user_metadata={"full_name": "Ada"})
        client.auth.get_user.return_value = response
        service = AuthService(client=client)

        user = service.get_user("valid-token")

        assert user is not None
        assert user.id == "u1"
        assert user.full_name == "Ada"

    def test_invalid_token_returns_none(self):
        client = MagicMock()
        client.auth.get_user.side_effect = RuntimeError("expired")
        service = AuthService(client=client)

        assert service.get_user("expired-token") is None

    def test_none_response_returns_none(self):
        client = MagicMock()
        client.auth.get_user.return_value = None
        service = AuthService(client=client)

        assert service.get_user("token") is None


class TestConfirmPasswordReset:
    def test_updates_password_via_admin_api_using_resolved_user_id(self):
        client = MagicMock()
        response = MagicMock()
        response.user = MagicMock(id="u1", email="a@b.com", user_metadata={})
        client.auth.get_user.return_value = response
        service = AuthService(client=client)
        admin_client = MagicMock()

        with patch("src.services.auth.auth_service.get_admin_client", return_value=admin_client):
            service.confirm_password_reset("recovery-token", "new-password123")

        admin_client.auth.admin.update_user_by_id.assert_called_once_with(
            "u1", {"password": "new-password123"}
        )

    def test_invalid_token_raises_auth_error_without_calling_admin_api(self):
        client = MagicMock()
        client.auth.get_user.side_effect = RuntimeError("expired")
        service = AuthService(client=client)
        admin_client = MagicMock()

        with patch("src.services.auth.auth_service.get_admin_client", return_value=admin_client):
            with pytest.raises(AuthError):
                service.confirm_password_reset("bad-token", "new-password123")

        admin_client.auth.admin.update_user_by_id.assert_not_called()

    def test_admin_api_failure_wrapped_as_auth_error(self):
        client = MagicMock()
        response = MagicMock()
        response.user = MagicMock(id="u1", email="a@b.com", user_metadata={})
        client.auth.get_user.return_value = response
        service = AuthService(client=client)
        admin_client = MagicMock()
        admin_client.auth.admin.update_user_by_id.side_effect = RuntimeError("boom")

        with patch("src.services.auth.auth_service.get_admin_client", return_value=admin_client):
            with pytest.raises(AuthError):
                service.confirm_password_reset("recovery-token", "new-password123")


class TestAdminCreateUser:
    def test_creates_pre_confirmed_user(self):
        client = MagicMock()
        client.auth.admin.create_user.return_value = MagicMock(
            user=MagicMock(id="u1", email="a@acme.com", user_metadata={"full_name": "Ada"})
        )
        service = AuthService(client=client)

        user = service.admin_create_user("a@acme.com", "password123", "Ada")

        assert user.id == "u1"
        assert user.full_name == "Ada"
        call_args = client.auth.admin.create_user.call_args[0][0]
        assert call_args["email"] == "a@acme.com"
        assert call_args["email_confirm"] is True
        assert call_args["user_metadata"] == {"full_name": "Ada"}

    def test_no_full_name_omits_user_metadata(self):
        client = MagicMock()
        client.auth.admin.create_user.return_value = MagicMock(
            user=MagicMock(id="u1", email="a@acme.com", user_metadata={})
        )
        service = AuthService(client=client)

        service.admin_create_user("a@acme.com", "password123")

        call_args = client.auth.admin.create_user.call_args[0][0]
        assert "user_metadata" not in call_args

    def test_supabase_exception_wrapped_as_auth_error(self):
        client = MagicMock()
        client.auth.admin.create_user.side_effect = RuntimeError("already registered")
        service = AuthService(client=client)

        with pytest.raises(AuthError, match="already registered"):
            service.admin_create_user("a@acme.com", "password123", "Ada")


class TestAdminInviteUser:
    def test_sends_invite_with_redirect_to(self):
        client = MagicMock()
        service = AuthService(client=client)

        service.admin_invite_user("teammate@acme.com", redirect_to="https://x/accept-invite")

        client.auth.admin.invite_user_by_email.assert_called_once_with(
            "teammate@acme.com", {"redirect_to": "https://x/accept-invite"}
        )

    def test_no_redirect_to_passes_none_options(self):
        client = MagicMock()
        service = AuthService(client=client)

        service.admin_invite_user("teammate@acme.com")

        client.auth.admin.invite_user_by_email.assert_called_once_with("teammate@acme.com", None)

    def test_supabase_exception_wrapped_as_auth_error(self):
        client = MagicMock()
        client.auth.admin.invite_user_by_email.side_effect = RuntimeError("rate limited")
        service = AuthService(client=client)

        with pytest.raises(AuthError, match="rate limited"):
            service.admin_invite_user("teammate@acme.com")
