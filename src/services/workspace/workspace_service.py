"""WorkspaceService — thin facade over WorkspaceRepository.

This is the class route/service code imports, not the repository directly
(matches the ConversationService/ConversationRepository split).
"""

from __future__ import annotations

from .workspace_models import Workspace
from .workspace_repository import WorkspaceRepository


class WorkspaceService:
    def __init__(self, repository: WorkspaceRepository | None = None) -> None:
        self._repo = repository or WorkspaceRepository()

    def get_by_id(self, workspace_id: str) -> Workspace | None:
        return self._repo.get_by_id(workspace_id)

    def get_by_slug(self, slug: str) -> Workspace | None:
        return self._repo.get_by_slug(slug)

    def get_default(self) -> Workspace:
        return self._repo.get_default()
