"""Tests for TenantAnalyticsService (Phase 26) — mocked client/repositories,
mirrors test_agent_dashboard_stats.py's averaging-query test style."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.services.admin.tenant_analytics_service import TenantAnalyticsService


def _count_response(count):
    response = MagicMock()
    response.count = count
    return response


def _client_returning_count(count) -> MagicMock:
    """A client where `.table(...).select(...).eq(...).eq(...)....execute()`
    resolves to the same count regardless of how many `.eq()` filters are
    chained on — `.eq()` returns the same chainable mock each time."""
    client = MagicMock()
    chain = MagicMock()
    chain.eq.return_value = chain
    chain.execute.return_value = _count_response(count)
    client.table.return_value.select.return_value = chain
    return client


class TestWorkspaceStats:
    def test_returns_all_expected_counts(self):
        client = _client_returning_count(5)
        service = TenantAnalyticsService(client=client)

        stats = service.workspace_stats("w1")

        assert stats["conversation_count"] == 5
        assert stats["escalation_count"] == 5
        assert set(stats["escalation_status_breakdown"].keys()) == {
            "waiting", "assigned", "active", "waiting_for_customer", "resolved", "closed",
        }
        assert all(count == 5 for count in stats["escalation_status_breakdown"].values())
        assert stats["appointment_count"] == 5
        assert stats["saved_recommendation_count"] == 5
        assert stats["saved_comparison_count"] == 5
        assert stats["feedback_helpful_count"] == 5
        assert stats["feedback_not_helpful_count"] == 5

    def test_zero_count_when_response_count_is_none(self):
        client = _client_returning_count(None)
        service = TenantAnalyticsService(client=client)

        stats = service.workspace_stats("w1")

        assert stats["conversation_count"] == 0


class TestPlatformDashboardStats:
    def test_counts_only_non_deleted_workspaces(self):
        client = _client_returning_count(2)
        agent_repo = MagicMock()
        agent_repo.list_by_workspace.return_value = []
        service = TenantAnalyticsService(client=client, agent_repository=agent_repo)

        active_workspace = MagicMock(id="w1", is_active=True, deleted_at=None)
        suspended_workspace = MagicMock(id="w2", is_active=False, deleted_at=None)
        deleted_workspace = MagicMock(id="w3", is_active=True, deleted_at="2026-01-01T00:00:00Z")

        stats = service.platform_dashboard_stats([active_workspace, suspended_workspace, deleted_workspace])

        assert stats["total_workspace_count"] == 2
        assert stats["active_workspace_count"] == 1
