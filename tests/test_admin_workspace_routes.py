"""Integration tests for the /admin/workspaces* + /admin/dashboard +
/admin/audit routes (Phase 26) — mirrors test_agent_escalation_routes.py's
dependency-override + patched-singleton pattern. Every endpoint must 403
without require_super_admin overridden."""

from __future__ import annotations

from unittest.mock import ANY, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.deps import get_current_user_required, require_super_admin, require_workspace_admin
from src.services.auth.auth_service import AuthUser

_FAKE_ADMIN = AuthUser(id="admin-1", email="admin@example.com", full_name="Admin")


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _authenticate_as_admin():
    app.dependency_overrides[require_super_admin] = lambda: _FAKE_ADMIN
    # Phase 28: get/analytics/branding/settings/products/apikey routes now
    # accept require_workspace_admin too (a strict widening — see
    # admin_workspaces.py's module docstring) — both must be overridden so
    # tests authenticate regardless of which dependency a given route uses.
    app.dependency_overrides[require_workspace_admin] = lambda: _FAKE_ADMIN
    app.dependency_overrides[get_current_user_required] = lambda: _FAKE_ADMIN


def _workspace(**overrides):
    # NOTE: `name=` is a reserved MagicMock constructor kwarg (sets the
    # mock's repr, not a `.name` attribute) — set it via configure_mock.
    base = MagicMock(
        id="w1", slug="acme", host=None, is_active=True, logo=None,
        primary_color=None, welcome_message=None, quick_actions=None, archived_at=None,
        deleted_at=None, created_at=None, updated_at=None, api_key="raw-key-value",
        owner_auth_user_id=None, plan="free",
    )
    base.configure_mock(name="Acme")
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


_FAKE_NON_ADMIN = AuthUser(id="u2", email="customer@example.com", full_name="Customer")


def _authenticate_as_non_admin():
    app.dependency_overrides[get_current_user_required] = lambda: _FAKE_NON_ADMIN


class TestAuthorization:
    def test_list_workspaces_401s_with_no_auth_at_all(self, client):
        response = client.get("/admin/workspaces")
        assert response.status_code == 401

    def test_list_workspaces_403s_for_authenticated_non_admin(self, client):
        _authenticate_as_non_admin()
        with patch("src.api.deps._platform_admin_service.is_super_admin", return_value=False):
            response = client.get("/admin/workspaces")
        assert response.status_code == 403

    def test_dashboard_403s_for_authenticated_non_admin(self, client):
        _authenticate_as_non_admin()
        with patch("src.api.deps._platform_admin_service.is_super_admin", return_value=False):
            response = client.get("/admin/dashboard")
        assert response.status_code == 403

    def test_audit_403s_for_authenticated_non_admin(self, client):
        _authenticate_as_non_admin()
        with patch("src.api.deps._platform_admin_service.is_super_admin", return_value=False):
            response = client.get("/admin/audit")
        assert response.status_code == 403


class TestWorkspaceAdminAccess:
    """Phase 28 — a workspace_admin (not a super admin) can now reach the
    per-workspace read/edit routes for their OWN workspace, but not a
    different one, and still can't reach cross-tenant/lifecycle routes."""

    def test_workspace_admin_can_get_their_own_workspace(self, client):
        _authenticate_as_non_admin()
        with patch("src.api.deps._platform_admin_service.is_super_admin", return_value=False), \
             patch("src.api.deps._workspace_admin_service.is_workspace_admin", return_value=True), \
             patch("src.api.routes.admin_workspaces._tenant_service.get_workspace", return_value=_workspace()):
            response = client.get("/admin/workspaces/w1")

        assert response.status_code == 200

    def test_workspace_admin_403s_for_a_different_workspace(self, client):
        _authenticate_as_non_admin()
        with patch("src.api.deps._platform_admin_service.is_super_admin", return_value=False), \
             patch("src.api.deps._workspace_admin_service.is_workspace_admin", return_value=False):
            response = client.get("/admin/workspaces/w2")

        assert response.status_code == 403

    def test_workspace_admin_can_regenerate_own_api_key(self, client):
        _authenticate_as_non_admin()
        with patch("src.api.deps._platform_admin_service.is_super_admin", return_value=False), \
             patch("src.api.deps._workspace_admin_service.is_workspace_admin", return_value=True), \
             patch("src.api.routes.admin_workspaces._tenant_service.get_workspace", return_value=_workspace()), \
             patch(
                 "src.api.routes.admin_workspaces._tenant_service.regenerate_api_key",
                 return_value="new-key",
             ):
            response = client.post("/admin/workspaces/w1/apikey/regenerate")

        assert response.status_code == 200

    def test_workspace_admin_still_403s_on_suspend(self, client):
        """Destructive lifecycle actions stay super-admin-only even for
        this workspace's own admin."""
        _authenticate_as_non_admin()
        with patch("src.api.deps._platform_admin_service.is_super_admin", return_value=False):
            response = client.post("/admin/workspaces/w1/suspend")

        assert response.status_code == 403

    def test_workspace_admin_still_403s_on_list_all_workspaces(self, client):
        _authenticate_as_non_admin()
        with patch("src.api.deps._platform_admin_service.is_super_admin", return_value=False):
            response = client.get("/admin/workspaces")

        assert response.status_code == 403


