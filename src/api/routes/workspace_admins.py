"""`GET /workspace-admins/me` (Phase 28) — lets the signed-in customer
dashboard discover which workspace(s), if any, the current user
administers, so it can show a "Workspace Admin" nav link. Distinct from
`/admin/me` (platform Super Admin only) and `/agents/me` (support-agent
identity) — this is the workspace_admin equivalent of both.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ...services.admin.tenant_repository import AdminWorkspaceRepository
from ...services.admin.workspace_admin_service import WorkspaceAdminService
from ...services.auth.auth_service import AuthUser
from ..deps import get_current_user_required

router = APIRouter()

_workspace_admin_service = WorkspaceAdminService()
_workspace_repository = AdminWorkspaceRepository()


@router.get("/workspace-admins/me")
def get_my_workspace_admin_memberships(user: AuthUser = Depends(get_current_user_required)) -> dict:
    workspace_ids = _workspace_admin_service.list_workspace_ids_for_admin(user.id)
    workspaces = []
    for workspace_id in workspace_ids:
        workspace = _workspace_repository.get_by_id(workspace_id)
        if workspace is not None:
            workspaces.append({"id": workspace.id, "slug": workspace.slug, "name": workspace.name})
    return {"workspaces": workspaces}
