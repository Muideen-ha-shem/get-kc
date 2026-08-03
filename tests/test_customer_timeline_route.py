"""Tests for GET /agent/customers/{id}/timeline (Phase 25)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.deps import get_current_user_required, get_current_workspace
from src.services.agents.agent_models import SupportAgent
from src.services.auth.auth_service import AuthUser
from src.services.workspace.workspace_context import WorkspaceContext

_FAKE_USER = AuthUser(id="u1", email="ada@example.com", full_name="Ada")
_FAKE_WORKSPACE = WorkspaceContext(workspace_id="w1", slug="acme", name="Acme")


def _agent(**overrides) -> SupportAgent:
    base = {
        "id": "a1", "workspace_id": "w1", "auth_user_id": "u1", "name": "Ada",
        "email": "ada@example.com", "department": "General", "status": "available",
        "created_at": None, "updated_at": None,
    }
    base.update(overrides)
    return SupportAgent(**base)


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


class TestCustomerTimelineRoute:
    def test_requires_registered_agent(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        app.dependency_overrides[get_current_workspace] = lambda: _FAKE_WORKSPACE
        with patch("src.api.routes.escalation._agent_service.get_by_auth_user_id", return_value=None):
            response = client.get("/agent/customers/u2/timeline")

        assert response.status_code == 404

    def test_returns_aggregated_timeline(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        app.dependency_overrides[get_current_workspace] = lambda: _FAKE_WORKSPACE
        fake_timeline = {
            "profile": None,
            "conversations": [],
            "saved_recommendations": [],
            "saved_comparisons": [],
            "appointments": [],
            "past_escalations": [],
            "demo_requests": [],
            "demo_requests_note": "Matched by email only — demo_requests has no direct customer link.",
        }
        with patch("src.api.routes.escalation._agent_service.get_by_auth_user_id", return_value=_agent()), \
             patch("src.api.routes.escalation.build_customer_timeline", return_value=fake_timeline) as mock_build:
            response = client.get("/agent/customers/u2/timeline")

        assert response.status_code == 200
        body = response.json()
        assert body["profile"] is None
        assert body["conversations"] == []
        assert "demo_requests_note" in body
        mock_build.assert_called_once_with("u2")
