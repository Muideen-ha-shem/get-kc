"""Tests for CollectionService/CollectionRepository (Phase 27)."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.services.knowledge_management.collection_repository import CollectionRepository
from src.services.knowledge_management.collection_service import CollectionService


def _row(**overrides):
    base = {"id": "c1", "workspace_id": "w1", "name": "Support", "description": None, "created_at": None, "updated_at": None, "archived_at": None}
    base.update(overrides)
    return base


class TestCollectionRepository:
    def test_create_inserts_row(self):
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.return_value.data = [_row()]
        repo = CollectionRepository(client=client)

        collection = repo.create("w1", "Support", None)

        assert collection.name == "Support"
        client.table.return_value.insert.assert_called_once_with(
            {"workspace_id": "w1", "name": "Support", "description": None}
        )

    def test_list_for_workspace_excludes_archived(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.is_.return_value.order.return_value.execute.return_value.data = [
            _row()
        ]
        repo = CollectionRepository(client=client)

        collections = repo.list_for_workspace("w1")

        assert len(collections) == 1
        client.table.return_value.select.return_value.eq.return_value.is_.assert_called_once_with(
            "archived_at", "null"
        )


class TestCollectionService:
    def test_create_delegates(self):
        repo = MagicMock()
        service = CollectionService(repository=repo)

        service.create("w1", "Sales", "Sales team docs")

        repo.create.assert_called_once_with("w1", "Sales", "Sales team docs")
