"""Tests for internal escalation notes (Phase 25) — repository + route."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.deps import get_current_user_optional, get_current_user_required, get_current_workspace
from src.services.agents.agent_models import SupportAgent
from src.services.auth.auth_service import AuthUser
from src.services.escalation.escalation_models import Escalation, EscalationNote
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


class TestEscalationNotesRepository:
    def test_add_note_inserts_and_returns_row(self):
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "n1", "escalation_id": "e1", "workspace_id": "w1", "author_agent_id": "a1",
             "content": "VIP customer", "created_at": None}
        ]
        repo = EscalationRepository(client=client)

        note = repo.add_note("w1", "e1", "a1", "VIP customer")

        assert isinstance(note, EscalationNote)
        assert note.content == "VIP customer"

    def test_list_notes_orders_by_created_at(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
        repo = EscalationRepository(client=client)

        repo.list_notes("e1")

        client.table.return_value.select.return_value.eq.return_value.order.assert_called_once_with("created_at")


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


class TestEscalationNotesRoute:
    def test_add_note_requires_registered_agent(self):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        app.dependency_overrides[get_current_workspace] = lambda: _FAKE_WORKSPACE
        with patch("src.api.routes.escalation._agent_service.get_by_auth_user_id", return_value=None):
            response = TestClient(app).post("/agent/escalations/e1/notes", json={"content": "note"})

        assert response.status_code == 404

    def test_add_note_succeeds_for_registered_agent(self):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        app.dependency_overrides[get_current_workspace] = lambda: _FAKE_WORKSPACE
        note = EscalationNote(id="n1", escalation_id="e1", workspace_id="w1", author_agent_id="a1", content="note")
        with patch("src.api.routes.escalation._agent_service.get_by_auth_user_id", return_value=_agent()), \
             patch("src.api.routes.escalation._escalation_repository.get", return_value=_escalation()), \
             patch("src.api.routes.escalation._escalation_repository.add_note", return_value=note) as mock_add:
            response = TestClient(app).post("/agent/escalations/e1/notes", json={"content": "note"})

        assert response.status_code == 200
        assert response.json()["content"] == "note"
        mock_add.assert_called_once_with("w1", "e1", "a1", "note")

    def test_detail_endpoint_inlines_notes(self):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        app.dependency_overrides[get_current_workspace] = lambda: _FAKE_WORKSPACE
        note = EscalationNote(id="n1", escalation_id="e1", workspace_id="w1", author_agent_id="a1", content="note")
        with patch("src.api.routes.escalation._agent_service.get_by_auth_user_id", return_value=_agent()), \
             patch("src.api.routes.escalation._escalation_repository.get", return_value=_escalation()), \
             patch("src.api.routes.escalation._escalation_repository.list_messages", return_value=[]), \
             patch("src.api.routes.escalation._escalation_repository.list_notes", return_value=[note]):
            response = TestClient(app).get("/agent/escalations/e1")

        assert response.status_code == 200
        assert response.json()["notes"][0]["content"] == "note"
