"""Tests for EscalationService's Phase 25 auto-assignment: escalate() /
create_direct() now assign the best available agent immediately, falling
back to `waiting` (the Phase 24 queue) when none are available."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.services.agents.agent_models import SupportAgent
from src.services.escalation.escalation_models import Escalation
from src.services.escalation.escalation_service import EscalationService


def _agent(**overrides) -> SupportAgent:
    base = {
        "id": "a1", "workspace_id": "w1", "auth_user_id": "u1", "name": "Ada",
        "email": "ada@example.com", "department": "Support", "status": "available",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    base.update(overrides)
    return SupportAgent(**base)


def _escalation(**overrides) -> Escalation:
    base = {
        "id": "e1", "workspace_id": "w1", "conversation_id": None, "status": "waiting",
        "assigned_agent_id": None, "trigger_reason": "explicit_request", "department": "Support",
        "summary": {}, "created_at": None, "assigned_at": None, "resolved_at": None, "closed_at": None,
        "ai_engaged": True,
    }
    base.update(overrides)
    return Escalation(**base)


class TestAutoAssignment:
    def test_assigns_best_available_agent_on_creation(self):
        agent_service = MagicMock()
        agent_service.list_available.return_value = [_agent(id="a1")]
        repository = MagicMock()
        repository.create.return_value = _escalation()
        repository.count_active_for_agent.return_value = 0
        repository.assign.return_value = _escalation(status="assigned", assigned_agent_id="a1")
        notification_service = MagicMock()

        service = EscalationService(
            agent_service=agent_service, repository=repository, notification_service=notification_service
        )

        result = service.create_direct(
            workspace_id="w1", workspace_name="Acme", conversation_id=None, question="talk to a human"
        )

        assert result.status == "assigned"
        assert result.assigned_agent_id == "a1"
        repository.assign.assert_called_once_with("e1", "a1")

    def test_falls_back_to_waiting_when_no_agent_available(self):
        agent_service = MagicMock()
        agent_service.list_available.return_value = []
        repository = MagicMock()
        repository.create.return_value = _escalation()
        notification_service = MagicMock()

        service = EscalationService(
            agent_service=agent_service, repository=repository, notification_service=notification_service
        )

        result = service.create_direct(
            workspace_id="w1", workspace_name="Acme", conversation_id=None, question="talk to a human"
        )

        assert result.status == "waiting"
        repository.assign.assert_not_called()

    def test_notifies_every_available_agent_regardless_of_who_is_assigned(self):
        agent_service = MagicMock()
        agent_service.list_available.return_value = [_agent(id="a1"), _agent(id="a2")]
        repository = MagicMock()
        repository.create.return_value = _escalation()
        repository.count_active_for_agent.return_value = 0
        repository.assign.return_value = _escalation(status="assigned", assigned_agent_id="a1")
        notification_service = MagicMock()

        service = EscalationService(
            agent_service=agent_service, repository=repository, notification_service=notification_service
        )

        service.create_direct(
            workspace_id="w1", workspace_name="Acme", conversation_id=None, question="talk to a human"
        )

        assert notification_service.notify.call_count == 2

    def test_department_computed_and_passed_to_create(self):
        agent_service = MagicMock()
        agent_service.list_available.return_value = []
        repository = MagicMock()
        repository.create.return_value = _escalation()
        notification_service = MagicMock()

        service = EscalationService(
            agent_service=agent_service, repository=repository, notification_service=notification_service
        )

        service.create_direct(
            workspace_id="w1", workspace_name="Acme", conversation_id=None, question="I was overcharged"
        )

        repository.create.assert_called_once_with("w1", None, "explicit_request", "Finance", {
            "customer": "Unknown", "workspace": "Acme", "intent": [], "sentiment": "neutral",
            "products": [], "problem": "I was overcharged", "actions_already_taken": [],
            "suggested_resolution": [],
        })
