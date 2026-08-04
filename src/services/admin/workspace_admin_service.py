"""WorkspaceAdminService — thin facade over WorkspaceAdminRepository
(Phase 27). `is_workspace_admin` backs the `require_workspace_admin`
FastAPI dependency."""

from __future__ import annotations

from .workspace_admin_repository import WorkspaceAdminRepository


class WorkspaceAdminService:
    def __init__(self, repository: WorkspaceAdminRepository | None = None) -> None:
        self._repo = repository or WorkspaceAdminRepository()

    def is_workspace_admin(self, auth_user_id: str, workspace_id: str) -> bool:
        return self._repo.get_by_auth_user_id(auth_user_id, workspace_id) is not None

    def list_for_workspace(self, workspace_id: str) -> list[dict]:
        return self._repo.list_for_workspace(workspace_id)

    def add_admin(self, workspace_id: str, auth_user_id: str) -> dict:
        return self._repo.add(workspace_id, auth_user_id)

    def remove_admin(self, workspace_id: str, auth_user_id: str) -> None:
        self._repo.remove(workspace_id, auth_user_id)
