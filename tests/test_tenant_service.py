"""Tests for TenantService/AdminWorkspaceRepository (Phase 26) — including
the security-relevant api-key-regeneration test: the old key never
resurfaces, the new key is returned exactly once."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from postgrest.exceptions import APIError

from src.services.admin.tenant_repository import AdminWorkspaceRepository
from src.services.admin.tenant_service import TenantService


def _workspace_row(**overrides):
    base = {
        "id": "w1", "slug": "acme", "name": "Acme", "api_key": "old-key", "host": None,
        "is_active": True, "logo": None, "primary_color": None, "welcome_message": None,
        "quick_actions": None, "archived_at": None, "deleted_at": None, "created_at": None,
        "updated_at": None,
    }
    base.update(overrides)
    return base


class TestAdminWorkspaceRepository:
    def test_create_generates_a_real_api_key(self):
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.return_value.data = [_workspace_row()]
        repo = AdminWorkspaceRepository(client=client)

        repo.create("acme", "Acme")

        payload = client.table.return_value.insert.call_args[0][0]
        assert payload["slug"] == "acme"
        assert len(payload["api_key"]) > 20

    def test_create_duplicate_slug_raises_value_error_not_raw_api_error(self):
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.side_effect = APIError(
            {"message": "duplicate key value violates unique constraint \"workspaces_slug_key\"", "code": "23505"}
        )
        repo = AdminWorkspaceRepository(client=client)

        with pytest.raises(ValueError, match="already exists"):
            repo.create("acme", "Acme")

    def test_create_other_api_error_propagates_unchanged(self):
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.side_effect = APIError(
            {"message": "some other failure", "code": "99999"}
        )
        repo = AdminWorkspaceRepository(client=client)

        with pytest.raises(APIError):
            repo.create("acme", "Acme")

    def test_archive_also_sets_is_active_false(self):
        client = MagicMock()
        client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            _workspace_row(is_active=False, archived_at="2026-01-01T00:00:00Z")
        ]
        repo = AdminWorkspaceRepository(client=client)

        repo.archive("w1")

        payload = client.table.return_value.update.call_args[0][0]
        assert payload["is_active"] is False
        assert "archived_at" in payload

    def test_reactivate_clears_archived_at(self):
        client = MagicMock()
        client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            _workspace_row(is_active=True, archived_at=None)
        ]
        repo = AdminWorkspaceRepository(client=client)

        repo.set_active("w1", True)

        payload = client.table.return_value.update.call_args[0][0]
        assert payload["is_active"] is True
        assert payload["archived_at"] is None

    def test_suspend_does_not_touch_archived_at(self):
        client = MagicMock()
        client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            _workspace_row(is_active=False)
        ]
        repo = AdminWorkspaceRepository(client=client)

        repo.set_active("w1", False)

        payload = client.table.return_value.update.call_args[0][0]
        assert "archived_at" not in payload

    def test_regenerate_api_key_returns_new_key_and_updates_row(self):
        client = MagicMock()
        client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            _workspace_row(api_key="whatever")
        ]
        repo = AdminWorkspaceRepository(client=client)

        new_key = repo.regenerate_api_key("w1")

        assert len(new_key) > 20
        updated_payload = client.table.return_value.update.call_args[0][0]
        assert updated_payload["api_key"] == new_key

    def test_regenerate_api_key_never_returns_the_same_key_twice(self):
        client = MagicMock()
        client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            _workspace_row()
        ]
        repo = AdminWorkspaceRepository(client=client)

        first = repo.regenerate_api_key("w1")
        second = repo.regenerate_api_key("w1")

        assert first != second


class TestTenantService:
    def test_create_workspace_records_audit_event(self):
        repo = MagicMock()
        repo.create.return_value = MagicMock(id="w1")
        audit = MagicMock()
        service = TenantService(repository=repo, audit=audit)

        service.create_workspace("acme", "Acme", None, "admin-1")

        audit.record.assert_called_once_with(
            "workspace.created", "admin-1", "w1", {"slug": "acme", "name": "Acme"}
        )

    def test_suspend_calls_set_active_false(self):
        repo = MagicMock()
        repo.set_active.return_value = MagicMock(id="w1")
        audit = MagicMock()
        service = TenantService(repository=repo, audit=audit)

        service.suspend("w1", "admin-1")

        repo.set_active.assert_called_once_with("w1", False)
        audit.record.assert_called_once_with("workspace.suspended", "admin-1", "w1", {})

    def test_reactivate_calls_set_active_true(self):
        repo = MagicMock()
        repo.set_active.return_value = MagicMock(id="w1")
        audit = MagicMock()
        service = TenantService(repository=repo, audit=audit)

        service.reactivate("w1", "admin-1")

        repo.set_active.assert_called_once_with("w1", True)

    def test_regenerate_api_key_delegates_and_audits(self):
        repo = MagicMock()
        repo.regenerate_api_key.return_value = "new-key-value"
        audit = MagicMock()
        service = TenantService(repository=repo, audit=audit)

        result = service.regenerate_api_key("w1", "admin-1")

        assert result == "new-key-value"
        audit.record.assert_called_once_with("workspace.apikey_regenerated", "admin-1", "w1", {})

    def test_archive_and_soft_delete(self):
        repo = MagicMock()
        repo.archive.return_value = MagicMock(id="w1")
        repo.soft_delete.return_value = MagicMock(id="w1")
        audit = MagicMock()
        service = TenantService(repository=repo, audit=audit)

        service.archive("w1", "admin-1")
        service.soft_delete("w1", "admin-1")

        repo.archive.assert_called_once_with("w1")
        repo.soft_delete.assert_called_once_with("w1")
        assert audit.record.call_count == 2
