"""Integration tests for /chat/feedback, /notifications, and the
notification triggers wired into /appointments, /saved-recommendations,
and /demo-request."""

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


class TestFeedbackRoute:
    def test_anonymous_feedback_accepted(self, client):
        row = MagicMock(id="f1", question="q", answer="a", rating="helpful", comment=None, created_at=None)
        with patch("src.api.routes.feedback._feedback_service.submit", return_value=row) as mock_submit:
            response = client.post("/chat/feedback", json={"question": "q", "answer": "a", "rating": "helpful"})

        assert response.status_code == 200
        assert mock_submit.call_args.kwargs["user_id"] is None

    def test_invalid_rating_rejected(self, client):
        response = client.post("/chat/feedback", json={"question": "q", "answer": "a", "rating": "meh"})
        assert response.status_code == 422

    def test_authenticated_feedback_records_user_id(self, client):
        app.dependency_overrides[get_current_user_optional] = lambda: _FAKE_USER
        row = MagicMock(id="f1", question="q", answer="a", rating="not_helpful", comment="too vague", created_at=None)
        with patch("src.api.routes.feedback._feedback_service.submit", return_value=row) as mock_submit:
            response = client.post(
                "/chat/feedback",
                json={"question": "q", "answer": "a", "rating": "not_helpful", "comment": "too vague"},
            )

        assert response.status_code == 200
        assert mock_submit.call_args.kwargs["user_id"] == "u1"


class TestNotificationRoutes:
    def test_list_requires_auth(self, client):
        response = client.get("/notifications")
        assert response.status_code == 401

    def test_list_returns_rows(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        app.dependency_overrides[get_current_access_token_required] = lambda: "token-1"
        row = MagicMock(id="n1", type="appointment", title="Appointment confirmed", body="...", is_read=False, created_at=None)
        with patch("src.api.routes.notifications._notification_service.list_for_user", return_value=[row]):
            response = client.get("/notifications")

        assert response.status_code == 200
        assert response.json()[0]["id"] == "n1"

    def test_unread_count(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        app.dependency_overrides[get_current_access_token_required] = lambda: "token-1"
        with patch("src.api.routes.notifications._notification_service.unread_count", return_value=2):
            response = client.get("/notifications/unread-count")

        assert response.json()["count"] == 2

    def test_mark_read_missing_returns_404(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        app.dependency_overrides[get_current_access_token_required] = lambda: "token-1"
        with patch("src.api.routes.notifications._notification_service.mark_read", return_value=False):
            response = client.post("/notifications/missing/read")

        assert response.status_code == 404

    def test_mark_all_read(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        app.dependency_overrides[get_current_access_token_required] = lambda: "token-1"
        with patch("src.api.routes.notifications._notification_service.mark_all_read") as mock_mark:
            response = client.post("/notifications/read-all")

        assert response.status_code == 200
        mock_mark.assert_called_once()


class TestNotificationTriggers:
    def test_appointment_booking_notifies_authenticated_user(self, client):
        app.dependency_overrides[get_current_user_optional] = lambda: _FAKE_USER
        appointment = MagicMock(id="a1", appointment_date="2026-08-01", time_slot="09:00", email="ada@example.com", status="confirmed")
        appointment.name = "Ada"
        with patch("src.api.routes.appointments._appointment_service.book", return_value=appointment), \
             patch("src.api.routes.appointments._notification_service.notify") as mock_notify:
            client.post("/appointments", json={"date": "2026-08-01", "time": "09:00", "name": "Ada", "email": "ada@example.com"})

        mock_notify.assert_called_once()
        assert mock_notify.call_args[0][0] == "u1"
        assert mock_notify.call_args[0][1] == "appointment"

    def test_anonymous_appointment_booking_does_not_notify(self, client):
        appointment = MagicMock(id="a1", appointment_date="2026-08-01", time_slot="09:00", email="ada@example.com", status="confirmed")
        appointment.name = "Ada"
        with patch("src.api.routes.appointments._appointment_service.book", return_value=appointment), \
             patch("src.api.routes.appointments._notification_service.notify") as mock_notify:
            client.post("/appointments", json={"date": "2026-08-01", "time": "09:00", "name": "Ada", "email": "ada@example.com"})

        mock_notify.assert_not_called()

    def test_saved_recommendation_notifies_owner(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        app.dependency_overrides[get_current_access_token_required] = lambda: "token-1"
        row = MagicMock(id="rec1", products=["SPIDIFY"], question="q", recommendation="r", created_at=None)
        with patch("src.api.routes.saved_items._recommendation_service.save", return_value=row), \
             patch("src.api.routes.saved_items._notification_service.notify") as mock_notify:
            client.post(
                "/saved-recommendations",
                json={"products": ["SPIDIFY"], "question": "q", "recommendation": "r"},
            )

        mock_notify.assert_called_once()
        assert mock_notify.call_args[0][1] == "saved_recommendation"

    def test_demo_request_notifies_authenticated_requester(self, client):
        app.dependency_overrides[get_current_user_optional] = lambda: _FAKE_USER
        with patch(
            "src.api.routes.demo_request.submit_demo_request",
            return_value={"id": 1, "name": "Ada", "email": "a@b.com", "company": None, "use_case": None, "product": None},
        ), patch("src.api.routes.demo_request._notification_service.notify") as mock_notify:
            client.post("/demo-request", json={"name": "Ada", "email": "a@b.com"})

        mock_notify.assert_called_once()
        assert mock_notify.call_args[0][1] == "demo_request"

    def test_anonymous_demo_request_does_not_notify(self, client):
        with patch(
            "src.api.routes.demo_request.submit_demo_request",
            return_value={"id": 1, "name": "Ada", "email": "a@b.com", "company": None, "use_case": None, "product": None},
        ), patch("src.api.routes.demo_request._notification_service.notify") as mock_notify:
            client.post("/demo-request", json={"name": "Ada", "email": "a@b.com"})

        mock_notify.assert_not_called()


class TestConversationSearch:
    def test_search_param_forwarded_to_service(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        app.dependency_overrides[get_current_access_token_required] = lambda: "token-1"
        with patch("src.api.routes.conversations._conversation_service.list_conversations", return_value=[]) as mock_list:
            client.get("/conversations?search=SPIDIFY")

        assert mock_list.call_args.kwargs["search"] == "SPIDIFY"

    def test_no_search_param_defaults_to_none(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        app.dependency_overrides[get_current_access_token_required] = lambda: "token-1"
        with patch("src.api.routes.conversations._conversation_service.list_conversations", return_value=[]) as mock_list:
            client.get("/conversations")

        assert mock_list.call_args.kwargs["search"] is None
