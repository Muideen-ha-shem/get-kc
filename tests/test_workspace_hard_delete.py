"""Tests for WorkspaceHardDeleteService and the
POST /admin/workspaces/{id}/hard-delete route — mirrors
test_admin_workspace_routes.py's dependency-override + patched-singleton
pattern for the route layer, plus direct MagicMock-client unit tests for
the service's deletion order/audit/failure behavior."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.deps import get_current_user_required, require_super_admin
from src.services.admin.workspace_deletion_service import (
    WorkspaceDeletionConfirmationError,
    WorkspaceHardDeleteService,
)
from src.services.auth.auth_service import AuthUser

_FAKE_ADMIN = AuthUser(id="admin-1", email="admin@example.com", full_name="Admin")
_FAKE_NON_ADMIN = AuthUser(id="u2", email="customer@example.com", full_name="Customer")

_GROUP_B_TABLES = (
    "conversation_messages", "message_feedback", "conversations", "saved_recommendations",
    "saved_comparisons", "notifications", "appointments", "customer_profiles", "documentation_chunks",
)


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _workspace(**overrides):
    base = MagicMock(id="w1", slug="acme")
    base.configure_mock(name="Acme")
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


class TestServiceDeletionOrder:
    """Direct unit tests against WorkspaceHardDeleteService, bypassing the
    route layer, so we can assert exactly which tables were touched."""

    def _make_service(self, workspace=None):
        client = MagicMock()
        repo = MagicMock()
        repo.get_by_id.return_value = workspace or _workspace()
        audit = MagicMock()
        service = WorkspaceHardDeleteService(client=client, repo=repo, audit=audit)
        return service, client, repo, audit

    def test_confirmation_mismatch_raises_before_any_delete(self):
        service, client, _repo, audit = self._make_service()

        with pytest.raises(WorkspaceDeletionConfirmationError):
            service.hard_delete("w1", "Wrong Name", "admin-1")

        client.table.assert_not_called()
        audit.record.assert_not_called()

    def test_happy_path_deletes_exactly_the_nine_group_b_tables_then_workspace_last(self):
        service, client, _repo, _audit = self._make_service()

        service.hard_delete("w1", "Acme", "admin-1")

        called_tables = [call.args[0] for call in client.table.call_args_list]
        assert called_tables == list(_GROUP_B_TABLES) + ["workspaces"]

        # Every Group B call filters by workspace_id; the final workspaces
        # call filters by id, not workspace_id.
        for table in _GROUP_B_TABLES:
            client.table.return_value.delete.return_value.eq.assert_any_call("workspace_id", "w1")

    def test_never_touches_group_a_cascade_covered_tables(self):
        service, client, _repo, _audit = self._make_service()

        service.hard_delete("w1", "Acme", "admin-1")

        called_tables = {call.args[0] for call in client.table.call_args_list}
        for group_a_table in ("knowledge_documents", "knowledge_sources", "escalations", "support_agents"):
            assert group_a_table not in called_tables

    def test_writes_final_audit_entry_with_null_workspace_id(self):
        service, _client, _repo, audit = self._make_service()

        service.hard_delete("w1", "Acme", "admin-1")

        audit.record.assert_called_once_with(
            "workspace.hard_deleted", "admin-1", None,
            {"deleted_workspace_id": "w1", "slug": "acme", "name": "Acme"},
        )

    def test_audit_written_after_workspace_row_delete(self):
        service, client, _repo, audit = self._make_service()
        call_order = []
        client.table.side_effect = lambda name: (call_order.append(("table", name)), MagicMock())[1]
        audit.record.side_effect = lambda *a, **k: call_order.append(("audit",))

        service.hard_delete("w1", "Acme", "admin-1")

        assert call_order[-2] == ("table", "workspaces")
        assert call_order[-1] == ("audit",)

    def test_stops_on_first_failure(self):
        service, client, _repo, audit = self._make_service()

        def side_effect(name):
            table_mock = MagicMock()
            if name == _GROUP_B_TABLES[2]:
                table_mock.delete.return_value.eq.return_value.execute.side_effect = RuntimeError("boom")
            return table_mock

        client.table.side_effect = side_effect

        with pytest.raises(RuntimeError):
            service.hard_delete("w1", "Acme", "admin-1")

        called_tables = [call.args[0] for call in client.table.call_args_list]
        # Exactly the tables up to and including the failing one were
        # attempted — nothing after it, and workspaces/audit never reached.
        assert called_tables == list(_GROUP_B_TABLES[:3])
        audit.record.assert_not_called()

    def test_workspace_not_found_raises_value_error(self):
        service, client, repo, audit = self._make_service()
        repo.get_by_id.return_value = None

        with pytest.raises(ValueError):
            service.hard_delete("missing", "Anything", "admin-1")

        client.table.assert_not_called()
        audit.record.assert_not_called()


class TestHardDeleteRoute:
    def _authenticate_as_admin(self):
        app.dependency_overrides[require_super_admin] = lambda: _FAKE_ADMIN
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_ADMIN

    def test_401s_with_no_auth_at_all(self, client):
        response = client.post("/admin/workspaces/w1/hard-delete", json={"confirm_name": "Acme"})
        assert response.status_code == 401

    def test_403s_for_authenticated_non_admin(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_NON_ADMIN
        with patch("src.api.deps._platform_admin_service.is_super_admin", return_value=False):
            response = client.post("/admin/workspaces/w1/hard-delete", json={"confirm_name": "Acme"})
        assert response.status_code == 403

    def test_404s_when_workspace_missing(self, client):
        self._authenticate_as_admin()
        with patch("src.api.routes.admin_workspaces._tenant_service.get_workspace", return_value=None):
            response = client.post("/admin/workspaces/missing/hard-delete", json={"confirm_name": "Acme"})
        assert response.status_code == 404

    def test_400s_on_confirmation_mismatch_and_service_not_left_partially_run(self, client):
        self._authenticate_as_admin()
        with (
            patch("src.api.routes.admin_workspaces._tenant_service.get_workspace", return_value=_workspace()),
            patch(
                "src.api.routes.admin_workspaces._workspace_deletion_service.hard_delete",
                side_effect=WorkspaceDeletionConfirmationError("mismatch"),
            ) as mock_hard_delete,
        ):
            response = client.post("/admin/workspaces/w1/hard-delete", json={"confirm_name": "Wrong"})

        assert response.status_code == 400
        mock_hard_delete.assert_called_once_with("w1", "Wrong", "admin-1")

    def test_204_on_success(self, client):
        self._authenticate_as_admin()
        with (
            patch("src.api.routes.admin_workspaces._tenant_service.get_workspace", return_value=_workspace()),
            patch("src.api.routes.admin_workspaces._workspace_deletion_service.hard_delete") as mock_hard_delete,
        ):
            response = client.post("/admin/workspaces/w1/hard-delete", json={"confirm_name": "Acme"})

        assert response.status_code == 204
        mock_hard_delete.assert_called_once_with("w1", "Acme", "admin-1")
