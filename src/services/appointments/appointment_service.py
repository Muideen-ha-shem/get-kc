"""AppointmentService — Support Center "Book a strategy session" booking.

Design notes
------------
Availability is *computed*, never stored: each call derives the candidate
dates from "today" forward and subtracts whatever's already booked in the
``appointments`` table for those dates. This is what gives "automatic
reset" for free — no cron job, no explicit reset step. Once a date is no
longer in the forward-looking window (i.e. the next calendar day begins),
it simply stops being offered, and that date's slots are irrelevant to any
future availability check.

The ``appointments`` table's ``unique (appointment_date, time_slot)``
constraint (see ``scripts/sql/005_saved_items.sql``) is the actual
correctness guarantee against a double-booking race between two concurrent
requests — this service's own read-then-insert check is a fast path for the
common case, not the source of truth.

Public feature (same precedent as ``demo_requests`` — no RLS, no auth
required to book), so no ``access_token`` plumbing here, unlike the
saved-items services. ``user_id`` is recorded when the booker happens to be
signed in, but is never required.

Swappable for a real scheduling/calendar provider later: everything a
provider would supply — slot template, availability window, booking
persistence — is isolated behind this one class's public methods.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from postgrest.exceptions import APIError
from supabase import Client

from ...sb import get_client
from ...services.workspace.workspace_models import DEFAULT_WORKSPACE_ID
from ...shared.logging import get_logger

logger: logging.Logger = get_logger(__name__)

_TABLE = "appointments"

# The fixed daily slot template — swap for a real calendar provider's
# availability feed later without touching any caller of this service.
SLOT_TEMPLATE: tuple[str, ...] = ("09:00", "10:30", "13:00", "15:30")

_UNIQUE_VIOLATION = "23505"


class SlotAlreadyBookedError(Exception):
    """Raised when the requested (date, time_slot) is already taken."""


class InvalidSlotError(Exception):
    """Raised for a date/time outside the offered availability window."""


@dataclass(frozen=True)
class DailyAvailability:
    date: str
    day_label: str
    slots: list[dict[str, Any]]
    fully_booked: bool


@dataclass(frozen=True)
class Appointment:
    id: str
    appointment_date: str
    time_slot: str
    name: str
    email: str
    status: str
    created_at: str | None = None


class AppointmentService:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def list_for_user(self, user_id: str) -> list[Appointment]:
        """Phase 25: used by the Customer Timeline aggregation. Public
        feature, no RLS on this table (see class docstring) — scoped by
        the app-layer `user_id` filter, same as every other query here."""
        response = (
            self._client.table(_TABLE)
            .select("*")
            .eq("user_id", user_id)
            .order("appointment_date", desc=True)
            .execute()
        )
        return [
            Appointment(
                id=row["id"], appointment_date=row["appointment_date"], time_slot=row["time_slot"],
                name=row["name"], email=row["email"], status=row["status"], created_at=row.get("created_at"),
            )
            for row in response.data
        ]

    def get_availability(self, days: int = 4, workspace_id: str | None = None) -> list[DailyAvailability]:
        candidate_dates = [date.today() + timedelta(days=offset) for offset in range(days)]
        start, end = candidate_dates[0].isoformat(), candidate_dates[-1].isoformat()

        query = (
            self._client.table(_TABLE)
            .select("appointment_date,time_slot")
            .eq("status", "confirmed")
            .gte("appointment_date", start)
            .lte("appointment_date", end)
        )
        if workspace_id is not None:
            query = query.eq("workspace_id", workspace_id)
        response = query.execute()
        booked_by_date: dict[str, set[str]] = {}
        for row in response.data:
            booked_by_date.setdefault(row["appointment_date"], set()).add(row["time_slot"])

        availability = []
        for day in candidate_dates:
            booked = booked_by_date.get(day.isoformat(), set())
            slots = [{"time": slot, "available": slot not in booked} for slot in SLOT_TEMPLATE]
            availability.append(
                DailyAvailability(
                    date=day.isoformat(),
                    day_label=day.strftime("%a"),
                    slots=slots,
                    fully_booked=all(not s["available"] for s in slots),
                )
            )
        return availability

    def book(
        self,
        appointment_date: str,
        time_slot: str,
        name: str,
        email: str,
        user_id: str | None = None,
        workspace_id: str = DEFAULT_WORKSPACE_ID,
    ) -> Appointment:
        if time_slot not in SLOT_TEMPLATE:
            raise InvalidSlotError(f"{time_slot!r} is not an offered time slot")

        # Note: the DB's unique(appointment_date, time_slot) constraint
        # (005_saved_items.sql) is not workspace-scoped — a Phase 22
        # migration only adds an ALTER-COLUMN, never an ALTER-CONSTRAINT, to
        # stay additive-only. Two different tenants booking the same date
        # and slot would still race on that constraint. Flagged as a Phase
        # 23 follow-up (widen the unique constraint to
        # (workspace_id, appointment_date, time_slot)), not a silent gap.
        existing = (
            self._client.table(_TABLE)
            .select("id")
            .eq("appointment_date", appointment_date)
            .eq("time_slot", time_slot)
            .eq("status", "confirmed")
            .eq("workspace_id", workspace_id)
            .limit(1)
            .execute()
        )
        if existing.data:
            raise SlotAlreadyBookedError(f"{appointment_date} {time_slot} is already booked")

        payload = {
            "appointment_date": appointment_date,
            "time_slot": time_slot,
            "name": name,
            "email": email,
            "user_id": user_id,
            "workspace_id": workspace_id,
        }
        try:
            response = self._client.table(_TABLE).insert(payload).execute()
        except APIError as exc:
            if exc.code == _UNIQUE_VIOLATION:
                raise SlotAlreadyBookedError(f"{appointment_date} {time_slot} is already booked") from exc
            raise
        row = response.data[0]
        return Appointment(
            id=row["id"], appointment_date=row["appointment_date"], time_slot=row["time_slot"],
            name=row["name"], email=row["email"], status=row["status"], created_at=row.get("created_at"),
        )