class TestWorkspaceCrud:
    def test_list_workspaces_succeeds_for_admin(self, client):
        _authenticate_as_admin()
        with patch(
            "src.api.routes.admin_workspaces._tenant_service.list_workspaces", return_value=[_workspace()]
        ):
            response = client.get("/admin/workspaces")

        assert response.status_code == 200
        assert response.json()[0]["slug"] == "acme"

    def test_create_workspace_returns_raw_api_key_once(self, client):
        _authenticate_as_admin()
        with patch(
            "src.api.routes.admin_workspaces._tenant_service.create_workspace",
            return_value=_workspace(api_key="brand-new-key"),
        ):
            response = client.post("/admin/workspaces", json={"slug": "acme", "name": "Acme"})

        assert response.status_code == 200
        assert response.json()["api_key"] == "brand-new-key"

    def test_create_workspace_duplicate_slug_returns_400_not_500(self, client):
        _authenticate_as_admin()
        with patch(
            "src.api.routes.admin_workspaces._tenant_service.create_workspace",
            side_effect=ValueError("Workspace slug 'acme' already exists"),
        ):
            response = client.post("/admin/workspaces", json={"slug": "acme", "name": "Acme"})

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_get_workspace_404s_when_missing(self, client):
        _authenticate_as_admin()
        with patch("src.api.routes.admin_workspaces._tenant_service.get_workspace", return_value=None):
            response = client.get("/admin/workspaces/missing")

        assert response.status_code == 404

    def test_suspend_and_reactivate(self, client):
        _authenticate_as_admin()
        with patch("src.api.routes.admin_workspaces._tenant_service.get_workspace", return_value=_workspace()), \
             patch(
                 "src.api.routes.admin_workspaces._tenant_service.suspend",
                 return_value=_workspace(is_active=False),
             ):
            response = client.post("/admin/workspaces/w1/suspend")
        assert response.status_code == 200
        assert response.json()["is_active"] is False

        with patch("src.api.routes.admin_workspaces._tenant_service.get_workspace", return_value=_workspace()), \
             patch(
                 "src.api.routes.admin_workspaces._tenant_service.reactivate",
                 return_value=_workspace(is_active=True),
             ):
            response = client.post("/admin/workspaces/w1/reactivate")
        assert response.status_code == 200
        assert response.json()["is_active"] is True

    def test_regenerate_api_key_response_never_contains_old_key(self, client):
        _authenticate_as_admin()
        with patch("src.api.routes.admin_workspaces._tenant_service.get_workspace", return_value=_workspace()), \
             patch(
                 "src.api.routes.admin_workspaces._tenant_service.regenerate_api_key",
                 return_value="fresh-key-abc",
             ):
            response = client.post("/admin/workspaces/w1/apikey/regenerate")

        assert response.status_code == 200
        assert response.json() == {"api_key": "fresh-key-abc"}


class TestBrandingSettingsProductsFlags:
    def test_update_branding(self, client):
        _authenticate_as_admin()
        with patch("src.api.routes.admin_workspaces._tenant_service.get_workspace", return_value=_workspace()), \
             patch(
                 "src.api.routes.admin_workspaces._tenant_service.update_branding",
                 return_value=_workspace(logo="https://x.com/logo.png"),
             ) as mock_update:
            response = client.patch(
                "/admin/workspaces/w1/branding", json={"logo": "https://x.com/logo.png"}
            )

        assert response.status_code == 200
        assert response.json()["logo"] == "https://x.com/logo.png"
        mock_update.assert_called_once_with("w1", "admin-1", logo="https://x.com/logo.png")

    def test_update_products_rejects_unknown_product(self, client):
        _authenticate_as_admin()
        with patch("src.api.routes.admin_workspaces._tenant_service.get_workspace", return_value=_workspace()), \
             patch(
                 "src.api.routes.admin_workspaces._product_service.set_enabled",
                 side_effect=ValueError("Unknown product_id: Nope"),
             ):
            response = client.patch(
                "/admin/workspaces/w1/products", json={"products": [{"product_id": "Nope", "enabled": True}]}
            )

        assert response.status_code == 400

    def test_update_flags(self, client):
        _authenticate_as_admin()
        flag = MagicMock(flag_key="ai_copilot", enabled=True)
        with patch("src.api.routes.admin_workspaces._tenant_service.get_workspace", return_value=_workspace()), \
             patch("src.api.routes.admin_workspaces._feature_flag_service.set_flag", return_value=flag), \
             patch("src.api.routes.admin_workspaces._audit_service.record"):
            response = client.patch(
                "/admin/workspaces/w1/flags", json={"flags": [{"flag_key": "ai_copilot", "enabled": True}]}
            )

        assert response.status_code == 200
        assert response.json()[0]["flag_key"] == "ai_copilot"


