"""Integration tests for /chat's workspace resolution (Phase 22, extended
for the identity-first fix — see get_current_chat_workspace's docstring).

Follows the dependency_overrides + patched-orchestrator pattern from
test_phase20_routes.py.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.deps import get_current_chat_workspace, get_current_user_optional
from src.services.auth.auth_service import AuthUser
from src.services.workspace.workspace_context import WorkspaceContext
from src.services.workspace.workspace_models import DEFAULT_WORKSPACE_ID


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


class TestChatWorkspaceBackwardCompatibility:
    def test_omitting_all_workspace_signals_still_returns_200(self, client):
        """No override at all — resolve_workspace() must fail open to the
        default workspace rather than erroring the request."""
        with patch("src.api.routes.chat.chat_orchestrator.process_request_response") as mock_process:
            from src.api.schemas import ChatResponse
            mock_process.return_value = ChatResponse(answer="ok", sources=[])

            response = client.post("/chat", json={"message": "hello"})

        assert response.status_code == 200
        assert response.json()["answer"] == "ok"

    def test_resolved_workspace_id_is_forwarded_to_orchestrator(self, client):
        app.dependency_overrides[get_current_chat_workspace] = lambda: WorkspaceContext(
            workspace_id="ws-acme", slug="acme", name="Acme"
        )
        with patch("src.api.routes.chat.chat_orchestrator.process_request_response") as mock_process:
            from src.api.schemas import ChatResponse
            mock_process.return_value = ChatResponse(answer="ok", sources=[])

            client.post("/chat", json={"message": "hello"})

        assert mock_process.call_args.kwargs["workspace_id"] == "ws-acme"

    def test_default_workspace_id_used_when_dependency_falls_back(self, client):
        app.dependency_overrides[get_current_chat_workspace] = lambda: WorkspaceContext(
            workspace_id=DEFAULT_WORKSPACE_ID, slug="ha-shem", name="Ha-Shem", is_default=True
        )
        with patch("src.api.routes.chat.chat_orchestrator.process_request_response") as mock_process:
            from src.api.schemas import ChatResponse
            mock_process.return_value = ChatResponse(answer="ok", sources=[])

            client.post("/chat", json={"message": "hello"})

        assert mock_process.call_args.kwargs["workspace_id"] == DEFAULT_WORKSPACE_ID


class TestChatWorkspaceIdentityFirstResolution:
    """Regression coverage for the cross-tenant leak: a signed-in customer
    with no workspace-identifying request signal must be resolved to
    *their own* workspace (via customer_profiles), not silently fall
    through to the default Ha-Shem workspace."""

    def test_authenticated_customer_with_no_request_signals_uses_own_workspace(self, client):
        fake_user = AuthUser(id="u1", email="a@greenbank.test", full_name="Ada")
        fake_profile = MagicMock(workspace_id="greenbank-ws-id")
        fake_workspace = MagicMock(id="greenbank-ws-id", is_active=True)
        app.dependency_overrides[get_current_user_optional] = lambda: fake_user

        with patch(
            "src.api.deps._profile_service.get_by_auth_user_id", return_value=fake_profile
        ), patch(
            "src.api.deps._workspace_repository.get_by_id", return_value=fake_workspace
        ), patch("src.api.routes.chat.chat_orchestrator.process_request_response") as mock_process:
            from src.api.schemas import ChatResponse
            mock_process.return_value = ChatResponse(answer="ok", sources=[])

            client.post("/chat", json={"message": "hello"})

        assert mock_process.call_args.kwargs["workspace_id"] == "greenbank-ws-id"

    def test_anonymous_request_unaffected_falls_through_to_lenient_resolution(self, client):
        """No user at all (public widget) — must behave exactly like
        get_current_workspace always has, proving the widget path is
        untouched by this fix."""
        with patch("src.api.routes.chat.chat_orchestrator.process_request_response") as mock_process:
            from src.api.schemas import ChatResponse
            mock_process.return_value = ChatResponse(answer="ok", sources=[])

            response = client.post("/chat", json={"message": "hello"})

        assert response.status_code == 200
        assert mock_process.call_args.kwargs["workspace_id"] == DEFAULT_WORKSPACE_ID
