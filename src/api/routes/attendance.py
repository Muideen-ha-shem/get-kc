"""Agent self-service attendance routes — clock in/out, AUX (Agent Operations).

`get_current_agent`-gated throughout (mirrors `agents.py`) so an agent only
ever acts on their own identity — never accepts a workspace_id or agent_id
from the client.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ...services.agents.agent_models import SupportAgent
from ...services.agents.attendance_models import AuxEvent, WorkSession
from ...services.agents.attendance_repository import AttendanceRepository
from ...services.agents.attendance_service import (
    AlreadyClockedInError,
    AttendanceService,
    NoActiveAuxError,
    NotClockedInError,
)
from ..deps import get_current_agent
from ..schemas import AttendanceMeSchema, AuxEventSchema, AuxStartRequest, WorkSessionSchema

router = APIRouter()

_attendance_repository = AttendanceRepository()
_attendance_service = AttendanceService(repository=_attendance_repository)


def _session_schema(session: WorkSession | None) -> WorkSessionSchema | None:
    if session is None:
        return None
    return WorkSessionSchema(
        id=session.id, agent_id=session.agent_id, work_date=session.work_date,
        clock_in_at=session.clock_in_at, clock_out_at=session.clock_out_at,
        total_work_seconds=session.total_work_seconds,
    )


def _aux_schema(aux: AuxEvent | None) -> AuxEventSchema | None:
    if aux is None:
        return None
    return AuxEventSchema(
        id=aux.id, agent_id=aux.agent_id, aux_type=aux.aux_type,
        started_at=aux.started_at, ended_at=aux.ended_at,
        duration_seconds=aux.duration_seconds, reason=aux.reason,
    )


@router.post("/agents/clock-in", response_model=WorkSessionSchema)
def clock_in(agent: SupportAgent = Depends(get_current_agent)) -> WorkSessionSchema:
    try:
        session = _attendance_service.clock_in(agent.workspace_id, agent.id)
    except AlreadyClockedInError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _session_schema(session)


@router.post("/agents/clock-out", response_model=WorkSessionSchema)
def clock_out(agent: SupportAgent = Depends(get_current_agent)) -> WorkSessionSchema:
    try:
        session = _attendance_service.clock_out(agent.id)
    except NotClockedInError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _session_schema(session)


@router.post("/agents/aux/start", response_model=AuxEventSchema)
def start_aux(
    request: AuxStartRequest, agent: SupportAgent = Depends(get_current_agent)
) -> AuxEventSchema:
    try:
        event = _attendance_service.start_aux(
            agent.workspace_id, agent.id, request.aux_type, request.reason
        )
    except NotClockedInError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _aux_schema(event)


@router.post("/agents/aux/end", response_model=AuxEventSchema)
def end_aux(agent: SupportAgent = Depends(get_current_agent)) -> AuxEventSchema:
    try:
        event = _attendance_service.end_aux(agent.id)
    except NoActiveAuxError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _aux_schema(event)


@router.get("/agents/attendance/me", response_model=AttendanceMeSchema)
def get_my_attendance(agent: SupportAgent = Depends(get_current_agent)) -> AttendanceMeSchema:
    session = _attendance_service.get_current_session(agent.id)
    aux = _attendance_service.get_current_aux(agent.id)
    history = _attendance_repository.list_aux_events_for_session(session.id) if session else []
    return AttendanceMeSchema(
        session=_session_schema(session),
        aux=_aux_schema(aux),
        today_aux_history=[_aux_schema(e) for e in history],
    )
