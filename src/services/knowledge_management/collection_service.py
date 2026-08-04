"""CollectionService — thin facade over CollectionRepository (Phase 27)."""

from __future__ import annotations

from .collection_repository import CollectionRepository
from .km_models import KnowledgeCollection


class CollectionService:
    def __init__(self, repository: CollectionRepository | None = None) -> None:
        self._repo = repository or CollectionRepository()

    def list_for_workspace(self, workspace_id: str) -> list[KnowledgeCollection]:
        return self._repo.list_for_workspace(workspace_id)

    def create(self, workspace_id: str, name: str, description: str | None = None) -> KnowledgeCollection:
        return self._repo.create(workspace_id, name, description)

    def archive(self, collection_id: str) -> KnowledgeCollection:
        return self._repo.archive(collection_id)
