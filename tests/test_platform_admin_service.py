"""Tests for PlatformAdminService/PlatformAdminRepository — mocked Supabase
client, mirrors test_profile_service.py's pattern."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.services.admin.platform_admin_repository import PlatformAdminRepository
from src.services.admin.platform_admin_service import PlatformAdminService


def _row(**overrides):
    base = {"id": "pa1", "auth_user_id": "u1", "created_at": None}
    base.update(overrides)
    return base


class TestPlatformAdminRepository:
    def test_get_by_auth_user_id_found(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            _row()
        ]
        repo = PlatformAdminRepository(client=client)

        admin = repo.get_by_auth_user_id("u1")

        assert admin is not None
        assert admin.auth_user_id == "u1"

    def test_get_by_auth_user_id_not_found(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        repo = PlatformAdminRepository(client=client)

        assert repo.get_by_auth_user_id("u2") is None

    def test_add_inserts_row(self):
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.return_value.data = [_row()]
        repo = PlatformAdminRepository(client=client)

        admin = repo.add("u1")

        assert admin.auth_user_id == "u1"
        client.table.return_value.insert.assert_called_once_with({"auth_user_id": "u1"})

    def test_remove_deletes_by_auth_user_id(self):
        client = MagicMock()
        repo = PlatformAdminRepository(client=client)

        repo.remove("u1")

        client.table.return_value.delete.return_value.eq.assert_called_once_with("auth_user_id", "u1")


class TestPlatformAdminService:
    def test_is_super_admin_true_when_row_exists(self):
        repo = MagicMock()
        repo.get_by_auth_user_id.return_value = MagicMock()
        service = PlatformAdminService(repository=repo)

        assert service.is_super_admin("u1") is True

    def test_is_super_admin_false_when_no_row(self):
        repo = MagicMock()
        repo.get_by_auth_user_id.return_value = None
        service = PlatformAdminService(repository=repo)

        assert service.is_super_admin("u1") is False
