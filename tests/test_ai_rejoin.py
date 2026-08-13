"""Tests for Phase 25's AI Rejoin: ChatRequest.handoff_context reaching
advisory_question (mirrors test_chat_orchestrator_session.py's
profile_context tests exactly), plus the rejoin-ai route."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.deps import get_current_agent, get_current_user_required, get_current_workspace
from src.orchestrator.chat_orchestrator import ChatOrchestrator
from src.services.advisory.advisory_layer import AdvisoryResult
from src.services.advisory.intent_engine import BusinessIntent
from src.services.agents.agent_models import SupportAgent
from src.services.auth.auth_service import AuthUser
from src.services.escalation.escalation_models import Escalation, EscalationMessage
from src.services.routing.source_router import RoutingDecision
from src.services.workspace.workspace_context import WorkspaceContext

_FAKE_USER = AuthUser(id="u1", email="ada@example.com", full_name="Ada")
_FAKE_WORKSPACE = WorkspaceContext(workspace_id="w1", slug="acme", name="Acme")


def _make_orchestrator(*, advisory_layer=None, evidence=None):
    if advisory_layer is not None:
        # MagicMock() auto-creates attributes returning a truthy MagicMock
        # by default — without this, ChatOrchestrator's zero-signal guard
        # clause would incorrectly short-circuit every test here that
        # passes a mocked advisory_layer.
        advisory_layer.check_zero_signal.return_value = None

    source_router = MagicMock()
    source_router.route.return_value = RoutingDecision(knowledge=True, web=False)

    search_manager = MagicMock()
    search_manager.retrieve.return_value = evidence or []
    search_manager.product_match = None
    search_manager.kb_confidence = 0.9

    response_generator = MagicMock()
    response_generator.generate.return_value = {"answer": "Answer.", "citations": []}

    return ChatOrchestrator(
        source_router=source_router,
        search_manager=search_manager,
        response_generator=response_generator,
        advisory_layer=advisory_layer,
    ), search_manager, response_generator


class TestHandoffContextThreading:
    def test_handoff_context_prefixed_onto_advisory_question(self):
        mock_advisory = MagicMock()
        mock_advisory.build.return_value = AdvisoryResult(intent=BusinessIntent(question="q"))
        orchestrator, search_manager, response_generator = _make_orchestrator(advisory_layer=mock_advisory)

        orchestrator.chat("Is this still broken?", handoff_context="Customer discussed a login issue with Ada.")

        advisory_question = mock_advisory.build.call_args[0][0]
        assert advisory_question.startswith("Customer discussed a login issue with Ada.")
        assert "Is this still broken?" in advisory_question

        retrieved_question = search_manager.retrieve.call_args[0][0]
        assert retrieved_question == "Is this still broken?"

    def test_no_handoff_context_leaves_advisory_question_unchanged(self):
        mock_advisory = MagicMock()
        mock_advisory.build.return_value = AdvisoryResult(intent=BusinessIntent(question="q"))
        orchestrator, _, _ = _make_orchestrator(advisory_layer=mock_advisory)

        orchestrator.chat("Is this still broken?")

        advisory_question = mock_advisory.build.call_args[0][0]
        assert advisory_question == "Is this still broken?"

    def test_both_profile_and_handoff_context_combine(self):
        mock_advisory = MagicMock()
        mock_advisory.build.return_value = AdvisoryResult(intent=BusinessIntent(question="q"))
        orchestrator, _, _ = _make_orchestrator(advisory_layer=mock_advisory)

        orchestrator.chat(
            "Is this still broken?",
            profile_context="ABC Bank",
            handoff_context="Customer discussed a login issue with Ada.",
        )

        advisory_question = mock_advisory.build.call_args[0][0]
        assert advisory_question.startswith("Customer discussed a login issue with Ada.")
        assert "ABC Bank" in advisory_question
        assert "Is this still broken?" in advisory_question


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
        "email": "ada@example.com", "department": "General", "status": "available",
        "created_at": None, "updated_at": None,
    }
    base.update(overrides)
    return SupportAgent(**base)


def _escalation(**overrides) -> Escalation:
    base = {
        "id": "e1", "workspace_id": "w1", "conversation_id": None, "status": "active",
        "assigned_agent_id": "a1", "trigger_reason": "explicit_request", "department": "Support",
        "summary": {"customer": "Unknown", "workspace": "Acme", "intent": [], "sentiment": "neutral",
                     "products": [], "problem": "Login issue", "actions_already_taken": [],
                     "suggested_resolution": []},
        "created_at": None, "assigned_at": None, "resolved_at": None, "closed_at": None,
        "ai_engaged": False,
    }
    base.update(overrides)
    return Escalation(**base)


class TestRejoinAiRoute:
    def test_rejoin_marks_resolved_and_returns_recap(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        app.dependency_overrides[get_current_agent] = lambda: _agent()
        message = EscalationMessage(
            id="m1", escalation_id="e1", sender_type="agent", sender_auth_user_id="u1", content="I fixed it"
        )
        with patch("src.api.routes.escalation._escalation_repository.get", return_value=_escalation()), \
             patch("src.api.routes.escalation._escalation_repository.list_messages", return_value=[message]), \
             patch("src.api.routes.escalation._escalation_repository.list_notes", return_value=[]), \
             patch(
                 "src.api.routes.escalation._escalation_repository.mark_resolved",
                 return_value=_escalation(status="resolved"),
             ), patch(
                 "src.api.routes.escalation._escalation_repository.set_ai_engaged",
                 return_value=_escalation(status="resolved", ai_engaged=True),
             ) as mock_set_ai_engaged, patch(
                 "src.api.routes.escalation._escalation_repository.merge_summary",
                 return_value=_escalation(status="resolved", ai_engaged=True),
             ):
            response = client.post("/agent/escalations/e1/rejoin-ai")

        assert response.status_code == 200
        body = response.json()
        assert body["escalation"]["status"] == "resolved"
        assert "Login issue" in body["handoff_recap"]
        assert "I fixed it" in body["handoff_recap"]
        mock_set_ai_engaged.assert_called_once_with("e1", True)
