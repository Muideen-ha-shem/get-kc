"""AI-to-human escalation routes (Phase 24) — `/chat/escalate`, `/agent/*`.

Uses `get_current_workspace` (Phase 22's lenient resolver), not
`get_current_workspace_strict` — these routes are hit via the authenticated
React frontend, same as `/chat`, never via the embeddable SDK's api-key path.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ...services.agents.agent_service import AgentService
from ...services.auth.auth_service import AuthUser
from ...services.escalation.escalation_repository import EscalationRepository
from ...services.escalation.escalation_service import EscalationService
from ...services.profile.profile_service import ProfileService
from ...services.workspace.workspace_context import WorkspaceContext
from ..deps import get_current_user_optional, get_current_user_required, get_current_workspace
from ..schemas import (
    EscalationActionRequest,
    EscalationCreateRequest,
    EscalationMessageCreateRequest,
    EscalationMessageSchema,
    EscalationSchema,
)

router = APIRouter()

_agent_service = AgentService()
_escalation_repository = EscalationRepository()
_escalation_service = EscalationService(agent_service=_agent_service, repository=_escalation_repository)
_profile_service = ProfileService()


def _customer_company(user: AuthUser | None) -> str | None:
    if user is None:
        return None
    try:
        profile = _profile_service.get_by_auth_user_id(user.id)
    except Exception:
        return None
    return profile.company_name if profile else None


def _to_schema(escalation, messages=None) -> EscalationSchema:
    return EscalationSchema(
        id=escalation.id,
        workspace_id=escalation.workspace_id,
        conversation_id=escalation.conversation_id,
        status=escalation.status,
        assigned_agent_id=escalation.assigned_agent_id,
        trigger_reason=escalation.trigger_reason,
        department=escalation.department,
        summary=escalation.summary,
        created_at=escalation.created_at,
        assigned_at=escalation.assigned_at,
        resolved_at=escalation.resolved_at,
        closed_at=escalation.closed_at,
        messages=(
            [
                EscalationMessageSchema(
                    id=m.id,
                    sender_type=m.sender_type,
                    sender_auth_user_id=m.sender_auth_user_id,
                    content=m.content,
                    created_at=m.created_at,
                )
                for m in messages
            ]
            if messages is not None
            else None
        ),
    )


def _require_agent(user: AuthUser, workspace: WorkspaceContext):
    agent = _agent_service.get_by_auth_user_id(user.id, workspace.workspace_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Not a registered agent for this workspace")
    return agent


@router.post("/chat/escalate", response_model=EscalationSchema)
def escalate_conversation(
    request: EscalationCreateRequest,
    user: AuthUser | None = Depends(get_current_user_optional),
    workspace: WorkspaceContext = Depends(get_current_workspace),
) -> EscalationSchema:
    escalation = _escalation_service.create_direct(
        workspace_id=workspace.workspace_id,
        workspace_name=workspace.name,
        conversation_id=request.conversation_id,
        question=request.question,
        customer_company=_customer_company(user),
    )
    return _to_schema(escalation)


@router.get("/agent/queue", response_model=list[EscalationSchema])
def get_agent_queue(
    user: AuthUser = Depends(get_current_user_required),
    workspace: WorkspaceContext = Depends(get_current_workspace),
) -> list[EscalationSchema]:
    _require_agent(user, workspace)
    escalations = _escalation_repository.list_waiting(workspace.workspace_id)
    return [_to_schema(e) for e in escalations]


@router.get("/agent/conversations", response_model=list[EscalationSchema])
def get_my_agent_conversations(
    user: AuthUser = Depends(get_current_user_required),
    workspace: WorkspaceContext = Depends(get_current_workspace),
) -> list[EscalationSchema]:
    agent = _require_agent(user, workspace)
    escalations = _escalation_repository.list_assigned_to(agent.id)
    return [_to_schema(e) for e in escalations]


@router.post("/agent/accept", response_model=EscalationSchema)
def accept_escalation(
    request: EscalationActionRequest,
    user: AuthUser = Depends(get_current_user_required),
    workspace: WorkspaceContext = Depends(get_current_workspace),
) -> EscalationSchema:
    agent = _require_agent(user, workspace)
    escalation = _escalation_repository.get(request.escalation_id)
    if escalation is None or escalation.workspace_id != workspace.workspace_id:
        raise HTTPException(status_code=404, detail="Escalation not found")
    if escalation.status != "waiting":
        raise HTTPException(status_code=409, detail="Escalation is not waiting for assignment")
    updated = _escalation_repository.assign(request.escalation_id, agent.id)
    return _to_schema(updated)


@router.post("/agent/resolve", response_model=EscalationSchema)
def resolve_escalation(
    request: EscalationActionRequest,
    user: AuthUser = Depends(get_current_user_required),
    workspace: WorkspaceContext = Depends(get_current_workspace),
) -> EscalationSchema:
    _require_agent(user, workspace)
    escalation = _escalation_repository.get(request.escalation_id)
    if escalation is None or escalation.workspace_id != workspace.workspace_id:
        raise HTTPException(status_code=404, detail="Escalation not found")
    if escalation.status not in ("assigned", "active"):
        raise HTTPException(status_code=409, detail="Escalation is not in an active/assigned state")
    updated = _escalation_repository.mark_resolved(request.escalation_id)
    return _to_schema(updated)


@router.get("/agent/escalations/{escalation_id}", response_model=EscalationSchema)
def get_escalation_detail(
    escalation_id: str,
    user: AuthUser = Depends(get_current_user_required),
    workspace: WorkspaceContext = Depends(get_current_workspace),
) -> EscalationSchema:
    _require_agent(user, workspace)
    escalation = _escalation_repository.get(escalation_id)
    if escalation is None or escalation.workspace_id != workspace.workspace_id:
        raise HTTPException(status_code=404, detail="Escalation not found")
    messages = _escalation_repository.list_messages(escalation_id)
    return _to_schema(escalation, messages=messages)


@router.post("/agent/escalations/{escalation_id}/messages", response_model=EscalationMessageSchema)
def send_escalation_message(
    escalation_id: str,
    request: EscalationMessageCreateRequest,
    user: AuthUser = Depends(get_current_user_required),
    workspace: WorkspaceContext = Depends(get_current_workspace),
) -> EscalationMessageSchema:
    escalation = _escalation_repository.get(escalation_id)
    if escalation is None or escalation.workspace_id != workspace.workspace_id:
        raise HTTPException(status_code=404, detail="Escalation not found")

    agent = _agent_service.get_by_auth_user_id(user.id, workspace.workspace_id)
    is_assigned_agent = agent is not None and agent.id == escalation.assigned_agent_id
    sender_type = "agent" if is_assigned_agent else "customer"

    # Check-then-write: must run before add_message so "first message"
    # detection sees an empty history.
    _escalation_repository.mark_active_if_first_message(escalation_id)
    message = _escalation_repository.add_message(escalation_id, sender_type, user.id, request.content)
    return EscalationMessageSchema(
        id=message.id,
        sender_type=message.sender_type,
        sender_auth_user_id=message.sender_auth_user_id,
        content=message.content,
        created_at=message.created_at,
    )
