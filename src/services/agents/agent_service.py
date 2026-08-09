"""AgentService — thin facade over AgentRepository (Phase 24)."""

from __future__ import annotations

from .agent_models import SupportAgent
from .agent_repository import AgentRepository


class AgentService:
    def __init__(self, repository: AgentRepository | None = None) -> None:
        self._repo = repository or AgentRepository()

    def get_by_auth_user_id(self, auth_user_id: str, workspace_id: str) -> SupportAgent | None:
        return self._repo.get_by_auth_user_id(auth_user_id, workspace_id)

    def get_by_auth_user_id_any_workspace(self, auth_user_id: str) -> SupportAgent | None:
        return self._repo.get_by_auth_user_id_any_workspace(auth_user_id)

    def get_by_id(self, agent_id: str) -> SupportAgent | None:
        return self._repo.get_by_id(agent_id)

    def get_or_create(
        self, auth_user_id: str, email: str, name: str, workspace_id: str, department: str = "General"
    ) -> SupportAgent:
        return self._repo.get_or_create(auth_user_id, email, name, workspace_id, department=department)

    def update_status(self, agent_id: str, status: str) -> SupportAgent:
        return self._repo.update_status(agent_id, status)

    def update_department(self, agent_id: str, department: str) -> SupportAgent:
        return self._repo.update_department(agent_id, department)

    def delete(self, agent_id: str) -> None:
        self._repo.delete(agent_id)

    def list_available(self, workspace_id: str) -> list[SupportAgent]:
        return self._repo.list_available(workspace_id)

    def list_by_workspace(self, workspace_id: str) -> list[SupportAgent]:
        return self._repo.list_by_workspace(workspace_id)
