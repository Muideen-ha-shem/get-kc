"""Super Admin user/agent/role management routes (Phase 26).

User suspend/reactivate/list reuse Supabase's Admin Auth API via a
locally-constructed admin (service-role) client — never the module-level
anon-keyed AuthService used everywhere else in the app.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ...sb import get_admin_client
from ...services.admin.audit_service import AuditService
from ...services.admin.platform_admin_service import PlatformAdminService
from ...services.admin.workspace_admin_service import WorkspaceAdminService
from ...services.agents.agent_service import AgentService
from ...services.auth.auth_service import AuthService, AuthUser
from ...services.escalation.escalation_repository import EscalationRepository
from ..deps import require_super_admin
from ..routes.auth import _password_reset_redirect_url
from ..schemas import SupportAgentSchema
from ..schemas_admin import AdminUserSchema, AgentPerformanceSchema, RoleAssignmentRequest

router = APIRouter()

_agent_service = AgentService()
_platform_admin_service = PlatformAdminService()
_workspace_admin_service = WorkspaceAdminService()
_audit_service = AuditService()
_escalation_repository = EscalationRepository()


def _to_agent_schema(agent) -> SupportAgentSchema:
    return SupportAgentSchema(
        id=agent.id, workspace_id=agent.workspace_id, name=agent.name, email=agent.email,
        department=agent.department, status=agent.status, created_at=agent.created_at,
    )


@router.get("/admin/users", response_model=list[AdminUserSchema])
def list_users(user: AuthUser = Depends(require_super_admin)) -> list[AdminUserSchema]:
    admin_auth = AuthService(client=get_admin_client())
    try:
        users = admin_auth.admin_list_users()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to list users — check SUPABASE_SERVICE_ROLE_KEY is configured.",
        ) from exc
    return [AdminUserSchema(id=u.id, email=u.email, full_name=u.full_name) for u in users]


@router.post("/admin/users/{auth_user_id}/suspend")
def suspend_user(auth_user_id: str, user: AuthUser = Depends(require_super_admin)) -> dict[str, str]:
    admin_auth = AuthService(client=get_admin_client())
    try:
        admin_auth.admin_suspend_user(auth_user_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to suspend user — check SUPABASE_SERVICE_ROLE_KEY is configured.",
        ) from exc
    _audit_service.record("user.suspended", user.id, None, {"target_auth_user_id": auth_user_id})
    return {"status": "suspended"}


@router.post("/admin/users/{auth_user_id}/reactivate")
def reactivate_user(auth_user_id: str, user: AuthUser = Depends(require_super_admin)) -> dict[str, str]:
    admin_auth = AuthService(client=get_admin_client())
    try:
        admin_auth.admin_reactivate_user(auth_user_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to reactivate user — check SUPABASE_SERVICE_ROLE_KEY is configured.",
        ) from exc
    _audit_service.record("user.reactivated", user.id, None, {"target_auth_user_id": auth_user_id})
    return {"status": "reactivated"}


@router.post("/admin/users/{auth_user_id}/reset-password")
def reset_user_password(
    auth_user_id: str, email: str, user: AuthUser = Depends(require_super_admin)
) -> dict[str, str]:
    """Reuses the existing (anon-client-safe) request_password_reset —
    no admin privileges needed for this one."""
    auth_service = AuthService()
    auth_service.request_password_reset(email, redirect_to=_password_reset_redirect_url())
    _audit_service.record("user.password_reset_requested", user.id, None, {"target_auth_user_id": auth_user_id})
    return {"status": "reset_email_sent"}


@router.post("/admin/users/{auth_user_id}/roles")
def assign_role(
    auth_user_id: str, request: RoleAssignmentRequest, user: AuthUser = Depends(require_super_admin)
) -> dict[str, str]:
    if request.role == "admin":
        _platform_admin_service.add_admin(auth_user_id)
        _audit_service.record("user.role_assigned", user.id, None, {"target_auth_user_id": auth_user_id, "role": "admin"})
        return {"status": "admin_assigned"}

    if request.role == "workspace_admin":
        if not request.workspace_id:
            raise HTTPException(status_code=400, detail="workspace_id is required to assign the workspace_admin role")
        _workspace_admin_service.add_admin(request.workspace_id, auth_user_id)
        _audit_service.record(
            "user.role_assigned", user.id, request.workspace_id,
            {"target_auth_user_id": auth_user_id, "role": "workspace_admin"},
        )
        return {"status": "workspace_admin_assigned"}

    if not request.workspace_id:
        raise HTTPException(status_code=400, detail="workspace_id is required to assign the agent role")
    _agent_service.get_or_create(
        auth_user_id, request.email or "", request.name or "", request.workspace_id,
        department=request.department or "General",
    )
    _audit_service.record(
        "user.role_assigned", user.id, request.workspace_id,
        {"target_auth_user_id": auth_user_id, "role": "agent"},
    )
    return {"status": "agent_assigned"}


@router.get("/admin/agents", response_model=list[SupportAgentSchema])
def list_agents(workspace_id: str, user: AuthUser = Depends(require_super_admin)) -> list[SupportAgentSchema]:
    return [_to_agent_schema(a) for a in _agent_service.list_by_workspace(workspace_id)]


@router.delete("/admin/agents/{agent_id}")
def delete_agent(agent_id: str, user: AuthUser = Depends(require_super_admin)) -> dict[str, str]:
    _agent_service.delete(agent_id)
    _audit_service.record("agent.removed", user.id, None, {"agent_id": agent_id})
    return {"status": "deleted"}


@router.patch("/admin/agents/{agent_id}/department", response_model=SupportAgentSchema)
def update_agent_department(
    agent_id: str, department: str, user: AuthUser = Depends(require_super_admin)
) -> SupportAgentSchema:
    agent = _agent_service.update_department(agent_id, department)
    _audit_service.record("agent.department_changed", user.id, agent.workspace_id, {"agent_id": agent_id, "department": department})
    return _to_agent_schema(agent)


@router.get("/admin/agents/{agent_id}/performance", response_model=AgentPerformanceSchema)
def get_agent_performance(agent_id: str, user: AuthUser = Depends(require_super_admin)) -> AgentPerformanceSchema:
    from datetime import datetime, timezone

    active_chats = _escalation_repository.count_active_for_agent(agent_id)
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    resolved_today = _escalation_repository.list_resolved_today_for_agent(agent_id, today_start.isoformat())
    return AgentPerformanceSchema(
        agent_id=agent_id, active_chats=active_chats, resolved_today=len(resolved_today),
        satisfaction_score=None,
    )
