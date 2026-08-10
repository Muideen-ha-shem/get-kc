"""TenantService — workspace/tenant administration (Phase 26).

Wraps AdminWorkspaceRepository + TenantAnalyticsService + AuditService.
Every mutating method logs an audit event. Branding is folded in here
(not a separate branding_service.py) — both write the identical
`workspaces` row through the identical client, so a second service would
just duplicate the write path.
"""

from __future__ import annotations

from .admin_models import AdminWorkspace
from .audit_service import AuditService
from .tenant_analytics_service import TenantAnalyticsService
from .tenant_repository import AdminWorkspaceRepository


class TenantService:
    def __init__(
        self,
        repository: AdminWorkspaceRepository | None = None,
        analytics: TenantAnalyticsService | None = None,
        audit: AuditService | None = None,
    ) -> None:
        self._repo = repository or AdminWorkspaceRepository()
        self._analytics = analytics or TenantAnalyticsService()
        self._audit = audit or AuditService()

    def list_workspaces(self) -> list[AdminWorkspace]:
        return self._repo.list_all()

    def get_workspace(self, workspace_id: str) -> AdminWorkspace | None:
        return self._repo.get_by_id(workspace_id)

    def create_workspace(
        self,
        slug: str,
        name: str,
        host: str | None,
        actor_auth_user_id: str,
        owner_auth_user_id: str | None = None,
        plan: str = "free",
    ) -> AdminWorkspace:
        workspace = self._repo.create(slug, name, host, owner_auth_user_id=owner_auth_user_id, plan=plan)
        self._audit.record("workspace.created", actor_auth_user_id, workspace.id, {"slug": slug, "name": name})
        return workspace

    def suspend(self, workspace_id: str, actor_auth_user_id: str) -> AdminWorkspace:
        workspace = self._repo.set_active(workspace_id, False)
        self._audit.record("workspace.suspended", actor_auth_user_id, workspace_id, {})
        return workspace

    def reactivate(self, workspace_id: str, actor_auth_user_id: str) -> AdminWorkspace:
        workspace = self._repo.set_active(workspace_id, True)
        self._audit.record("workspace.reactivated", actor_auth_user_id, workspace_id, {})
        return workspace

    def archive(self, workspace_id: str, actor_auth_user_id: str) -> AdminWorkspace:
        workspace = self._repo.archive(workspace_id)
        self._audit.record("workspace.archived", actor_auth_user_id, workspace_id, {})
        return workspace

    def soft_delete(self, workspace_id: str, actor_auth_user_id: str) -> AdminWorkspace:
        workspace = self._repo.soft_delete(workspace_id)
        self._audit.record("workspace.deleted", actor_auth_user_id, workspace_id, {})
        return workspace

    def update_branding(self, workspace_id: str, actor_auth_user_id: str, **fields) -> AdminWorkspace:
        workspace = self._repo.update_branding(workspace_id, **fields)
        self._audit.record("workspace.branding_changed", actor_auth_user_id, workspace_id, fields)
        return workspace

    def regenerate_api_key(self, workspace_id: str, actor_auth_user_id: str) -> str:
        new_key = self._repo.regenerate_api_key(workspace_id)
        self._audit.record("workspace.apikey_regenerated", actor_auth_user_id, workspace_id, {})
        return new_key

    def workspace_analytics(self, workspace_id: str) -> dict:
        return self._analytics.workspace_stats(workspace_id)

    def platform_dashboard(self) -> dict:
        workspaces = self._repo.list_all()
        return self._analytics.platform_dashboard_stats(workspaces)
