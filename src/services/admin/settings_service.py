"""SettingsService — thin facade over WorkspaceSettingsRepository (Phase 26)."""

from __future__ import annotations

from .admin_models import WorkspaceSettings
from .workspace_settings_repository import WorkspaceSettingsRepository


class SettingsService:
    def __init__(self, repository: WorkspaceSettingsRepository | None = None) -> None:
        self._repo = repository or WorkspaceSettingsRepository()

    def get(self, workspace_id: str) -> WorkspaceSettings:
        existing = self._repo.get_by_workspace_id(workspace_id)
        if existing is not None:
            return existing
        return self._repo.create_default(workspace_id)

    def update(self, workspace_id: str, **fields) -> WorkspaceSettings:
        return self._repo.upsert(workspace_id, **fields)
