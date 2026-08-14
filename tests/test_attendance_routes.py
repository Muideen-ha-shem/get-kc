"""Integration tests for /agents/clock-in, /agents/clock-out, /agents/aux/*,
/agents/attendance/me — mirrors test_agent_escalation_routes.py's
dependency-override + patched-singleton pattern."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.deps import get_current_agent
from src.services.agents.agent_models import SupportAgent
from src.services.agents.attendance_service import (
    AlreadyClockedInError,
    NoActiveAuxError,
    NotClockedInError,
)

_FAKE_AGENT = SupportAgent(
    id="a1", workspace_id="w1", auth_user_id="u1", name="Ada", email="ada@example.com",
    department="Support", status="available",
)


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _authenticate():
    app.dependency_overrides[get_current_agent] = lambda: _FAKE_AGENT


class TestClockInOut:
    def test_clock_in_requires_agent(self, client):
        response = client.post("/agents/clock-in")
        assert response.status_code == 401

    def test_clock_in_succeeds(self, client):
        _authenticate()
        session = MagicMock(
            id="s1", agent_id="a1", work_date="2026-01-01", clock_in_at="2026-01-01T08:00:00+00:00",
            clock_out_at=None, total_work_seconds=None,
        )
        with patch(
            "src.api.routes.attendance._attendance_service.clock_in", return_value=session
        ) as mock_clock_in:
            response = client.post("/agents/clock-in")

        assert response.status_code == 200
        assert response.json()["clock_out_at"] is None
        mock_clock_in.assert_called_once_with("w1", "a1")

    def test_clock_in_conflict_returns_409(self, client):
        _authenticate()
        with patch(
            "src.api.routes.attendance._attendance_service.clock_in",
            side_effect=AlreadyClockedInError("already in"),
        ):
            response = client.post("/agents/clock-in")

        assert response.status_code == 409

    def test_clock_out_conflict_returns_409(self, client):
        _authenticate()
        with patch(
            "src.api.routes.attendance._attendance_service.clock_out",
            side_effect=NotClockedInError("not in"),
        ):
            response = client.post("/agents/clock-out")

        assert response.status_code == 409


class TestAux:
    def test_start_aux_requires_agent(self, client):
        response = client.post("/agents/aux/start", json={"aux_type": "meeting"})
        assert response.status_code == 401

    def test_start_aux_succeeds(self, client):
        _authenticate()
        event = MagicMock(
            id="x1", agent_id="a1", aux_type="meeting", started_at="2026-01-01T09:00:00+00:00",
            ended_at=None, duration_seconds=None, reason="standup",
        )
        with patch(
            "src.api.routes.attendance._attendance_service.start_aux", return_value=event
        ) as mock_start:
            response = client.post("/agents/aux/start", json={"aux_type": "meeting", "reason": "standup"})

        assert response.status_code == 200
        assert response.json()["aux_type"] == "meeting"
        mock_start.assert_called_once_with("w1", "a1", "meeting", "standup")

    def test_start_aux_without_session_returns_409(self, client):
        _authenticate()
        with patch(
            "src.api.routes.attendance._attendance_service.start_aux",
            side_effect=NotClockedInError("not clocked in"),
        ):
            response = client.post("/agents/aux/start", json={"aux_type": "meeting"})

        assert response.status_code == 409

    def test_end_aux_without_active_aux_returns_409(self, client):
        _authenticate()
        with patch(
            "src.api.routes.attendance._attendance_service.end_aux",
            side_effect=NoActiveAuxError("no active aux"),
        ):
            response = client.post("/agents/aux/end")

        assert response.status_code == 409


class TestAttendanceMe:
    def test_returns_none_session_and_aux_when_clocked_out(self, client):
        _authenticate()
        with patch("src.api.routes.attendance._attendance_service.get_current_session", return_value=None), \
             patch("src.api.routes.attendance._attendance_service.get_current_aux", return_value=None):
            response = client.get("/agents/attendance/me")

        assert response.status_code == 200
        body = response.json()
        assert body["session"] is None
        assert body["aux"] is None
        assert body["today_aux_history"] == []

    def test_returns_session_aux_and_history_when_clocked_in(self, client):
        _authenticate()
        session = MagicMock(
            id="s1", agent_id="a1", work_date="2026-01-01", clock_in_at="2026-01-01T08:00:00+00:00",
            clock_out_at=None, total_work_seconds=None,
        )
        aux = MagicMock(
            id="x1", agent_id="a1", aux_type="meeting", started_at="2026-01-01T09:00:00+00:00",
            ended_at=None, duration_seconds=None, reason=None,
        )
        with patch("src.api.routes.attendance._attendance_service.get_current_session", return_value=session), \
             patch("src.api.routes.attendance._attendance_service.get_current_aux", return_value=aux), \
             patch(
                 "src.api.routes.attendance._attendance_repository.list_aux_events_for_session",
                 return_value=[aux],
             ):
            response = client.get("/agents/attendance/me")

        assert response.status_code == 200
        body = response.json()
        assert body["session"]["id"] == "s1"
        assert body["aux"]["aux_type"] == "meeting"
        assert len(body["today_aux_history"]) == 1
