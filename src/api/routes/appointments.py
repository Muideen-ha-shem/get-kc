from fastapi import APIRouter, Depends, HTTPException

from ...services.appointments.appointment_service import (
    AppointmentService,
    InvalidSlotError,
    SlotAlreadyBookedError,
)
from ...services.auth.auth_service import AuthUser
from ..deps import get_current_user_optional
from ..schemas import AppointmentSchema, AppointmentSlotSchema, BookAppointmentRequest, DailyAvailabilitySchema

router = APIRouter()

_appointment_service = AppointmentService()


@router.get("/appointments/availability", response_model=list[DailyAvailabilitySchema])
def get_availability(days: int = 4) -> list[DailyAvailabilitySchema]:
    days = max(1, min(days, 14))
    availability = _appointment_service.get_availability(days=days)
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
    request: BookAppointmentRequest, user: AuthUser | None = Depends(get_current_user_optional)
) -> AppointmentSchema:
    try:
        appointment = _appointment_service.book(
            request.date, request.time, request.name, request.email,
            user_id=user.id if user else None,
        )
    except SlotAlreadyBookedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidSlotError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AppointmentSchema(
        id=appointment.id, date=appointment.appointment_date, time=appointment.time_slot,
        name=appointment.name, email=appointment.email, status=appointment.status,
    )
