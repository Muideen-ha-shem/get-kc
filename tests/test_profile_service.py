"""Tests for ProfileService — all Supabase calls mocked."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.services.profile.profile_service import ProfileService


def _row(**overrides):
    base = {
        "id": "p1", "auth_user_id": "u1", "email": "a@b.com", "full_name": None,
        "company_name": None, "industry": None, "phone": None,
        "created_at": None, "updated_at": None, "last_login": None,
    }
    base.update(overrides)
    return base


class TestGetOrCreate:
    def test_returns_existing_profile_without_inserting(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [_row()]
        service = ProfileService(client=client)

        profile = service.get_or_create("u1", "a@b.com")

        assert profile.auth_user_id == "u1"
        client.table.return_value.insert.assert_not_called()

    def test_creates_profile_when_missing(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        client.table.return_value.insert.return_value.execute.return_value.data = [_row(full_name="Ada")]
        service = ProfileService(client=client)

        profile = service.get_or_create("u1", "a@b.com", "Ada")

        assert profile.full_name == "Ada"
        client.table.return_value.insert.assert_called_once()


class TestUpdate:
    def test_updates_allowed_fields_only(self):
        client = MagicMock()
        client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            _row(company_name="Acme", industry="Financial Services")
        ]
        service = ProfileService(client=client)

        profile = service.update("u1", company_name="Acme", industry="Financial Services", email="ignored@x.com")

        assert profile.company_name == "Acme"
        payload = client.table.return_value.update.call_args[0][0]
        assert "email" not in payload

    def test_no_op_update_returns_existing_profile(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [_row()]
        service = ProfileService(client=client)

        profile = service.update("u1")

        assert profile.auth_user_id == "u1"
        client.table.return_value.update.assert_not_called()

    def test_missing_profile_raises(self):
        client = MagicMock()
        client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []
        service = ProfileService(client=client)

        import pytest
        with pytest.raises(ValueError):
            service.update("u1", company_name="Acme")


class TestRecordLogin:
    def test_updates_last_login(self):
        client = MagicMock()
        service = ProfileService(client=client)

        service.record_login("u1")

        client.table.return_value.update.assert_called_once()
        payload = client.table.return_value.update.call_args[0][0]
        assert "last_login" in payload
