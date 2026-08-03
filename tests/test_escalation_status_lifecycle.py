"""Tests for the Phase 25 waiting_for_customer status transitions —
repository methods plus the message-send route's auto-flip-back-to-active
rule."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.deps import get_current_user_required, get_current_workspace
from src.services.agents.agent_models import SupportAgent
from src.services.auth.auth_service import AuthUser
from src.services.escalation.escalation_models import Escalation, EscalationMessage
from src.services.escalation.escalation_repository import EscalationRepository
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


def _escalation(**overrides) -> Escalation:
    base = {
        "id": "e1", "workspace_id": "w1", "conversation_id": None, "status": "active",
        "assigned_agent_id": "a1", "trigger_reason": "explicit_request", "department": "Support",
        "summary": None, "created_at": None, "assigned_at": None, "resolved_at": None, "closed_at": None,
        "ai_engaged": False,
    }
    base.update(overrides)
    return Escalation(**base)


class TestRepositoryTransitions:
    def test_set_waiting_for_customer_updates_status(self):
        client = MagicMock()
        client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            {"id": "e1", "workspace_id": "w1", "conversation_id": None, "status": "waiting_for_customer",
             "assigned_agent_id": "a1", "trigger_reason": "explicit_request", "department": "Support",
             "summary": None, "created_at": None, "assigned_at": None, "resolved_at": None, "closed_at": None,
             "ai_engaged": False}
        ]
        repo = EscalationRepository(client=client)

        updated = repo.set_waiting_for_customer("e1")

        assert updated.status == "waiting_for_customer"

    def test_set_active_scoped_to_waiting_for_customer_only(self):
        client = MagicMock()
        repo = EscalationRepository(client=client)

        repo.set_active("e1")

        client.table.return_value.update.return_value.eq.return_value.eq.assert_called_once_with(
            "status", "waiting_for_customer"
        )


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


class TestWaitForCustomerRoute:
    def test_requires_in_progress_status(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        app.dependency_overrides[get_current_workspace] = lambda: _FAKE_WORKSPACE
        with patch("src.api.routes.escalation._agent_service.get_by_auth_user_id", return_value=_agent()), \
             patch("src.api.routes.escalation._escalation_repository.get", return_value=_escalation(status="waiting")):
            response = client.post("/agent/escalations/e1/wait-for-customer")

        assert response.status_code == 409

    def test_transitions_active_to_waiting_for_customer(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        app.dependency_overrides[get_current_workspace] = lambda: _FAKE_WORKSPACE
        with patch("src.api.routes.escalation._agent_service.get_by_auth_user_id", return_value=_agent()), \
             patch("src.api.routes.escalation._escalation_repository.get", return_value=_escalation(status="active")), \
             patch(
                 "src.api.routes.escalation._escalation_repository.set_waiting_for_customer",
                 return_value=_escalation(status="waiting_for_customer"),
             ):
            response = client.post("/agent/escalations/e1/wait-for-customer")

        assert response.status_code == 200
        assert response.json()["status"] == "waiting_for_customer"


class TestMessageAutoFlipsBackToActive:
    def test_customer_message_calls_set_active(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        app.dependency_overrides[get_current_workspace] = lambda: _FAKE_WORKSPACE
        message_row = EscalationMessage(
            id="m1", escalation_id="e1", sender_type="customer", sender_auth_user_id="u2", content="hi"
        )
        with patch(
            "src.api.routes.escalation._escalation_repository.get",
            return_value=_escalation(status="waiting_for_customer", assigned_agent_id="a-other"),
        ), patch("src.api.routes.escalation._agent_service.get_by_auth_user_id", return_value=None), \
           patch("src.api.routes.escalation._escalation_repository.mark_active_if_first_message"), \
           patch("src.api.routes.escalation._escalation_repository.set_active") as mock_set_active, \
           patch("src.api.routes.escalation._escalation_repository.add_message", return_value=message_row):
            response = client.post("/agent/escalations/e1/messages", json={"content": "hi"})

        assert response.status_code == 200
        mock_set_active.assert_called_once_with("e1")

    def test_agent_message_does_not_call_set_active(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        app.dependency_overrides[get_current_workspace] = lambda: _FAKE_WORKSPACE
        message_row = EscalationMessage(
            id="m1", escalation_id="e1", sender_type="agent", sender_auth_user_id="u1", content="hi"
        )
        with patch(
            "src.api.routes.escalation._escalation_repository.get",
            return_value=_escalation(status="waiting_for_customer", assigned_agent_id="a1"),
        ), patch("src.api.routes.escalation._agent_service.get_by_auth_user_id", return_value=_agent()), \
           patch("src.api.routes.escalation._escalation_repository.mark_active_if_first_message"), \
           patch("src.api.routes.escalation._escalation_repository.set_active") as mock_set_active, \
           patch("src.api.routes.escalation._escalation_repository.add_message", return_value=message_row):
            response = client.post("/agent/escalations/e1/messages", json={"content": "hi"})

        assert response.status_code == 200
        mock_set_active.assert_not_called()
