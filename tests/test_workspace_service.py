"""Tests for WorkspaceRepository/WorkspaceService — Supabase mocked."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.services.workspace.workspace_models import Workspace
from src.services.workspace.workspace_repository import WorkspaceRepository
from src.services.workspace.workspace_service import WorkspaceService


def _row(**overrides):
    base = {"id": "w1", "slug": "acme", "name": "Acme", "api_key": None, "host": None, "is_active": True}
    base.update(overrides)
    return base


class TestWorkspaceRepository:
    def test_get_by_id_returns_workspace(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            _row()
        ]
        repo = WorkspaceRepository(client=client)

        workspace = repo.get_by_id("w1")

        assert workspace == Workspace(id="w1", slug="acme", name="Acme")

    def test_get_by_slug_not_found_returns_none(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        repo = WorkspaceRepository(client=client)

        assert repo.get_by_slug("missing") is None

    def test_get_default_falls_back_when_lookup_raises(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = RuntimeError(
            "network down"
        )
        repo = WorkspaceRepository(client=client)

        workspace = repo.get_default()

        assert workspace == Workspace.default()

    def test_get_default_falls_back_when_seed_row_missing(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        repo = WorkspaceRepository(client=client)

        workspace = repo.get_default()

        assert workspace == Workspace.default()

    def test_get_default_returns_real_row_when_present(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            _row(id="real-id", slug="ha-shem", name="Ha-Shem")
        ]
        repo = WorkspaceRepository(client=client)

        workspace = repo.get_default()

        assert workspace.id == "real-id"


class TestWorkspaceService:
    def test_get_by_slug_delegates_to_repository(self):
        repo = MagicMock()
        repo.get_by_slug.return_value = Workspace(id="w1", slug="acme", name="Acme")
        service = WorkspaceService(repository=repo)

        workspace = service.get_by_slug("acme")

        assert workspace.slug == "acme"
        repo.get_by_slug.assert_called_once_with("acme")
