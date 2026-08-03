"""Agent management routes (Phase 24) — `/agents/*`."""

from fastapi import APIRouter, Depends, HTTPException

from ...services.agents.agent_service import AgentService
from ...services.auth.auth_service import AuthUser
from ...services.workspace.workspace_context import WorkspaceContext
from ..deps import get_current_user_required, get_current_workspace
from ..schemas import AgentStatusUpdate, SupportAgentSchema

router = APIRouter()

_agent_service = AgentService()


def _to_schema(agent) -> SupportAgentSchema:
    return SupportAgentSchema(
        id=agent.id,
        workspace_id=agent.workspace_id,
        name=agent.name,
        email=agent.email,
        department=agent.department,
        status=agent.status,
        created_at=agent.created_at,
    )


@router.get("/agents/me", response_model=SupportAgentSchema)
def get_my_agent_profile(
    user: AuthUser = Depends(get_current_user_required),
    workspace: WorkspaceContext = Depends(get_current_workspace),
) -> SupportAgentSchema:
    agent = _agent_service.get_or_create(
        user.id, user.email or "", user.full_name or user.email or "Agent", workspace.workspace_id
    )
    return _to_schema(agent)


@router.patch("/agents/status", response_model=SupportAgentSchema)
def update_my_status(
    request: AgentStatusUpdate,
    user: AuthUser = Depends(get_current_user_required),
    workspace: WorkspaceContext = Depends(get_current_workspace),
) -> SupportAgentSchema:
    agent = _agent_service.get_by_auth_user_id(user.id, workspace.workspace_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Not a registered agent for this workspace")
    updated = _agent_service.update_status(agent.id, request.status)
    return _to_schema(updated)


@router.get("/agents", response_model=list[SupportAgentSchema])
def list_agents(
    user: AuthUser = Depends(get_current_user_required),
    workspace: WorkspaceContext = Depends(get_current_workspace),
) -> list[SupportAgentSchema]:
    agents = _agent_service.list_by_workspace(workspace.workspace_id)
    return [_to_schema(a) for a in agents]
