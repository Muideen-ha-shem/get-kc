"""Tests for FeatureFlagService/FeatureFlagRepository (Phase 26)."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.services.admin.feature_flag_repository import FeatureFlagRepository
from src.services.admin.feature_flag_service import FeatureFlagService


def _flag_row(**overrides):
    base = {"id": "f1", "workspace_id": "w1", "flag_key": "ai_copilot", "enabled": True, "created_at": None, "updated_at": None}
    base.update(overrides)
    return base


class TestFeatureFlagRepository:
    def test_set_flag_inserts_when_missing(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        client.table.return_value.insert.return_value.execute.return_value.data = [_flag_row()]
        repo = FeatureFlagRepository(client=client)

        flag = repo.set_flag("w1", "ai_copilot", True)

        assert flag.enabled is True
        client.table.return_value.insert.assert_called_once_with(
            {"workspace_id": "w1", "flag_key": "ai_copilot", "enabled": True}
        )

    def test_set_flag_updates_when_existing(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            _flag_row(enabled=True)
        ]
        client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            _flag_row(enabled=False)
        ]
        repo = FeatureFlagRepository(client=client)

        flag = repo.set_flag("w1", "ai_copilot", False)

        assert flag.enabled is False


class TestFeatureFlagService:
    def test_is_enabled_returns_default_when_no_flag_row(self):
        repo = MagicMock()
        repo.get.return_value = None
        service = FeatureFlagService(repository=repo)

        assert service.is_enabled("w1", "ai_copilot", default=True) is True
        assert service.is_enabled("w1", "ai_copilot", default=False) is False

    def test_is_enabled_returns_stored_value_when_flag_exists(self):
        repo = MagicMock()
        repo.get.return_value = MagicMock(enabled=False)
        service = FeatureFlagService(repository=repo)

        assert service.is_enabled("w1", "ai_copilot", default=True) is False
