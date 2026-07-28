"""Integration tests for /saved-comparisons, /saved-recommendations, and
/appointments — following the same dependency_overrides + patched-service
pattern as test_phase20_routes.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.deps import get_current_access_token_required, get_current_user_optional, get_current_user_required
from src.services.auth.auth_service import AuthUser

_FAKE_USER = AuthUser(id="u1", email="a@b.com", full_name="Ada")


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _authenticate():
    app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
    app.dependency_overrides[get_current_access_token_required] = lambda: "token-1"


class TestSavedComparisonsRoutes:
    def test_requires_auth(self, client):
        response = client.post("/saved-comparisons", json={"product_ids": ["SPIDIFY", "ZivaAIRA"]})
        assert response.status_code == 401

    def test_save_returns_saved_row(self, client):
        _authenticate()
        row = MagicMock(id="cmp1", product_ids=["SPIDIFY", "ZivaAIRA"], created_at=None)
        with patch("src.api.routes.saved_items._comparison_service.save", return_value=row):
            response = client.post("/saved-comparisons", json={"product_ids": ["SPIDIFY", "ZivaAIRA"]})

        assert response.status_code == 200
        assert response.json()["product_ids"] == ["SPIDIFY", "ZivaAIRA"]

    def test_single_product_rejected_by_validation(self, client):
        _authenticate()
        response = client.post("/saved-comparisons", json={"product_ids": ["SPIDIFY"]})
        assert response.status_code == 422

    def test_list_returns_rows(self, client):
        _authenticate()
        row = MagicMock(id="cmp1", product_ids=["SPIDIFY", "ZivaAIRA"], created_at=None)
        with patch("src.api.routes.saved_items._comparison_service.list_for_user", return_value=[row]):
            response = client.get("/saved-comparisons")

        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_delete_missing_returns_404(self, client):
        _authenticate()
        with patch("src.api.routes.saved_items._comparison_service.delete", return_value=False):
            response = client.delete("/saved-comparisons/missing")

        assert response.status_code == 404


class TestSavedRecommendationsRoutes:
    def test_requires_auth(self, client):
        response = client.post(
            "/saved-recommendations",
            json={"products": ["SPIDIFY"], "question": "q", "recommendation": "r"},
        )
        assert response.status_code == 401

    def test_save_returns_saved_row(self, client):
        _authenticate()
        row = MagicMock(id="rec1", products=["SPIDIFY"], question="q", recommendation="r", created_at=None)
        with patch("src.api.routes.saved_items._recommendation_service.save", return_value=row):
            response = client.post(
                "/saved-recommendations",
                json={"products": ["SPIDIFY"], "question": "q", "recommendation": "r"},
            )

        assert response.status_code == 200
        assert response.json()["products"] == ["SPIDIFY"]

    def test_delete_missing_returns_404(self, client):
        _authenticate()
        with patch("src.api.routes.saved_items._recommendation_service.delete", return_value=False):
            response = client.delete("/saved-recommendations/missing")

        assert response.status_code == 404


class TestAppointmentRoutes:
    def test_availability_is_public_no_auth_required(self, client):
        with patch("src.api.routes.appointments._appointment_service.get_availability", return_value=[]):
            response = client.get("/appointments/availability")

        assert response.status_code == 200

    def test_book_appointment_anonymous_succeeds(self, client):
        appointment = MagicMock(
            id="a1", appointment_date="2026-08-01", time_slot="09:00",
            email="ada@example.com", status="confirmed",
        )
        appointment.name = "Ada"
        with patch("src.api.routes.appointments._appointment_service.book", return_value=appointment):
            response = client.post(
                "/appointments",
                json={"date": "2026-08-01", "time": "09:00", "name": "Ada", "email": "ada@example.com"},
            )

        assert response.status_code == 200
        assert response.json()["status"] == "confirmed"

    def test_book_appointment_invalid_email_rejected(self, client):
        response = client.post(
            "/appointments",
            json={"date": "2026-08-01", "time": "09:00", "name": "Ada", "email": "not-an-email"},
        )
        assert response.status_code == 422

    def test_book_already_taken_slot_returns_409(self, client):
        from src.services.appointments.appointment_service import SlotAlreadyBookedError

        with patch(
            "src.api.routes.appointments._appointment_service.book",
            side_effect=SlotAlreadyBookedError("taken"),
        ):
            response = client.post(
                "/appointments",
                json={"date": "2026-08-01", "time": "09:00", "name": "Ada", "email": "ada@example.com"},
            )

        assert response.status_code == 409

    def test_book_invalid_slot_returns_400(self, client):
        from src.services.appointments.appointment_service import InvalidSlotError

        with patch(
            "src.api.routes.appointments._appointment_service.book",
            side_effect=InvalidSlotError("bad slot"),
        ):
            response = client.post(
                "/appointments",
                json={"date": "2026-08-01", "time": "23:59", "name": "Ada", "email": "ada@example.com"},
            )

        assert response.status_code == 400

    def test_book_appointment_records_user_id_when_authenticated(self, client):
        app.dependency_overrides[get_current_user_optional] = lambda: _FAKE_USER
        appointment = MagicMock(
            id="a1", appointment_date="2026-08-01", time_slot="09:00",
            email="ada@example.com", status="confirmed",
        )
        appointment.name = "Ada"
        with patch("src.api.routes.appointments._appointment_service.book", return_value=appointment) as mock_book:
            client.post(
                "/appointments",
                json={"date": "2026-08-01", "time": "09:00", "name": "Ada", "email": "ada@example.com"},
            )

        assert mock_book.call_args.kwargs["user_id"] == "u1"
