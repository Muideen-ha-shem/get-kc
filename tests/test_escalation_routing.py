"""Tests for select_agent — first-available assignment."""

from __future__ import annotations

from src.services.agents.agent_models import SupportAgent
from src.services.escalation.routing import select_agent


def _agent(**overrides) -> SupportAgent:
    base = {
        "id": "a1", "workspace_id": "w1", "auth_user_id": "u1", "name": "Ada",
        "email": "ada@example.com", "department": "General", "status": "offline",
    }
    base.update(overrides)
    return SupportAgent(**base)


class TestSelectAgent:
    def test_returns_first_available(self):
        agents = [_agent(id="a1", status="offline"), _agent(id="a2", status="available"), _agent(id="a3", status="available")]
        selected = select_agent(agents)
        assert selected is not None
        assert selected.id == "a2"

    def test_empty_list_returns_none(self):
        assert select_agent([]) is None

    def test_all_unavailable_returns_none(self):
        agents = [_agent(status="away"), _agent(status="offline")]
        assert select_agent(agents) is None
