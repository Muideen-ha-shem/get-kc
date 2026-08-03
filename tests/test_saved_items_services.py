"""Tests for SavedComparisonService / SavedRecommendationService — Supabase
calls mocked, following the same RLS-authenticated-client pattern proven in
test_rls_authenticated_client.py (Phase 20)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.services.saved_items.saved_comparison_service import SavedComparisonService
from src.services.saved_items.saved_recommendation_service import SavedRecommendationService
from src.services.workspace.workspace_models import DEFAULT_WORKSPACE_ID


def _comparison_row(**overrides):
    base = {"id": "cmp1", "user_id": "u1", "product_ids": ["SPIDIFY", "ZivaAIRA"], "created_at": None}
    base.update(overrides)
    return base


def _recommendation_row(**overrides):
    base = {
        "id": "rec1", "user_id": "u1", "products": ["SPIDIFY"],
        "question": "We need identity verification", "recommendation": "SPIDIFY is a great fit.",
        "created_at": None,
    }
    base.update(overrides)
    return base


class TestSavedComparisonService:
    def test_save_inserts_and_returns_row(self):
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.return_value.data = [_comparison_row()]
        service = SavedComparisonService(client=client)

        row = service.save("u1", ["SPIDIFY", "ZivaAIRA"])

        assert row.product_ids == ["SPIDIFY", "ZivaAIRA"]
        client.table.return_value.insert.assert_called_once_with(
            {"user_id": "u1", "product_ids": ["SPIDIFY", "ZivaAIRA"], "workspace_id": DEFAULT_WORKSPACE_ID}
        )

    def test_save_uses_authenticated_client_when_token_given(self):
        default_client = MagicMock()
        authed_client = MagicMock()
        authed_client.table.return_value.insert.return_value.execute.return_value.data = [_comparison_row()]

        with patch(
            "src.services.saved_items.saved_comparison_service.get_authenticated_client",
            return_value=authed_client,
        ) as mock_get_authed:
            service = SavedComparisonService(client=default_client)
            service.save("u1", ["SPIDIFY", "ZivaAIRA"], access_token="real-jwt")

        mock_get_authed.assert_called_once_with("real-jwt")
        default_client.table.assert_not_called()

    def test_list_for_user_orders_newest_first(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            _comparison_row()
        ]
        service = SavedComparisonService(client=client)

        rows = service.list_for_user("u1")

        assert len(rows) == 1
        client.table.return_value.select.return_value.eq.return_value.order.assert_called_once_with(
            "created_at", desc=True
        )

    def test_delete_returns_true_when_deleted(self):
        client = MagicMock()
        client.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            _comparison_row()
        ]
        service = SavedComparisonService(client=client)

        assert service.delete("cmp1", "u1") is True

    def test_delete_returns_false_when_not_owned(self):
        client = MagicMock()
        client.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        service = SavedComparisonService(client=client)

        assert service.delete("cmp1", "u1") is False


class TestSavedRecommendationService:
    def test_save_inserts_and_returns_row(self):
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.return_value.data = [_recommendation_row()]
        service = SavedRecommendationService(client=client)

        row = service.save("u1", ["SPIDIFY"], "We need identity verification", "SPIDIFY is a great fit.")

        assert row.products == ["SPIDIFY"]
        assert row.question == "We need identity verification"

    def test_delete_scoped_to_owner(self):
        client = MagicMock()
        client.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            _recommendation_row()
        ]
        service = SavedRecommendationService(client=client)

        assert service.delete("rec1", "u1") is True
        client.table.return_value.delete.return_value.eq.assert_any_call("id", "rec1")
