"""Tests for GET /agent/dashboard/stats (Phase 25)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.deps import get_current_agent, get_current_user_required, get_current_workspace
from src.services.agents.agent_models import SupportAgent
from src.services.auth.auth_service import AuthUser
from src.services.escalation.escalation_models import Escalation
from src.services.workspace.workspace_context import WorkspaceContext

_FAKE_USER = AuthUser(id="u1", email="ada@example.com", full_name="Ada")
_FAKE_WORKSPACE = WorkspaceContext(workspace_id="w1", slug="acme", name="Acme")


def _agent(**overrides) -> SupportAgent:
    base = {
        "id": "a1", "workspace_id": "w1", "auth_user_id": "u1", "name": "Ada",
        "email": "ada@example.com", "department": "Support", "status": "available",
        "created_at": None, "updated_at": None,
    }
    base.update(overrides)
    return SupportAgent(**base)


def _resolved_escalation(created_at: str, resolved_at: str) -> Escalation:
    return Escalation(
        id="e1", workspace_id="w1", conversation_id=None, status="resolved",
        assigned_agent_id="a1", trigger_reason="explicit_request", department="Support",
        summary=None, created_at=created_at, assigned_at=None, resolved_at=resolved_at,
        closed_at=None, ai_engaged=False,
    )


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


class TestDashboardStats:
    def test_requires_registered_agent(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        with patch("src.api.deps._agent_service.get_by_auth_user_id_any_workspace", return_value=None):
            response = client.get("/agent/dashboard/stats")

        assert response.status_code == 404

    def test_returns_workload_and_average_resolution(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        app.dependency_overrides[get_current_agent] = lambda: _agent()
        resolved = [
            _resolved_escalation("2026-08-03T09:00:00+00:00", "2026-08-03T09:30:00+00:00"),
            _resolved_escalation("2026-08-03T10:00:00+00:00", "2026-08-03T10:10:00+00:00"),
        ]
        with patch("src.api.routes.escalation._escalation_repository.count_active_for_agent", return_value=3), \
             patch(
                 "src.api.routes.escalation._escalation_repository.list_resolved_today_for_agent",
                 return_value=resolved,
             ):
            response = client.get("/agent/dashboard/stats")

        assert response.status_code == 200
        body = response.json()
        assert body["current_workload"] == 3
        assert body["resolved_today"] == 2
        assert body["average_resolution_minutes"] == 20.0
        assert body["status"] == "available"
        assert body["department"] == "Support"
