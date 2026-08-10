"""Tests for AgentRepository (mocked Supabase) and AgentService (mocked
repository) — mirrors test_profile_service.py's pattern."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.services.agents.agent_repository import AgentRepository
from src.services.agents.agent_service import AgentService


def _row(**overrides):
    base = {
        "id": "a1", "workspace_id": "w1", "auth_user_id": "u1", "name": "Ada",
        "email": "ada@example.com", "department": "General", "status": "offline",
        "created_at": None, "updated_at": None,
    }
    base.update(overrides)
    return base


class TestAgentRepository:
    def test_get_or_create_returns_existing_without_inserting(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            _row()
        ]
        repo = AgentRepository(client=client)

        agent = repo.get_or_create("u1", "ada@example.com", "Ada", "w1")

        assert agent.id == "a1"
        client.table.return_value.insert.assert_not_called()

    def test_get_or_create_creates_when_missing(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        client.table.return_value.insert.return_value.execute.return_value.data = [_row(department="Sales")]
        repo = AgentRepository(client=client)

        agent = repo.get_or_create("u1", "ada@example.com", "Ada", "w1", department="Sales")

        assert agent.department == "Sales"
        client.table.return_value.insert.assert_called_once()

    def test_list_available_filters_by_workspace_and_status(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            _row(status="available")
        ]
        repo = AgentRepository(client=client)

        agents = repo.list_available("w1")

        assert len(agents) == 1
        client.table.return_value.select.return_value.eq.return_value.eq.assert_called_once_with(
            "status", "available"
        )

    def test_update_status_updates_row(self):
        client = MagicMock()
        client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            _row(status="available")
        ]
        repo = AgentRepository(client=client)

        agent = repo.update_status("a1", "available")

        assert agent.status == "available"


class TestAgentService:
    def test_list_available_delegates_to_repository(self):
        repo = MagicMock()
        repo.list_available.return_value = []
        service = AgentService(repository=repo)

        service.list_available("w1")

        repo.list_available.assert_called_once_with("w1")

    def test_get_or_create_delegates_to_repository(self):
        repo = MagicMock()
        service = AgentService(repository=repo)

        service.get_or_create("u1", "ada@example.com", "Ada", "w1")

        repo.get_or_create.assert_called_once_with("u1", "ada@example.com", "Ada", "w1", department="General")