class TestDashboardAndAudit:
    def test_dashboard_returns_stats(self, client):
        _authenticate_as_admin()
        stats = {
            "total_workspace_count": 3, "active_workspace_count": 2,
            "total_conversation_count": 10, "total_escalation_count": 4, "total_agent_count": 5,
        }
        with patch("src.api.routes.admin_workspaces._tenant_service.platform_dashboard", return_value=stats):
            response = client.get("/admin/dashboard")

        assert response.status_code == 200
        assert response.json() == stats

    def test_audit_log_listing(self, client):
        _authenticate_as_admin()
        entry = MagicMock(
            id="a1", workspace_id="w1", actor_auth_user_id="admin-1",
            action="workspace.created", metadata={}, created_at=None,
        )
        with patch("src.api.routes.admin_workspaces._audit_service.list_recent", return_value=[entry]):
            response = client.get("/admin/audit")

        assert response.status_code == 200
        assert response.json()[0]["action"] == "workspace.created"

    def test_audit_log_listing_threads_filter_params(self, client):
        _authenticate_as_admin()
        with patch("src.api.routes.admin_workspaces._audit_service.list_recent", return_value=[]) as mock_list:
            response = client.get(
                "/admin/audit",
                params={
                    "workspace_id": "w1", "action": "workspace.archived", "actor_auth_user_id": "admin-1",
                    "start_date": "2026-01-01", "end_date": "2026-01-31", "limit": 50,
                },
            )

        assert response.status_code == 200
        mock_list.assert_called_once_with(
            workspace_id="w1", limit=50, action="workspace.archived", actor_auth_user_id="admin-1",
            start_date="2026-01-01", end_date="2026-01-31",
        )


_REPORT_FIXTURE = {
    "conversation_count": 10, "escalation_count": 4,
    "escalation_status_breakdown": {
        "waiting": 0, "assigned": 0, "active": 0, "waiting_for_customer": 0, "resolved": 1, "closed": 1,
    },
    "appointment_count": 0, "saved_recommendation_count": 0, "saved_comparison_count": 0,
    "feedback_helpful_count": 0, "feedback_not_helpful_count": 0,
    "resolution_rate": 0.5, "average_resolution_minutes": 45.0,
    "department_activity": {"Support": 2}, "frustrated_conversation_count": 1,
    "agents": [{"id": "a1", "name": "Ada", "department": "Support", "status": "available", "current_workload": 2}],
    "requested_products": {"SPIDIFY": 2}, "ai_resolved_rate_estimate": 0.8,
    "ai_resolved_rate_caveat": "Approximate.",
    "knowledge_gaps": None, "frequently_searched_topics": None,
    "insufficient_evidence_questions": None, "source_failures": None,
    "knowledge_tracking_note": "Not tracked yet.",
}


class TestWorkspaceReportAndAnalyst:
    def test_report_requires_workspace_admin(self, client):
        response = client.get("/admin/workspaces/w1/report")
        assert response.status_code == 401

    def test_report_returns_extended_metrics(self, client):
        _authenticate_as_admin()
        with patch("src.api.routes.admin_workspaces._tenant_service.get_workspace", return_value=_workspace()), \
             patch(
                 "src.api.routes.admin_workspaces._tenant_analytics_service.workspace_operational_report",
                 return_value=_REPORT_FIXTURE,
             ) as mock_report:
            response = client.get("/admin/workspaces/w1/report")

        assert response.status_code == 200
        assert response.json()["resolution_rate"] == 0.5
        assert response.json()["knowledge_gaps"] is None
        mock_report.assert_called_once_with("w1")

    def test_report_404s_for_unknown_workspace(self, client):
        _authenticate_as_admin()
        with patch("src.api.routes.admin_workspaces._tenant_service.get_workspace", return_value=None):
            response = client.get("/admin/workspaces/w1/report")

        assert response.status_code == 404

    def test_ask_requires_workspace_admin(self, client):
        response = client.post("/admin/workspaces/w1/ask", json={"question": "How did we do?"})
        assert response.status_code == 401

    def test_ask_returns_grounded_answer(self, client):
        _authenticate_as_admin()
        with patch("src.api.routes.admin_workspaces._tenant_service.get_workspace", return_value=_workspace()), \
             patch(
                 "src.api.routes.admin_workspaces.answer_question",
                 return_value={"answer": "FACT: 4 escalations this week."},
             ) as mock_ask:
            response = client.post("/admin/workspaces/w1/ask", json={"question": "How did support perform?"})

        assert response.status_code == 200
        assert response.json()["answer"] == "FACT: 4 escalations this week."
        mock_ask.assert_called_once_with(
            "w1", "How did support perform?", analytics_service=ANY,
        )

    def test_ask_404s_for_unknown_workspace(self, client):
        _authenticate_as_admin()
        with patch("src.api.routes.admin_workspaces._tenant_service.get_workspace", return_value=None):
            response = client.post("/admin/workspaces/w1/ask", json={"question": "How did we do?"})

        assert response.status_code == 404
