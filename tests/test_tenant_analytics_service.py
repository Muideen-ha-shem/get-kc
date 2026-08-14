"""Tests for TenantAnalyticsService (Phase 26) — mocked client/repositories,
mirrors test_agent_dashboard_stats.py's averaging-query test style."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

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


def _client_by_table_and_select(responses: dict[tuple[str, str], list[dict]]) -> MagicMock:
    """A client where `.table(name).select(arg)...execute().data` resolves
    per (table, select_arg) pair — precise enough to distinguish the three
    distinct list-queries workspace_operational_report() makes (each uses
    a different select() argument), unlike the flat count-only mock above
    (which is fine for workspace_stats()'s uniform count queries, but not
    for these)."""
    client = MagicMock()

    def table_fn(table_name):
        table_mock = MagicMock()

        def select_fn(select_arg, **_kwargs):
            chain = MagicMock()
            chain.eq.return_value = chain
            chain.in_.return_value = chain
            chain.gte.return_value = chain
            chain.lte.return_value = chain
            chain.limit.return_value = chain
            chain.order.return_value = chain
            chain.not_.is_.return_value = chain
            response = MagicMock()
            response.data = responses.get((table_name, select_arg), [])
            chain.execute.return_value = response
            return chain

        table_mock.select.side_effect = select_fn
        return table_mock

    client.table.side_effect = table_fn
    return client


_BASE_STATS = {
    "conversation_count": 10,
    "escalation_count": 4,
    "escalation_status_breakdown": {
        "waiting": 0, "assigned": 0, "active": 0, "waiting_for_customer": 0, "resolved": 1, "closed": 1,
    },
    "appointment_count": 0,
    "saved_recommendation_count": 0,
    "saved_comparison_count": 0,
    "feedback_helpful_count": 0,
    "feedback_not_helpful_count": 0,
}


class TestWorkspaceOperationalReport:
    def test_resolution_rate_and_average_time(self):
        client = _client_by_table_and_select({
            ("escalations", "assigned_agent_id,department,created_at,resolved_at,summary"): [
                {
                    "assigned_agent_id": "a1", "department": "Support",
                    "created_at": "2026-01-01T00:00:00+00:00", "resolved_at": "2026-01-01T01:00:00+00:00",
                    "summary": {"sentiment": "neutral"},
                },
                {
                    "assigned_agent_id": "a1", "department": "Support",
                    "created_at": "2026-01-01T00:00:00+00:00", "resolved_at": "2026-01-01T00:30:00+00:00",
                    "summary": {"sentiment": "frustrated"},
                },
            ],
            ("escalations", "conversation_id"): [{"conversation_id": "c1"}, {"conversation_id": "c2"}],
            ("saved_recommendations", "products"): [{"products": ["SPIDIFY", "V-Login"]}, {"products": ["SPIDIFY"]}],
        })
        from types import SimpleNamespace

        agent_repo = MagicMock()
        agent_repo.list_by_workspace.return_value = [
            SimpleNamespace(id="a1", name="Ada", department="Support", status="available"),
        ]
        escalation_repo = MagicMock()
        escalation_repo.count_active_for_agent.return_value = 2
        attendance_repo = MagicMock()
        attendance_repo.get_active_session.return_value = None
        attendance_repo.get_active_aux.return_value = None
        service = TenantAnalyticsService(
            client=client, agent_repository=agent_repo, escalation_repository=escalation_repo,
            attendance_repository=attendance_repo,
        )

        with patch.object(service, "workspace_stats", return_value=_BASE_STATS):
            report = service.workspace_operational_report("w1")

        assert report["resolution_rate"] == 0.5  # (resolved + closed) / escalation_count = 2/4
        assert report["average_resolution_minutes"] == 45.0  # mean of 60 and 30
        assert report["department_activity"] == {"Support": 2}
        assert report["frustrated_conversation_count"] == 1
        assert report["agents"] == [
            {
                "id": "a1", "name": "Ada", "department": "Support", "status": "available", "current_workload": 2,
                "clock_in_at": None, "current_aux": None, "current_aux_started_at": None,
                "avg_first_response_minutes": None,
            },
        ]
        assert report["requested_products"] == {"SPIDIFY": 2, "V-Login": 1}
        assert report["ai_resolved_rate_estimate"] == 0.8  # (10 - 2) / 10
        assert report["clocked_in_count"] == 0
        assert report["available_count"] == 0
        assert report["performance_targets"] == {
            "resolution_rate": None, "response_minutes": None, "resolution_minutes": None, "csat": None,
        }
        assert report["adherence"] is None
        assert "no schedule configured" in report["adherence_note"].lower()

    def test_zero_escalations_gives_none_resolution_rate(self):
        client = _client_by_table_and_select({})
        agent_repo = MagicMock()
        agent_repo.list_by_workspace.return_value = []
        attendance_repo = MagicMock()
        service = TenantAnalyticsService(
            client=client, agent_repository=agent_repo, attendance_repository=attendance_repo,
        )

        stats = {**_BASE_STATS, "escalation_count": 0, "conversation_count": 0}
        with patch.object(service, "workspace_stats", return_value=stats):
            report = service.workspace_operational_report("w1")

        assert report["resolution_rate"] is None
        assert report["average_resolution_minutes"] is None
        assert report["ai_resolved_rate_estimate"] is None

    def test_knowledge_metrics_are_honestly_none_not_fabricated(self):
        client = _client_by_table_and_select({})
        agent_repo = MagicMock()
        agent_repo.list_by_workspace.return_value = []
        attendance_repo = MagicMock()
        service = TenantAnalyticsService(
            client=client, agent_repository=agent_repo, attendance_repository=attendance_repo,
        )

        with patch.object(service, "workspace_stats", return_value=_BASE_STATS):
            report = service.workspace_operational_report("w1")

        assert report["knowledge_gaps"] is None
        assert report["frequently_searched_topics"] is None
        assert report["insufficient_evidence_questions"] is None
        assert report["source_failures"] is None
        assert "not tracked yet" in report["knowledge_tracking_note"].lower()
        assert "not tracked" in report["csat_note"].lower()

    def test_aux_breakdown_and_categorization(self):
        client = _client_by_table_and_select({})
        from types import SimpleNamespace

        agent_repo = MagicMock()
        agent_repo.list_by_workspace.return_value = [
            SimpleNamespace(id="a1", name="Ada", department="Support", status="away"),
            SimpleNamespace(id="a2", name="David", department="Support", status="available"),
        ]
        escalation_repo = MagicMock()
        escalation_repo.count_active_for_agent.return_value = 0
        attendance_repo = MagicMock()

        session_a1 = SimpleNamespace(clock_in_at="2026-01-01T08:00:00+00:00")
        session_a2 = SimpleNamespace(clock_in_at="2026-01-01T08:15:00+00:00")
        aux_a1 = SimpleNamespace(aux_type="training", started_at="2026-01-01T09:00:00+00:00")

        def get_active_session(agent_id):
            return {"a1": session_a1, "a2": session_a2}.get(agent_id)

        def get_active_aux(agent_id):
            return aux_a1 if agent_id == "a1" else None

        attendance_repo.get_active_session.side_effect = get_active_session
        attendance_repo.get_active_aux.side_effect = get_active_aux

        service = TenantAnalyticsService(
            client=client, agent_repository=agent_repo, escalation_repository=escalation_repo,
            attendance_repository=attendance_repo,
        )

        with patch.object(service, "workspace_stats", return_value=_BASE_STATS):
            report = service.workspace_operational_report("w1")

        assert report["clocked_in_count"] == 2
        assert report["available_count"] == 1  # a2 only — a1 is in AUX
        assert report["aux_breakdown"] == {"training": 1}
        assert report["aux_time_by_category"] == {"productive_operational": 1}  # built-in default
