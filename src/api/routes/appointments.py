from fastapi import APIRouter, Depends, HTTPException

from ...services.appointments.appointment_service import (
    AppointmentService,
    InvalidSlotError,
    SlotAlreadyBookedError,
)
from ...services.auth.auth_service import AuthUser
from ...services.notifications.notification_service import NotificationService
from ...services.workspace.workspace_context import WorkspaceContext
from ..deps import get_current_access_token, get_current_user_optional, get_current_workspace
from ..schemas import AppointmentSchema, AppointmentSlotSchema, BookAppointmentRequest, DailyAvailabilitySchema

router = APIRouter()

_appointment_service = AppointmentService()
_notification_service = NotificationService()


@router.get("/appointments/availability", response_model=list[DailyAvailabilitySchema])
def get_availability(
    days: int = 4, workspace: WorkspaceContext = Depends(get_current_workspace)
) -> list[DailyAvailabilitySchema]:
    days = max(1, min(days, 14))
    availability = _appointment_service.get_availability(days=days, workspace_id=workspace.workspace_id)
    return [
        DailyAvailabilitySchema(
            date=day.date,
            day_label=day.day_label,
            slots=[AppointmentSlotSchema(time=s["time"], available=s["available"]) for s in day.slots],
            fully_booked=day.fully_booked,
        )
        for day in availability
    ]


@router.post("/appointments", response_model=AppointmentSchema)
def book_appointment(
    request: BookAppointmentRequest,
    user: AuthUser | None = Depends(get_current_user_optional),
    access_token: str | None = Depends(get_current_access_token),
    workspace: WorkspaceContext = Depends(get_current_workspace),
) -> AppointmentSchema:
    try:
        appointment = _appointment_service.book(
            request.date, request.time, request.name, request.email,
            user_id=user.id if user else None,
            workspace_id=workspace.workspace_id,
        )
    except SlotAlreadyBookedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidSlotError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if user is not None:
        _notification_service.notify(
            user.id, "appointment", "Appointment confirmed",
            f"{appointment.appointment_date} at {appointment.time_slot}",
            access_token=access_token, workspace_id=workspace.workspace_id,
        )

    return AppointmentSchema(
        id=appointment.id, date=appointment.appointment_date, time=appointment.time_slot,
        name=appointment.name, email=appointment.email, status=appointment.status,
    )
