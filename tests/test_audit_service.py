"""Tests for AuditService/AuditRepository (Phase 26) — append-only."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.services.admin.audit_repository import AuditRepository
from src.services.admin.audit_service import AuditService


def _row(**overrides):
    base = {
        "id": "a1", "workspace_id": "w1", "actor_auth_user_id": "u1",
        "action": "workspace.created", "metadata": {}, "created_at": None,
    }
    base.update(overrides)
    return base


class TestAuditRepository:
    def test_insert_writes_expected_payload(self):
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.return_value.data = [_row()]
        repo = AuditRepository(client=client)

        entry = repo.insert("w1", "u1", "workspace.created", {"slug": "acme"})

        assert entry.action == "workspace.created"
        client.table.return_value.insert.assert_called_once_with(
            {"workspace_id": "w1", "actor_auth_user_id": "u1", "action": "workspace.created",
             "metadata": {"slug": "acme"}}
        )

    def test_list_recent_filters_by_workspace_when_given(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        repo = AuditRepository(client=client)

        repo.list_recent("w1", 50)

        client.table.return_value.select.return_value.eq.assert_called_once_with("workspace_id", "w1")

    def test_list_recent_without_workspace_id_skips_filter(self):
        client = MagicMock()
        client.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        repo = AuditRepository(client=client)

        repo.list_recent(None, 50)

        client.table.return_value.select.return_value.eq.assert_not_called()

    def test_append_only_no_update_or_delete_method(self):
        """Append-only is a structural guarantee, not a runtime guard —
        confirmed by the absence of these methods entirely."""
        assert not hasattr(AuditRepository, "update")
        assert not hasattr(AuditRepository, "delete")
        assert not hasattr(AuditService, "update")
        assert not hasattr(AuditService, "delete")


class TestAuditService:
    def test_record_delegates_to_repository_insert(self):
        repo = MagicMock()
        repo.insert.return_value = MagicMock()
        service = AuditService(repository=repo)

        service.record("workspace.created", "u1", "w1", {"slug": "acme"})

        repo.insert.assert_called_once_with("w1", "u1", "workspace.created", {"slug": "acme"})

    def test_list_recent_defaults(self):
        repo = MagicMock()
        repo.list_recent.return_value = []
        service = AuditService(repository=repo)

        service.list_recent()

        repo.list_recent.assert_called_once_with(None, 100)
