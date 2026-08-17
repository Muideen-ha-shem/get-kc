"""Tests for AttendanceService — clock in/out and AUX transitions (Agent
Operations). All of section 26's clocking rules, plus SupportAgent.status
sync at each transition (load-bearing for auto-assignment)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.services.agents.attendance_service import (
    AlreadyClockedInError,
    AttendanceService,
    NoActiveAuxError,
    NotClockedInError,
)


def _session(**overrides):
    base = {"id": "s1", "clock_in_at": "2026-01-01T08:00:00+00:00"}
    base.update(overrides)
    return SimpleNamespace(**base)


def _aux(**overrides):
    base = {"id": "x1", "aux_type": "meeting", "started_at": "2026-01-01T09:00:00+00:00"}
    base.update(overrides)
    return SimpleNamespace(**base)


def _make_service():
    repo = MagicMock()
    agents = MagicMock()
    return AttendanceService(repository=repo, agent_service=agents), repo, agents


class TestClockIn:
    def test_clock_in_succeeds_and_sets_status_available(self):
        service, repo, agents = _make_service()
        repo.get_active_session.return_value = None
        repo.clock_in.return_value = _session()

        service.clock_in("w1", "a1")

        repo.clock_in.assert_called_once_with("w1", "a1")
        agents.update_status.assert_called_once_with("a1", "available")

    def test_double_clock_in_rejected(self):
        service, repo, agents = _make_service()
        repo.get_active_session.return_value = _session()

        with pytest.raises(AlreadyClockedInError):
            service.clock_in("w1", "a1")
        repo.clock_in.assert_not_called()
        agents.update_status.assert_not_called()


class TestClockOut:
    def test_clock_out_while_out_rejected(self):
        service, repo, agents = _make_service()
        repo.get_active_session.return_value = None

        with pytest.raises(NotClockedInError):
            service.clock_out("a1")
        repo.clock_out.assert_not_called()

    def test_clock_out_sets_status_offline_and_computes_duration(self):
        from datetime import datetime, timedelta, timezone

        service, repo, agents = _make_service()
        clock_in_at = datetime.now(timezone.utc) - timedelta(hours=4)
        repo.get_active_session.return_value = _session(clock_in_at=clock_in_at.isoformat())
        repo.get_active_aux.return_value = None
        repo.clock_out.return_value = _session(clock_out_at="now", total_work_seconds=14400)

        service.clock_out("a1")

        called_session_id, called_seconds = repo.clock_out.call_args[0]
        assert called_session_id == "s1"
        assert called_seconds == pytest.approx(4 * 3600, abs=5)
        agents.update_status.assert_called_once_with("a1", "offline")

    def test_clock_out_force_ends_active_aux(self):
        service, repo, agents = _make_service()
        repo.get_active_session.return_value = _session()
        repo.get_active_aux.return_value = _aux(id="x1", started_at="2026-01-01T09:00:00+00:00")
        repo.clock_out.return_value = _session(clock_out_at="now")

        service.clock_out("a1")

        repo.end_aux.assert_called_once()
        assert repo.end_aux.call_args[0][0] == "x1"


class TestAux:
    def test_start_aux_without_session_rejected(self):
        service, repo, agents = _make_service()
        repo.get_active_session.return_value = None

        with pytest.raises(NotClockedInError):
            service.start_aux("w1", "a1", "meeting")
        repo.start_aux.assert_not_called()

    def test_start_aux_sets_status_away(self):
        service, repo, agents = _make_service()
        repo.get_active_session.return_value = _session()
        repo.get_active_aux.return_value = None
        repo.start_aux.return_value = _aux()

        service.start_aux("w1", "a1", "meeting", reason="standup")

        repo.start_aux.assert_called_once_with("w1", "a1", "s1", "meeting", "standup")
        agents.update_status.assert_called_once_with("a1", "away")

    def test_starting_a_second_aux_ends_the_first_first(self):
        """Only one active AUX at a time — enforced by auto-ending the
        previous one, not by rejecting the new request (see the module
        docstring for why: switching Meeting -> Break is one action)."""
        service, repo, agents = _make_service()
        repo.get_active_session.return_value = _session()
        repo.get_active_aux.return_value = _aux(id="x1", aux_type="meeting", started_at="2026-01-01T09:00:00+00:00")
        repo.start_aux.return_value = _aux(id="x2", aux_type="break")

        service.start_aux("w1", "a1", "break")

        repo.end_aux.assert_called_once()
        assert repo.end_aux.call_args[0][0] == "x1"
        repo.start_aux.assert_called_once_with("w1", "a1", "s1", "break", None)

    def test_end_aux_without_active_aux_rejected(self):
        service, repo, agents = _make_service()
        repo.get_active_aux.return_value = None

        with pytest.raises(NoActiveAuxError):
            service.end_aux("a1")
        repo.end_aux.assert_not_called()

    def test_end_aux_sets_status_available(self):
        service, repo, agents = _make_service()
        repo.get_active_aux.return_value = _aux(id="x1", started_at="2026-01-01T09:00:00+00:00")
        repo.end_aux.return_value = _aux(id="x1", ended_at="now", duration_seconds=1800)

        service.end_aux("a1")

        repo.end_aux.assert_called_once()
        assert repo.end_aux.call_args[0][0] == "x1"
        agents.update_status.assert_called_once_with("a1", "available")
