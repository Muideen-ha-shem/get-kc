"""Tests for NotificationService — Supabase mocked, RLS-authenticated-client
pattern verified the same way as test_rls_authenticated_client.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.services.notifications.notification_service import NotificationService


def _row(**overrides):
    base = {"id": "n1", "type": "appointment", "title": "Appointment confirmed", "body": "2026-08-01 at 09:00", "is_read": False, "created_at": None}
    base.update(overrides)
    return base


class TestNotify:
    def test_notify_inserts_and_returns_row(self):
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.return_value.data = [_row()]
        service = NotificationService(client=client)

        notification = service.notify("u1", "appointment", "Appointment confirmed", "2026-08-01 at 09:00")

        assert notification is not None
        assert notification.type == "appointment"

    def test_notify_uses_authenticated_client_when_token_given(self):
        default_client = MagicMock()
        authed_client = MagicMock()
        authed_client.table.return_value.insert.return_value.execute.return_value.data = [_row()]

        with patch(
            "src.services.notifications.notification_service.get_authenticated_client",
            return_value=authed_client,
        ) as mock_get_authed:
            service = NotificationService(client=default_client)
            service.notify("u1", "appointment", "Appointment confirmed", access_token="real-jwt")

        mock_get_authed.assert_called_once_with("real-jwt")
        default_client.table.assert_not_called()

    def test_notify_failure_is_swallowed_and_returns_none(self):
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.side_effect = RuntimeError("boom")
        service = NotificationService(client=client)

        result = service.notify("u1", "appointment", "Appointment confirmed")

        assert result is None  # must not raise


class TestListAndCounts:
    def test_list_for_user_orders_newest_first(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            _row()
        ]
        service = NotificationService(client=client)

        rows = service.list_for_user("u1")

        assert len(rows) == 1
        client.table.return_value.select.return_value.eq.return_value.order.assert_called_once_with(
            "created_at", desc=True
        )

    def test_unread_count_reads_response_count(self):
        client = MagicMock()
        response = MagicMock()
        response.count = 3
        client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = response
        service = NotificationService(client=client)

        assert service.unread_count("u1") == 3

    def test_unread_count_defaults_to_zero_when_none(self):
        client = MagicMock()
        response = MagicMock()
        response.count = None
        client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = response
        service = NotificationService(client=client)

        assert service.unread_count("u1") == 0


class TestMarkRead:
    def test_mark_read_returns_true_when_updated(self):
        client = MagicMock()
        client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            _row(is_read=True)
        ]
        service = NotificationService(client=client)

        assert service.mark_read("n1", "u1") is True

    def test_mark_read_returns_false_when_not_owned(self):
        client = MagicMock()
        client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        service = NotificationService(client=client)

        assert service.mark_read("n1", "u1") is False

    def test_mark_all_read_scopes_to_unread_own_rows(self):
        client = MagicMock()
        service = NotificationService(client=client)

        service.mark_all_read("u1")

        client.table.return_value.update.assert_called_once_with({"is_read": True})
