"""Integration tests for /chat's workspace resolution (Phase 22).

Follows the dependency_overrides + patched-orchestrator pattern from
test_phase20_routes.py.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.deps import get_current_workspace
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
        app.dependency_overrides[get_current_workspace] = lambda: WorkspaceContext(
            workspace_id="ws-acme", slug="acme", name="Acme"
        )
        with patch("src.api.routes.chat.chat_orchestrator.process_request_response") as mock_process:
            from src.api.schemas import ChatResponse
            mock_process.return_value = ChatResponse(answer="ok", sources=[])

            client.post("/chat", json={"message": "hello"})

        assert mock_process.call_args.kwargs["workspace_id"] == "ws-acme"

    def test_default_workspace_id_used_when_dependency_falls_back(self, client):
        app.dependency_overrides[get_current_workspace] = lambda: WorkspaceContext(
            workspace_id=DEFAULT_WORKSPACE_ID, slug="ha-shem", name="Ha-Shem", is_default=True
        )
        with patch("src.api.routes.chat.chat_orchestrator.process_request_response") as mock_process:
            from src.api.schemas import ChatResponse
            mock_process.return_value = ChatResponse(answer="ok", sources=[])

            client.post("/chat", json={"message": "hello"})

        assert mock_process.call_args.kwargs["workspace_id"] == DEFAULT_WORKSPACE_ID
