"""Tests for AppointmentService — Supabase calls mocked."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest
from postgrest.exceptions import APIError

from src.services.appointments.appointment_service import (
    AppointmentService,
    InvalidSlotError,
    SlotAlreadyBookedError,
    SLOT_TEMPLATE,
)


class TestGetAvailability:
    def test_returns_one_entry_per_day_with_full_slot_template(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value.data = []
        service = AppointmentService(client=client)

        availability = service.get_availability(days=4)

        assert len(availability) == 4
        assert all(len(day.slots) == len(SLOT_TEMPLATE) for day in availability)
        assert all(day.fully_booked is False for day in availability)

    def test_booked_slot_marked_unavailable(self):
        today = date.today().isoformat()
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value.data = [
            {"appointment_date": today, "time_slot": SLOT_TEMPLATE[0]}
        ]
        service = AppointmentService(client=client)

        availability = service.get_availability(days=1)

        slots_by_time = {s["time"]: s["available"] for s in availability[0].slots}
        assert slots_by_time[SLOT_TEMPLATE[0]] is False
        assert slots_by_time[SLOT_TEMPLATE[1]] is True

    def test_fully_booked_day_flagged(self):
        today = date.today().isoformat()
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value.data = [
            {"appointment_date": today, "time_slot": slot} for slot in SLOT_TEMPLATE
        ]
        service = AppointmentService(client=client)

        availability = service.get_availability(days=1)

        assert availability[0].fully_booked is True
        assert all(not s["available"] for s in availability[0].slots)

    def test_window_advances_with_today_automatic_reset(self):
        """No explicit 'reset' step exists — availability is recomputed
        from date.today() on every call, so a date that falls out of the
        forward-looking window on a later call simply isn't offered
        anymore, which is the whole 'reset' behaviour."""
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value.data = []
        service = AppointmentService(client=client)

        availability = service.get_availability(days=3)
        expected_dates = [(date.today() + timedelta(days=i)).isoformat() for i in range(3)]

        assert [day.date for day in availability] == expected_dates


class TestBookAppointment:
    def test_successful_booking(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        client.table.return_value.insert.return_value.execute.return_value.data = [{
            "id": "a1", "appointment_date": "2026-08-01", "time_slot": "09:00",
            "name": "Ada", "email": "ada@example.com", "status": "confirmed", "created_at": None,
        }]
        service = AppointmentService(client=client)

        appointment = service.book("2026-08-01", "09:00", "Ada", "ada@example.com")

        assert appointment.id == "a1"
        assert appointment.status == "confirmed"

    def test_invalid_slot_rejected_before_any_query(self):
        client = MagicMock()
        service = AppointmentService(client=client)

        with pytest.raises(InvalidSlotError):
            service.book("2026-08-01", "23:59", "Ada", "ada@example.com")

        client.table.return_value.insert.assert_not_called()

    def test_already_booked_slot_rejected_by_precheck(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "existing"}
        ]
        service = AppointmentService(client=client)

        with pytest.raises(SlotAlreadyBookedError):
            service.book("2026-08-01", "09:00", "Ada", "ada@example.com")

        client.table.return_value.insert.assert_not_called()

    def test_concurrent_double_booking_caught_by_unique_constraint(self):
        """Simulates the precheck passing (race window) but the DB's unique
        constraint rejecting the insert — this is the actual correctness
        guarantee, not the precheck."""
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        client.table.return_value.insert.return_value.execute.side_effect = APIError(
            {"message": "duplicate key value violates unique constraint", "code": "23505"}
        )
        service = AppointmentService(client=client)

        with pytest.raises(SlotAlreadyBookedError):
            service.book("2026-08-01", "09:00", "Ada", "ada@example.com")

    def test_unrelated_api_error_propagates(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        client.table.return_value.insert.return_value.execute.side_effect = APIError(
            {"message": "connection error", "code": "08000"}
        )
        service = AppointmentService(client=client)

        with pytest.raises(APIError):
            service.book("2026-08-01", "09:00", "Ada", "ada@example.com")
