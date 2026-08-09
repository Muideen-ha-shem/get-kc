"""Agent management routes (Phase 24) — `/agents/*`."""

from fastapi import APIRouter, Depends

from ...services.agents.agent_models import SupportAgent
from ...services.agents.agent_service import AgentService
from ...services.auth.auth_service import AuthUser
from ...services.workspace.workspace_context import WorkspaceContext
from ..deps import get_current_agent, get_current_user_required, get_current_workspace
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
def get_my_agent_profile(agent: SupportAgent = Depends(get_current_agent)) -> SupportAgentSchema:
    """Read-only lookup of the caller's own agent identity (see
    ``get_current_agent``'s docstring — this used to be a ``get_or_create``
    keyed on ambient workspace context, which silently minted a spurious
    duplicate agent row under the wrong workspace for anyone who wasn't a
    Ha-Shem agent. Real agent rows are always created by an admin's role
    assignment (``admin_users.py``); this route only ever reads."""
    return _to_schema(agent)


@router.patch("/agents/status", response_model=SupportAgentSchema)
def update_my_status(
    request: AgentStatusUpdate, agent: SupportAgent = Depends(get_current_agent)
) -> SupportAgentSchema:
    updated = _agent_service.update_status(agent.id, request.status)
    return _to_schema(updated)


@router.get("/agents", response_model=list[SupportAgentSchema])
def list_agents(
    user: AuthUser = Depends(get_current_user_required),
    workspace: WorkspaceContext = Depends(get_current_workspace),
) -> list[SupportAgentSchema]:
    agents = _agent_service.list_by_workspace(workspace.workspace_id)
    return [_to_schema(a) for a in agents]
