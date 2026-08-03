"""AI-to-human escalation routes (Phase 24 + Phase 25) — `/chat/escalate`,
`/agent/*`.

Uses `get_current_workspace` (Phase 22's lenient resolver), not
`get_current_workspace_strict` — these routes are hit via the authenticated
React frontend, same as `/chat`, never via the embeddable SDK's api-key path.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from ...services.agents.agent_service import AgentService
from ...services.auth.auth_service import AuthUser
from ...services.escalation.copilot import suggest_reply
from ...services.escalation.customer_timeline import build_customer_timeline
from ...services.escalation.escalation_repository import EscalationRepository
from ...services.escalation.escalation_service import EscalationService
from ...services.profile.profile_service import ProfileService
from ...services.workspace.workspace_context import WorkspaceContext
from ..deps import get_current_user_optional, get_current_user_required, get_current_workspace
from ..schemas import (
    AgentDashboardStatsSchema,
    CopilotSuggestReplyRequest,
    CopilotSuggestReplySchema,
    CustomerTimelineSchema,
    EscalationActionRequest,
    EscalationCreateRequest,
    EscalationMessageCreateRequest,
    EscalationMessageSchema,
    EscalationNoteCreateRequest,
    EscalationNoteSchema,
    EscalationSchema,
    RejoinAiResponseSchema,
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


def _agent_name(agent_id: str | None) -> str | None:
    """Best-effort enrichment for the AI-to-human handoff message — a
    lookup failure must never break the escalation response."""
    if agent_id is None:
        return None
    try:
        agent = _agent_service.get_by_id(agent_id)
    except Exception:
        return None
    return agent.name if agent else None


def _to_schema(escalation, messages=None, notes=None) -> EscalationSchema:
    return EscalationSchema(
        id=escalation.id,
        workspace_id=escalation.workspace_id,
        conversation_id=escalation.conversation_id,
        status=escalation.status,
        assigned_agent_id=escalation.assigned_agent_id,
        assigned_agent_name=_agent_name(escalation.assigned_agent_id),
        trigger_reason=escalation.trigger_reason,
        department=escalation.department,
        ai_engaged=escalation.ai_engaged,
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
        notes=(
            [
                EscalationNoteSchema(
                    id=n.id, author_agent_id=n.author_agent_id, content=n.content, created_at=n.created_at
                )
                for n in notes
            ]
            if notes is not None
            else None
        ),
    )


def _require_agent(user: AuthUser, workspace: WorkspaceContext):
    agent = _agent_service.get_by_auth_user_id(user.id, workspace.workspace_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Not a registered agent for this workspace")
    return agent


def _get_escalation_or_404(escalation_id: str, workspace: WorkspaceContext):
    escalation = _escalation_repository.get(escalation_id)
    if escalation is None or escalation.workspace_id != workspace.workspace_id:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return escalation


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
    escalation = _get_escalation_or_404(request.escalation_id, workspace)
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
    escalation = _get_escalation_or_404(request.escalation_id, workspace)
    if escalation.status not in ("assigned", "active", "waiting_for_customer"):
        raise HTTPException(status_code=409, detail="Escalation is not in an active/assigned state")
    updated = _escalation_repository.mark_resolved(request.escalation_id)
    return _to_schema(updated)


@router.post("/agent/escalations/{escalation_id}/wait-for-customer", response_model=EscalationSchema)
def wait_for_customer(
    escalation_id: str,
    user: AuthUser = Depends(get_current_user_required),
    workspace: WorkspaceContext = Depends(get_current_workspace),
) -> EscalationSchema:
    _require_agent(user, workspace)
    escalation = _get_escalation_or_404(escalation_id, workspace)
    if escalation.status != "active":
        raise HTTPException(status_code=409, detail="Escalation is not in progress")
    updated = _escalation_repository.set_waiting_for_customer(escalation_id)
    return _to_schema(updated)


@router.get("/agent/escalations/{escalation_id}", response_model=EscalationSchema)
def get_escalation_detail(
    escalation_id: str,
    user: AuthUser = Depends(get_current_user_required),
    workspace: WorkspaceContext = Depends(get_current_workspace),
) -> EscalationSchema:
    _require_agent(user, workspace)
    escalation = _get_escalation_or_404(escalation_id, workspace)
    messages = _escalation_repository.list_messages(escalation_id)
    notes = _escalation_repository.list_notes(escalation_id)
    return _to_schema(escalation, messages=messages, notes=notes)


@router.post("/agent/escalations/{escalation_id}/messages", response_model=EscalationMessageSchema)
def send_escalation_message(
    escalation_id: str,
    request: EscalationMessageCreateRequest,
    user: AuthUser = Depends(get_current_user_required),
    workspace: WorkspaceContext = Depends(get_current_workspace),
) -> EscalationMessageSchema:
    escalation = _get_escalation_or_404(escalation_id, workspace)

    agent = _agent_service.get_by_auth_user_id(user.id, workspace.workspace_id)
    is_assigned_agent = agent is not None and agent.id == escalation.assigned_agent_id
    sender_type = "agent" if is_assigned_agent else "customer"

    # Check-then-write: must run before add_message so "first message"
    # detection sees an empty history.
    _escalation_repository.mark_active_if_first_message(escalation_id)
    if sender_type == "customer":
        # Phase 25: a customer reply while the agent marked the escalation
        # "waiting for customer" moves it back to "in progress" — a no-op
        # (guarded by .eq("status", "waiting_for_customer")) otherwise.
        _escalation_repository.set_active(escalation_id)
    message = _escalation_repository.add_message(escalation_id, sender_type, user.id, request.content)
    return EscalationMessageSchema(
        id=message.id,
        sender_type=message.sender_type,
        sender_auth_user_id=message.sender_auth_user_id,
        content=message.content,
        created_at=message.created_at,
    )


@router.post("/agent/escalations/{escalation_id}/notes", response_model=EscalationNoteSchema)
def add_escalation_note(
    escalation_id: str,
    request: EscalationNoteCreateRequest,
    user: AuthUser = Depends(get_current_user_required),
    workspace: WorkspaceContext = Depends(get_current_workspace),
) -> EscalationNoteSchema:
    agent = _require_agent(user, workspace)
    _get_escalation_or_404(escalation_id, workspace)
    note = _escalation_repository.add_note(workspace.workspace_id, escalation_id, agent.id, request.content)
    return EscalationNoteSchema(
        id=note.id, author_agent_id=note.author_agent_id, content=note.content, created_at=note.created_at
    )


@router.post(
    "/agent/escalations/{escalation_id}/copilot/suggest-reply", response_model=CopilotSuggestReplySchema
)
def copilot_suggest_reply(
    escalation_id: str,
    request: CopilotSuggestReplyRequest,
    user: AuthUser = Depends(get_current_user_required),
    workspace: WorkspaceContext = Depends(get_current_workspace),
) -> CopilotSuggestReplySchema:
    """Drafts a suggested reply — never sent automatically. The agent
    reviews/edits it and sends it explicitly via POST .../messages."""
    _require_agent(user, workspace)
    _get_escalation_or_404(escalation_id, workspace)
    result = suggest_reply(workspace_id=workspace.workspace_id, question=request.question)
    return CopilotSuggestReplySchema(draft=result["draft"], citations=result["citations"])


@router.post("/agent/escalations/{escalation_id}/rejoin-ai", response_model=RejoinAiResponseSchema)
def rejoin_ai(
    escalation_id: str,
    user: AuthUser = Depends(get_current_user_required),
    workspace: WorkspaceContext = Depends(get_current_workspace),
) -> RejoinAiResponseSchema:
    """Hands the conversation back to the AI: marks the escalation resolved
    and flips ai_engaged back on. /chat itself never reads escalation state
    — the frontend passes the returned handoff_recap as ChatRequest.
    handoff_context on the next turn so the AI resumes without the customer
    repeating themselves."""
    _require_agent(user, workspace)
    escalation = _get_escalation_or_404(escalation_id, workspace)
    messages = _escalation_repository.list_messages(escalation_id)
    notes = _escalation_repository.list_notes(escalation_id)

    recap_parts = []
    if escalation.summary:
        recap_parts.append(f"Prior AI summary: {escalation.summary.get('problem', '')}")
    if messages:
        recent = " | ".join(f"{m.sender_type}: {m.content}" for m in messages[-5:])
        recap_parts.append(f"Recent conversation with support: {recent}")
    if notes:
        recap_parts.append(f"Agent notes: {' | '.join(n.content for n in notes)}")
    handoff_recap = " ".join(recap_parts) or "Customer was previously connected with a support agent."

    resolved = _escalation_repository.mark_resolved(escalation_id)
    resolved = _escalation_repository.set_ai_engaged(escalation_id, True)
    return RejoinAiResponseSchema(escalation=_to_schema(resolved), handoff_recap=handoff_recap)


@router.get("/agent/customers/{auth_user_id}/timeline", response_model=CustomerTimelineSchema)
def get_customer_timeline(
    auth_user_id: str,
    user: AuthUser = Depends(get_current_user_required),
    workspace: WorkspaceContext = Depends(get_current_workspace),
) -> CustomerTimelineSchema:
    _require_agent(user, workspace)
    timeline = build_customer_timeline(auth_user_id)

    profile = timeline["profile"]
    return CustomerTimelineSchema(
        profile=(
            {
                "id": profile.id, "email": profile.email, "full_name": profile.full_name,
                "company_name": profile.company_name, "industry": profile.industry,
            }
            if profile
            else None
        ),
        conversations=[
            {"id": c.id, "title": c.title, "created_at": c.created_at, "updated_at": c.updated_at}
            for c in timeline["conversations"]
        ],
        saved_recommendations=[
            {
                "id": r.id, "products": r.products, "question": r.question,
                "recommendation": r.recommendation, "created_at": r.created_at,
            }
            for r in timeline["saved_recommendations"]
        ],
        saved_comparisons=[
            {"id": c.id, "product_ids": c.product_ids, "created_at": c.created_at}
            for c in timeline["saved_comparisons"]
        ],
        appointments=[
            {
                "id": a.id, "date": a.appointment_date, "time": a.time_slot,
                "name": a.name, "email": a.email, "status": a.status,
            }
            for a in timeline["appointments"]
        ],
        past_escalations=[_to_schema(e) for e in timeline["past_escalations"]],
        demo_requests=timeline["demo_requests"],
        demo_requests_note=timeline["demo_requests_note"],
    )


@router.get("/agent/dashboard/stats", response_model=AgentDashboardStatsSchema)
def get_agent_dashboard_stats(
    user: AuthUser = Depends(get_current_user_required),
    workspace: WorkspaceContext = Depends(get_current_workspace),
) -> AgentDashboardStatsSchema:
    agent = _require_agent(user, workspace)
    workload = _escalation_repository.count_active_for_agent(agent.id)

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    resolved_today = _escalation_repository.list_resolved_today_for_agent(agent.id, today_start.isoformat())

    average_minutes: float | None = None
    if resolved_today:
        durations = []
        for escalation in resolved_today:
            if escalation.created_at and escalation.resolved_at:
                created = datetime.fromisoformat(escalation.created_at.replace("Z", "+00:00"))
                resolved = datetime.fromisoformat(escalation.resolved_at.replace("Z", "+00:00"))
                durations.append((resolved - created).total_seconds() / 60)
        if durations:
            average_minutes = sum(durations) / len(durations)

    return AgentDashboardStatsSchema(
        status=agent.status,
        department=agent.department,
        current_workload=workload,
        resolved_today=len(resolved_today),
        average_resolution_minutes=average_minutes,
    )
