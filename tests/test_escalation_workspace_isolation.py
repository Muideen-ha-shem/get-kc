"""Cross-tenant isolation checks for agents/escalations (Phase 24) — mirrors
test_cross_workspace_isolation.py's style. All Supabase calls mocked."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.services.agents.agent_repository import AgentRepository
from src.services.escalation.escalation_repository import EscalationRepository


class TestAgentWorkspaceIsolation:
    def test_list_available_scopes_to_requested_workspace(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = []
        repo = AgentRepository(client=client)

        repo.list_available("workspace-a")

        client.table.return_value.select.return_value.eq.assert_called_once_with("workspace_id", "workspace-a")

    def test_list_by_workspace_never_mixes_workspaces(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            {"id": "a1", "workspace_id": "workspace-a", "auth_user_id": "u1", "name": "Ada",
             "email": "a@x.com", "department": "General", "status": "available",
             "created_at": None, "updated_at": None}
        ]
        repo = AgentRepository(client=client)

        agents = repo.list_by_workspace("workspace-a")

        assert all(a.workspace_id == "workspace-a" for a in agents)
        client.table.return_value.select.return_value.eq.assert_called_once_with("workspace_id", "workspace-a")


class TestEscalationWorkspaceIsolation:
    def test_list_waiting_scopes_to_requested_workspace(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = []
        repo = EscalationRepository(client=client)

        repo.list_waiting("workspace-b")

        client.table.return_value.select.return_value.eq.assert_called_once_with("workspace_id", "workspace-b")
