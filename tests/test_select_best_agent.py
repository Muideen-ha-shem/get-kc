"""Tests for select_best_agent — workload + idle-time ordering, department
preference, edge cases."""

from __future__ import annotations

from src.services.agents.agent_models import SupportAgent
from src.services.escalation.routing import select_best_agent


def _agent(**overrides) -> SupportAgent:
    base = {
        "id": "a1", "workspace_id": "w1", "auth_user_id": "u1", "name": "Ada",
        "email": "ada@example.com", "department": "Support", "status": "available",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    base.update(overrides)
    return SupportAgent(**base)


class TestSelectBestAgent:
    def test_lowest_workload_wins(self):
        agents = [_agent(id="a1"), _agent(id="a2")]
        workloads = {"a1": 3, "a2": 1}
        assert select_best_agent(agents, workloads).id == "a2"

    def test_ties_broken_by_oldest_idle(self):
        agents = [
            _agent(id="a1", updated_at="2026-01-02T00:00:00Z"),
            _agent(id="a2", updated_at="2026-01-01T00:00:00Z"),
        ]
        workloads = {"a1": 0, "a2": 0}
        assert select_best_agent(agents, workloads).id == "a2"

    def test_unavailable_agents_excluded(self):
        agents = [_agent(id="a1", status="offline"), _agent(id="a2", status="available")]
        assert select_best_agent(agents, {}).id == "a2"

    def test_empty_list_returns_none(self):
        assert select_best_agent([], {}) is None

    def test_department_preference_used_when_match_exists(self):
        agents = [
            _agent(id="a1", department="Sales", updated_at="2026-01-01T00:00:00Z"),
            _agent(id="a2", department="Support", updated_at="2026-01-02T00:00:00Z"),
        ]
        selected = select_best_agent(agents, {}, department="Support")
        assert selected.id == "a2"

    def test_department_preference_falls_back_when_no_match(self):
        agents = [_agent(id="a1", department="Sales")]
        selected = select_best_agent(agents, {}, department="Finance")
        assert selected.id == "a1"

    def test_no_workload_entry_defaults_to_zero(self):
        agents = [_agent(id="a1"), _agent(id="a2")]
        workloads = {"a1": 5}
        assert select_best_agent(agents, workloads).id == "a2"
