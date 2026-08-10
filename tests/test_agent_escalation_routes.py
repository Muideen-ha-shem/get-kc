"""Integration tests for the Phase 24 agent/escalation routes — mirrors
test_chat_workspace_routes.py's dependency_overrides + patched-singleton
pattern.

Agent-identity routes (/agents/me, /agents/status, /agent/*) resolve via
get_current_agent (identity-based — see deps.py's docstring for why this
replaced get_current_workspace for these routes), so tests override that
dependency directly rather than get_current_workspace. /chat/escalate
stays on get_current_workspace since it's a customer-facing route.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.deps import get_current_agent, get_current_user_optional, get_current_user_required, get_current_workspace
from src.services.agents.agent_models import SupportAgent
from src.services.auth.auth_service import AuthUser
from src.services.escalation.escalation_models import Escalation
from src.services.workspace.workspace_context import WorkspaceContext

_FAKE_USER = AuthUser(id="u1", email="ada@example.com", full_name="Ada")
_FAKE_WORKSPACE = WorkspaceContext(workspace_id="w1", slug="acme", name="Acme")


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _agent(**overrides) -> SupportAgent:
    base = {
        "id": "a1", "workspace_id": "w1", "auth_user_id": "u1", "name": "Ada",
        "email": "ada@example.com", "department": "General", "status": "offline",
        "created_at": None, "updated_at": None,
    }
    base.update(overrides)
    return SupportAgent(**base)


def _authenticate():
    """For customer-facing routes still on get_current_workspace (/chat/escalate)."""
    app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
    app.dependency_overrides[get_current_user_optional] = lambda: _FAKE_USER
    app.dependency_overrides[get_current_workspace] = lambda: _FAKE_WORKSPACE


def _authenticate_as_agent(agent: SupportAgent | None = None):
    """For identity-based agent routes (/agents/me, /agents/status, /agent/*)."""
    app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
    app.dependency_overrides[get_current_user_optional] = lambda: _FAKE_USER
    app.dependency_overrides[get_current_agent] = lambda: agent or _agent()


def _escalation(**overrides) -> Escalation:
    base = {
        "id": "e1", "workspace_id": "w1", "conversation_id": None, "status": "waiting",
        "assigned_agent_id": None, "trigger_reason": "explicit_request", "department": None,
        "summary": {"customer": "Unknown", "workspace": "Acme", "intent": [], "sentiment": "neutral",
                     "products": [], "problem": "help", "actions_already_taken": [], "suggested_resolution": []},
        "created_at": None, "assigned_at": None, "resolved_at": None, "closed_at": None,
    }
    base.update(overrides)
    return Escalation(**base)


class TestAgentsRoutes:
    def test_agents_me_returns_existing_agent(self, client):
        _authenticate_as_agent(_agent())
        response = client.get("/agents/me")

        assert response.status_code == 200
        assert response.json()["id"] == "a1"

    def test_agents_me_404s_when_not_registered(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        with patch(
            "src.api.deps._agent_service.get_by_auth_user_id_any_workspace", return_value=None
        ):
            response = client.get("/agents/me")

        assert response.status_code == 404

    def test_update_status_returns_404_when_not_an_agent(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        with patch(
            "src.api.deps._agent_service.get_by_auth_user_id_any_workspace", return_value=None
        ):
            response = client.patch("/agents/status", json={"status": "available"})

        assert response.status_code == 404

    def test_update_status_updates_when_registered(self, client):
        _authenticate_as_agent(_agent())
        with patch("src.api.routes.agents._agent_service.update_status", return_value=_agent(status="available")):
            response = client.patch("/agents/status", json={"status": "available"})

        assert response.status_code == 200
        assert response.json()["status"] == "available"


class TestEscalationRoutes:
    def test_chat_escalate_creates_and_notifies(self, client):
        _authenticate()
        with patch(
            "src.api.routes.escalation._escalation_service.create_direct", return_value=_escalation()
        ) as mock_create:
            response = client.post("/chat/escalate", json={"question": "talk to a human", "conversation_id": None})

        assert response.status_code == 200
        assert response.json()["id"] == "e1"
        mock_create.assert_called_once()

    def test_agent_queue_requires_registered_agent(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        with patch(
            "src.api.deps._agent_service.get_by_auth_user_id_any_workspace", return_value=None
        ):
            response = client.get("/agent/queue")

        assert response.status_code == 404

    def test_agent_queue_scoped_to_workspace(self, client):
        _authenticate_as_agent(_agent())
        with patch(
            "src.api.routes.escalation._escalation_repository.list_waiting", return_value=[_escalation()]
        ) as mock_list:
            response = client.get("/agent/queue")

        assert response.status_code == 200
        assert len(response.json()) == 1
        mock_list.assert_called_once_with("w1")

    def test_accept_already_assigned_returns_409(self, client):
        _authenticate_as_agent(_agent())
        with patch(
            "src.api.routes.escalation._escalation_repository.get",
            return_value=_escalation(status="assigned"),
        ):
            response = client.post("/agent/accept", json={"escalation_id": "e1"})

        assert response.status_code == 409

    def test_accept_waiting_escalation_succeeds(self, client):
        _authenticate_as_agent(_agent())
        with patch("src.api.routes.escalation._escalation_repository.get", return_value=_escalation()), \
             patch(
                 "src.api.routes.escalation._escalation_repository.assign",
                 return_value=_escalation(status="assigned", assigned_agent_id="a1"),
             ) as mock_assign:
            response = client.post("/agent/accept", json={"escalation_id": "e1"})

        assert response.status_code == 200
        assert response.json()["status"] == "assigned"
        mock_assign.assert_called_once_with("e1", "a1")

    def test_resolve_requires_assigned_or_active(self, client):
        _authenticate_as_agent(_agent())
        with patch("src.api.routes.escalation._escalation_repository.get", return_value=_escalation(status="waiting")):
            response = client.post("/agent/resolve", json={"escalation_id": "e1"})

        assert response.status_code == 409

    def test_resolve_succeeds_when_active(self, client):
        _authenticate_as_agent(_agent())
        with patch("src.api.routes.escalation._escalation_repository.get", return_value=_escalation(status="active")), \
             patch(
                 "src.api.routes.escalation._escalation_repository.mark_resolved",
                 return_value=_escalation(status="resolved"),
             ):
            response = client.post("/agent/resolve", json={"escalation_id": "e1"})

        assert response.status_code == 200
        assert response.json()["status"] == "resolved"

    def test_message_transitions_to_active_on_first_message(self, client):
        _authenticate()
        message_row = MagicMock(
            id="m1", sender_type="agent", sender_auth_user_id="u1", content="hi", created_at=None
        )
        with patch(
            "src.api.routes.escalation._escalation_repository.get",
            return_value=_escalation(status="assigned", assigned_agent_id="a1"),
        ), patch(
            "src.api.routes.escalation._agent_service.get_by_auth_user_id_any_workspace", return_value=_agent()
        ), patch(
               "src.api.routes.escalation._escalation_repository.mark_active_if_first_message"
           ) as mock_mark_active, \
           patch(
               "src.api.routes.escalation._escalation_repository.add_message", return_value=message_row
           ) as mock_add:
            response = client.post("/agent/escalations/e1/messages", json={"content": "hi"})

        assert response.status_code == 200
        mock_mark_active.assert_called_once_with("e1")
        mock_add.assert_called_once_with("e1", "agent", "u1", "hi")
