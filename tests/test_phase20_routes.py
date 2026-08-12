"""Integration tests for Phase 20 routes — auth, profile, conversations,
and the updated /chat contract (anonymous + authenticated + persistence).

Auth is faked via FastAPI's dependency_overrides (the documented way to
swap a Depends() callable in tests) rather than hitting real Supabase.
Service-layer calls are patched at the module the route imports them from.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.deps import (
    get_current_access_token_required,
    get_current_user_optional,
    get_current_user_required,
)
from src.services.auth.auth_service import AuthUser
from src.services.workspace.workspace_models import DEFAULT_WORKSPACE_ID


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


_FAKE_USER = AuthUser(id="u1", email="a@b.com", full_name="Ada")


# ---------------------------------------------------------------------------
# /chat — backward compatibility + new optional fields
# ---------------------------------------------------------------------------


class TestChatBackwardCompatibility:
    def test_anonymous_request_without_session_id_still_works(self, client):
        with patch("src.api.routes.chat.chat_orchestrator.process_request_response") as mock_process:
            from src.api.schemas import ChatResponse
            mock_process.return_value = ChatResponse(answer="ok", sources=[], session_id="generated-1")

            response = client.post("/chat", json={"message": "hello"})

        assert response.status_code == 200
        body = response.json()
        assert body["answer"] == "ok"
        assert body["session_id"] == "generated-1"
        mock_process.assert_called_once_with(
            "hello", session_id=None, profile_context=None, workspace_id=DEFAULT_WORKSPACE_ID,
            workspace_name="Ha-Shem Limited", workspace_welcome_message="Welcome to Ha-Shem — how can HavisIQ help today?",
            handoff_context=None,
        )

    def test_old_style_request_without_new_fields_is_accepted(self, client):
        with patch("src.api.routes.chat.chat_orchestrator.process_request_response") as mock_process:
            from src.api.schemas import ChatResponse
            mock_process.return_value = ChatResponse(answer="ok", sources=[])

            response = client.post("/chat", json={"message": "hello"})

        assert response.status_code == 200
        assert response.json()["session_id"] is None


class TestChatSessionIdPassthrough:
    def test_session_id_forwarded_to_orchestrator(self, client):
        with patch("src.api.routes.chat.chat_orchestrator.process_request_response") as mock_process:
            from src.api.schemas import ChatResponse
            mock_process.return_value = ChatResponse(answer="ok", sources=[], session_id="s1")

            client.post("/chat", json={"message": "How much does it cost?", "session_id": "s1"})

        mock_process.assert_called_once_with(
            "How much does it cost?", session_id="s1", profile_context=None,
            workspace_id=DEFAULT_WORKSPACE_ID,
            workspace_name="Ha-Shem Limited", workspace_welcome_message="Welcome to Ha-Shem — how can HavisIQ help today?",
            handoff_context=None,
        )


class TestChatAuthenticatedPersonalizationAndPersistence:
    def test_authenticated_user_gets_profile_context(self, client):
        app.dependency_overrides[get_current_user_optional] = lambda: _FAKE_USER
        fake_profile = MagicMock(company_name="ABC Bank", industry="Financial Services")

        with patch("src.api.routes.chat._profile_service.get_by_auth_user_id", return_value=fake_profile), \
             patch("src.api.routes.chat.chat_orchestrator.process_request_response") as mock_process:
            from src.api.schemas import ChatResponse
            mock_process.return_value = ChatResponse(answer="ok", sources=[])

            client.post("/chat", json={"message": "We need customer onboarding"})

        kwargs = mock_process.call_args.kwargs
        assert kwargs["profile_context"] == "ABC Bank — Financial Services"

    def test_conversation_persistence_triggered_when_conversation_id_present(self, client):
        app.dependency_overrides[get_current_user_optional] = lambda: _FAKE_USER

        with patch("src.api.routes.chat.chat_orchestrator.process_request_response") as mock_process, \
             patch("src.api.routes.chat._profile_service.get_by_auth_user_id", return_value=None), \
             patch("src.api.routes.chat._conversation_service.record_turn") as mock_record:
            from src.api.schemas import ChatResponse
            mock_process.return_value = ChatResponse(answer="ok answer", sources=["https://x.com"])

            client.post("/chat", json={"message": "hi", "conversation_id": "c1"})

        mock_record.assert_called_once()
        args = mock_record.call_args[0]
        assert args[0] == "c1"
        assert args[1] == "u1"

    def test_persistence_failure_never_breaks_chat_response(self, client):
        app.dependency_overrides[get_current_user_optional] = lambda: _FAKE_USER

        with patch("src.api.routes.chat.chat_orchestrator.process_request_response") as mock_process, \
             patch("src.api.routes.chat._profile_service.get_by_auth_user_id", return_value=None), \
             patch("src.api.routes.chat._conversation_service.record_turn", side_effect=RuntimeError("db down")):
            from src.api.schemas import ChatResponse
            mock_process.return_value = ChatResponse(answer="ok", sources=[])

            response = client.post("/chat", json={"message": "hi", "conversation_id": "c1"})

        assert response.status_code == 200
        assert response.json()["answer"] == "ok"

    def test_anonymous_with_conversation_id_does_not_persist(self, client):
        with patch("src.api.routes.chat.chat_orchestrator.process_request_response") as mock_process, \
             patch("src.api.routes.chat._conversation_service.record_turn") as mock_record:
            from src.api.schemas import ChatResponse
            mock_process.return_value = ChatResponse(answer="ok", sources=[])

            client.post("/chat", json={"message": "hi", "conversation_id": "c1"})

        mock_record.assert_not_called()


# ---------------------------------------------------------------------------
# /auth
# ---------------------------------------------------------------------------


class TestAuthRoutes:
    def test_sign_up_returns_session(self, client):
        from src.services.auth.auth_service import AuthSession

        session = AuthSession(access_token="tok", refresh_token="ref", user=_FAKE_USER)
        with patch("src.api.routes.auth._auth_service.sign_up", return_value=session), \
             patch("src.api.routes.auth._profile_service.get_or_create"):
            response = client.post(
                "/auth/sign-up", json={"email": "a@b.com", "password": "password123", "full_name": "Ada"}
            )

        assert response.status_code == 200
        assert response.json()["access_token"] == "tok"

    def test_sign_up_invalid_email_rejected_before_hitting_service(self, client):
        response = client.post("/auth/sign-up", json={"email": "not-an-email", "password": "password123"})
        assert response.status_code == 422

    def test_sign_in_bad_credentials_returns_401(self, client):
        from src.services.auth.auth_service import AuthError

        with patch("src.api.routes.auth._auth_service.sign_in", side_effect=AuthError("Invalid email or password")):
            response = client.post("/auth/sign-in", json={"email": "a@b.com", "password": "wrong"})

        assert response.status_code == 401

    def test_sign_out_always_returns_200_even_without_token(self, client):
        response = client.post("/auth/sign-out")
        assert response.status_code == 200

    def test_password_reset_returns_200(self, client):
        with patch("src.api.routes.auth._auth_service.request_password_reset"):
            response = client.post("/auth/password-reset", json={"email": "a@b.com"})
        assert response.status_code == 200

    def test_password_reset_passes_redirect_to_frontend_reset_page(self, client):
        with patch("src.api.routes.auth._auth_service.request_password_reset") as mock_reset:
            client.post("/auth/password-reset", json={"email": "a@b.com"})
        assert mock_reset.call_args.kwargs["redirect_to"].endswith("/reset-password")

    def test_update_password_returns_200(self, client):
        with patch("src.api.routes.auth._auth_service.confirm_password_reset"):
            response = client.post(
                "/auth/update-password",
                json={"access_token": "recovery-token", "new_password": "new-password123"},
            )
        assert response.status_code == 200

    def test_update_password_invalid_token_returns_400(self, client):
        from src.services.auth.auth_service import AuthError

        with patch(
            "src.api.routes.auth._auth_service.confirm_password_reset",
            side_effect=AuthError("This reset link is invalid or has expired."),
        ):
            response = client.post(
                "/auth/update-password",
                json={"access_token": "bad-token", "new_password": "new-password123"},
            )
        assert response.status_code == 400

    def test_me_without_token_returns_401(self, client):
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_me_with_valid_override_returns_user(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        response = client.get("/auth/me")
        assert response.status_code == 200
        assert response.json()["id"] == "u1"


# ---------------------------------------------------------------------------
# /profile
# ---------------------------------------------------------------------------


class TestProfileRoutes:
    def test_get_profile_requires_auth(self, client):
        response = client.get("/profile")
        assert response.status_code == 401

    def test_get_profile_returns_data_for_authenticated_user(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        app.dependency_overrides[get_current_access_token_required] = lambda: "token-1"
        fake_profile = MagicMock(
            id="p1", email="a@b.com", full_name="Ada", company_name=None, industry=None, phone=None,
        )
        with patch("src.api.routes.profile._profile_service.get_or_create", return_value=fake_profile):
            response = client.get("/profile")

        assert response.status_code == 200
        assert response.json()["email"] == "a@b.com"

    def test_update_profile_requires_auth(self, client):
        response = client.patch("/profile", json={"company_name": "Acme"})
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# /conversations
# ---------------------------------------------------------------------------


class TestConversationRoutes:
    def test_list_conversations_requires_auth(self, client):
        response = client.get("/conversations")
        assert response.status_code == 401

    def test_list_conversations_for_authenticated_user(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        app.dependency_overrides[get_current_access_token_required] = lambda: "token-1"
        row = MagicMock(id="c1", title="New conversation", created_at=None, updated_at=None)
        with patch("src.api.routes.conversations._conversation_service.list_conversations", return_value=[row]):
            response = client.get("/conversations")

        assert response.status_code == 200
        assert response.json()[0]["id"] == "c1"

    def test_get_missing_conversation_returns_404(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        app.dependency_overrides[get_current_access_token_required] = lambda: "token-1"
        with patch("src.api.routes.conversations._conversation_service.get_conversation", return_value=None):
            response = client.get("/conversations/c-missing")

        assert response.status_code == 404

    def test_delete_missing_conversation_returns_404(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        app.dependency_overrides[get_current_access_token_required] = lambda: "token-1"
        with patch("src.api.routes.conversations._conversation_service.delete_conversation", return_value=False):
            response = client.delete("/conversations/c-missing")

        assert response.status_code == 404

    def test_create_conversation(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        app.dependency_overrides[get_current_access_token_required] = lambda: "token-1"
        row = MagicMock(id="c1", title="New conversation", created_at=None, updated_at=None)
        with patch("src.api.routes.conversations._conversation_service.start_conversation", return_value=row):
            response = client.post("/conversations", json={})

        assert response.status_code == 200
        assert response.json()["id"] == "c1"
