"""Workspace/tenant management routes (Phase 26, extended Phase 28).

Cross-tenant and destructive-lifecycle routes (list all, create, suspend/
reactivate/archive/delete, platform dashboard, audit, feature flags)
depend on `require_super_admin` only. Per-workspace read/edit routes
(get/analytics/branding/settings/products/api-key) additionally accept a
matching `workspace_admin` (Phase 28) — a self-service org owner manages
their own workspace's settings the same way a super admin would, just
scoped to that one workspace. `require_workspace_admin` already allows
either; widening these routes to it is a strict widening (super admins
still pass everywhere), never a narrowing.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ...services.admin.audit_service import AuditService
from ...services.admin.feature_flag_service import FeatureFlagService
from ...services.admin.product_service import ProductService
from ...services.admin.settings_service import SettingsService
from ...services.admin.tenant_analytics_service import TenantAnalyticsService
from ...services.admin.tenant_service import TenantService
from ...services.admin.workspace_analyst import answer_question
from ...services.admin.workspace_deletion_service import (
    WorkspaceDeletionConfirmationError,
    WorkspaceHardDeleteService,
)
from ...services.auth.auth_service import AuthUser
from ..deps import require_super_admin, require_workspace_admin
from ..schemas_admin import (
    ApiKeyRegenerateResponse,
    AuditLogEntrySchema,
    FeatureFlagSchema,
    FeatureFlagsUpdateRequest,
    PlatformDashboardSchema,
    WorkspaceAdminSchema,
    WorkspaceAnalyticsSchema,
    WorkspaceAskRequest,
    WorkspaceAskResponseSchema,
    WorkspaceBrandingUpdateRequest,
    WorkspaceCreateRequest,
    WorkspaceCreateResponse,
    WorkspaceHardDeleteRequest,
    WorkspaceProductSchema,
    WorkspaceProductsUpdateRequest,
    WorkspaceReportSchema,
    WorkspaceSettingsSchema,
    WorkspaceSettingsUpdateRequest,
)

router = APIRouter()

_tenant_service = TenantService()
_tenant_analytics_service = TenantAnalyticsService()
_settings_service = SettingsService()
_feature_flag_service = FeatureFlagService()
_product_service = ProductService()
_audit_service = AuditService()
_workspace_deletion_service = WorkspaceHardDeleteService()


def _to_workspace_schema(workspace) -> WorkspaceAdminSchema:
    return WorkspaceAdminSchema(
        id=workspace.id, slug=workspace.slug, name=workspace.name, host=workspace.host,
        is_active=workspace.is_active, logo=workspace.logo, primary_color=workspace.primary_color,
        welcome_message=workspace.welcome_message, quick_actions=workspace.quick_actions,
        archived_at=workspace.archived_at, deleted_at=workspace.deleted_at,
        created_at=workspace.created_at, updated_at=workspace.updated_at,
        owner_auth_user_id=workspace.owner_auth_user_id, plan=workspace.plan,
    )


def _to_settings_schema(settings) -> WorkspaceSettingsSchema:
    return WorkspaceSettingsSchema(
        workspace_id=settings.workspace_id,
        ai_enabled=settings.ai_enabled,
        confidence_threshold=settings.confidence_threshold,
        live_search_enabled=settings.live_search_enabled,
        human_escalation_enabled=settings.human_escalation_enabled,
        ai_personality=settings.ai_personality,
        welcome_prompt=settings.welcome_prompt,
        chat_enabled=settings.chat_enabled,
        offline_mode=settings.offline_mode,
        greeting_message=settings.greeting_message,
        working_hours=settings.working_hours,
        escalation_timeout_minutes=settings.escalation_timeout_minutes,
        auto_assignment_enabled=settings.auto_assignment_enabled,
        secondary_color=settings.secondary_color,
        chat_avatar=settings.chat_avatar,
        company_name=settings.company_name,
        footer_text=settings.footer_text,
    )


def _get_workspace_or_404(workspace_id: str):
    workspace = _tenant_service.get_workspace(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.get("/admin/me")
def get_admin_me(user: AuthUser = Depends(require_super_admin)) -> dict:
    return {"is_super_admin": True, "auth_user_id": user.id}


@router.get("/admin/workspaces", response_model=list[WorkspaceAdminSchema])
def list_workspaces(user: AuthUser = Depends(require_super_admin)) -> list[WorkspaceAdminSchema]:
    return [_to_workspace_schema(w) for w in _tenant_service.list_workspaces()]


@router.post("/admin/workspaces", response_model=WorkspaceCreateResponse)
def create_workspace(
    request: WorkspaceCreateRequest, user: AuthUser = Depends(require_super_admin)
) -> WorkspaceCreateResponse:
    try:
        workspace = _tenant_service.create_workspace(request.slug, request.name, request.host, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return WorkspaceCreateResponse(workspace=_to_workspace_schema(workspace), api_key=workspace.api_key)


@router.get("/admin/workspaces/{workspace_id}", response_model=WorkspaceAdminSchema)
def get_workspace(workspace_id: str, user: AuthUser = Depends(require_workspace_admin)) -> WorkspaceAdminSchema:
    return _to_workspace_schema(_get_workspace_or_404(workspace_id))


@router.get("/admin/workspaces/{workspace_id}/analytics", response_model=WorkspaceAnalyticsSchema)
def get_workspace_analytics(
    workspace_id: str, user: AuthUser = Depends(require_workspace_admin)
) -> WorkspaceAnalyticsSchema:
    _get_workspace_or_404(workspace_id)
    return WorkspaceAnalyticsSchema(**_tenant_service.workspace_analytics(workspace_id))


@router.get("/admin/workspaces/{workspace_id}/report", response_model=WorkspaceReportSchema)
def get_workspace_report(
    workspace_id: str, user: AuthUser = Depends(require_workspace_admin)
) -> WorkspaceReportSchema:
    """Extends the basic analytics above with resolution rate/timing, a
    per-agent breakdown, and customer/AI trend signals — see
    TenantAnalyticsService.workspace_operational_report()."""
    _get_workspace_or_404(workspace_id)
    return WorkspaceReportSchema(**_tenant_analytics_service.workspace_operational_report(workspace_id))


@router.post("/admin/workspaces/{workspace_id}/ask", response_model=WorkspaceAskResponseSchema)
def ask_workspace_analyst(
    workspace_id: str, request: WorkspaceAskRequest, user: AuthUser = Depends(require_workspace_admin)
) -> WorkspaceAskResponseSchema:
    """"Ask HavisIQ" — answers grounded in this workspace's real
    operational metrics, never another workspace's (workspace_id is
    require_workspace_admin's own resolved value, never accepted as
    free-form input beyond that)."""
    _get_workspace_or_404(workspace_id)
    result = answer_question(workspace_id, request.question, analytics_service=_tenant_analytics_service)
    return WorkspaceAskResponseSchema(answer=result["answer"])


@router.patch("/admin/workspaces/{workspace_id}/branding", response_model=WorkspaceAdminSchema)
def update_workspace_branding(
    workspace_id: str, request: WorkspaceBrandingUpdateRequest, user: AuthUser = Depends(require_workspace_admin)
) -> WorkspaceAdminSchema:
    _get_workspace_or_404(workspace_id)
    fields = {k: v for k, v in request.model_dump().items() if v is not None}
    workspace = _tenant_service.update_branding(workspace_id, user.id, **fields)
    return _to_workspace_schema(workspace)


@router.get("/admin/workspaces/{workspace_id}/settings", response_model=WorkspaceSettingsSchema)
def get_workspace_settings(
    workspace_id: str, user: AuthUser = Depends(require_workspace_admin)
) -> WorkspaceSettingsSchema:
    _get_workspace_or_404(workspace_id)
    settings = _settings_service.get(workspace_id)
    return _to_settings_schema(settings)


@router.patch("/admin/workspaces/{workspace_id}/settings", response_model=WorkspaceSettingsSchema)
def update_workspace_settings(
    workspace_id: str, request: WorkspaceSettingsUpdateRequest, user: AuthUser = Depends(require_workspace_admin)
) -> WorkspaceSettingsSchema:
    _get_workspace_or_404(workspace_id)
    fields = {k: v for k, v in request.model_dump().items() if v is not None}
    settings = _settings_service.update(workspace_id, **fields)
    _audit_service.record("workspace.settings_changed", user.id, workspace_id, fields)
    return _to_settings_schema(settings)


@router.get("/admin/workspaces/{workspace_id}/products", response_model=list[WorkspaceProductSchema])
def get_workspace_products(
    workspace_id: str, user: AuthUser = Depends(require_workspace_admin)
) -> list[WorkspaceProductSchema]:
    _get_workspace_or_404(workspace_id)
    return [
        WorkspaceProductSchema(product_id=p.product_id, enabled=p.enabled)
        for p in _product_service.list_for_workspace(workspace_id)
    ]


@router.patch("/admin/workspaces/{workspace_id}/products", response_model=list[WorkspaceProductSchema])
def update_workspace_products(
    workspace_id: str, request: WorkspaceProductsUpdateRequest, user: AuthUser = Depends(require_workspace_admin)
) -> list[WorkspaceProductSchema]:
    _get_workspace_or_404(workspace_id)
    updated = []
    for item in request.products:
        try:
            flag = _product_service.set_enabled(workspace_id, item.product_id, item.enabled)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        updated.append(WorkspaceProductSchema(product_id=flag.product_id, enabled=flag.enabled))
    _audit_service.record(
        "workspace.products_changed", user.id, workspace_id,
        {"products": [p.model_dump() for p in request.products]},
    )
    return updated


@router.get("/admin/workspaces/{workspace_id}/flags", response_model=list[FeatureFlagSchema])
def get_workspace_flags(
    workspace_id: str, user: AuthUser = Depends(require_super_admin)
) -> list[FeatureFlagSchema]:
    _get_workspace_or_404(workspace_id)
    return [
        FeatureFlagSchema(flag_key=f.flag_key, enabled=f.enabled)
        for f in _feature_flag_service.list_for_workspace(workspace_id)
    ]


@router.patch("/admin/workspaces/{workspace_id}/flags", response_model=list[FeatureFlagSchema])
def update_workspace_flags(
    workspace_id: str, request: FeatureFlagsUpdateRequest, user: AuthUser = Depends(require_super_admin)
) -> list[FeatureFlagSchema]:
    _get_workspace_or_404(workspace_id)
    updated = []
    for item in request.flags:
        flag = _feature_flag_service.set_flag(workspace_id, item.flag_key, item.enabled)
        updated.append(FeatureFlagSchema(flag_key=flag.flag_key, enabled=flag.enabled))
    _audit_service.record(
        "workspace.flags_changed", user.id, workspace_id, {"flags": [f.model_dump() for f in request.flags]}
    )
    return updated


@router.post("/admin/workspaces/{workspace_id}/apikey/regenerate", response_model=ApiKeyRegenerateResponse)
def regenerate_workspace_api_key(
    workspace_id: str, user: AuthUser = Depends(require_workspace_admin)
) -> ApiKeyRegenerateResponse:
    _get_workspace_or_404(workspace_id)
    new_key = _tenant_service.regenerate_api_key(workspace_id, user.id)
    return ApiKeyRegenerateResponse(api_key=new_key)


@router.post("/admin/workspaces/{workspace_id}/suspend", response_model=WorkspaceAdminSchema)
def suspend_workspace(workspace_id: str, user: AuthUser = Depends(require_super_admin)) -> WorkspaceAdminSchema:
    _get_workspace_or_404(workspace_id)
    return _to_workspace_schema(_tenant_service.suspend(workspace_id, user.id))


@router.post("/admin/workspaces/{workspace_id}/reactivate", response_model=WorkspaceAdminSchema)
def reactivate_workspace(workspace_id: str, user: AuthUser = Depends(require_super_admin)) -> WorkspaceAdminSchema:
    _get_workspace_or_404(workspace_id)
    return _to_workspace_schema(_tenant_service.reactivate(workspace_id, user.id))


@router.post("/admin/workspaces/{workspace_id}/archive", response_model=WorkspaceAdminSchema)
def archive_workspace(workspace_id: str, user: AuthUser = Depends(require_super_admin)) -> WorkspaceAdminSchema:
    _get_workspace_or_404(workspace_id)
    return _to_workspace_schema(_tenant_service.archive(workspace_id, user.id))


@router.post("/admin/workspaces/{workspace_id}/delete", response_model=WorkspaceAdminSchema)
def soft_delete_workspace(workspace_id: str, user: AuthUser = Depends(require_super_admin)) -> WorkspaceAdminSchema:
    _get_workspace_or_404(workspace_id)
    return _to_workspace_schema(_tenant_service.soft_delete(workspace_id, user.id))


@router.post("/admin/workspaces/{workspace_id}/hard-delete", status_code=204)
def hard_delete_workspace(
    workspace_id: str, body: WorkspaceHardDeleteRequest, user: AuthUser = Depends(require_super_admin)
) -> None:
    """Irreversibly deletes the workspace and every row it owns — gated
    behind confirm_name matching the workspace's current name exactly.
    Separate from the reversible soft-delete route above, which stays
    untouched; the frontend's Delete button now calls this one instead."""
    _get_workspace_or_404(workspace_id)
    try:
        _workspace_deletion_service.hard_delete(workspace_id, body.confirm_name, user.id)
    except WorkspaceDeletionConfirmationError:
        raise HTTPException(status_code=400, detail="Workspace name confirmation did not match.")


@router.get("/admin/dashboard", response_model=PlatformDashboardSchema)
def get_admin_dashboard(user: AuthUser = Depends(require_super_admin)) -> PlatformDashboardSchema:
    return PlatformDashboardSchema(**_tenant_service.platform_dashboard())


@router.get("/admin/audit", response_model=list[AuditLogEntrySchema])
def get_audit_log(
    workspace_id: str | None = None,
    action: str | None = None,
    actor_auth_user_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 100,
    user: AuthUser = Depends(require_super_admin),
) -> list[AuditLogEntrySchema]:
    entries = _audit_service.list_recent(
        workspace_id=workspace_id, limit=limit, action=action, actor_auth_user_id=actor_auth_user_id,
        start_date=start_date, end_date=end_date,
    )
    return [
        AuditLogEntrySchema(
            id=e.id, workspace_id=e.workspace_id, actor_auth_user_id=e.actor_auth_user_id,
            action=e.action, metadata=e.metadata, created_at=e.created_at,
        )
        for e in entries
    ]
