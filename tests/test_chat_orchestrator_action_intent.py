"""Integration tests proving ChatOrchestrator's action-intent short-circuit
(Step 0.6) actually keeps live-chat/escalation/appointment requests out of
retrieval end-to-end.

Live-confirmed bug this fixes: "Can you arrange a quick chat with a
specialist?" got an improvised "Absolutely — I can set up a quick chat..."
(no backend action taken), and the follow-up "Today 1:45pm WAT, live chat"
had zero KB evidence and fell through to a live web search, returning
unrelated timezone/city content (Los Angeles, Chicago, SavvyCal, ...)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from src.orchestrator.chat_orchestrator import ChatOrchestrator
from src.services.advisory.session_context import SessionContext
from src.services.routing.source_router import RoutingDecision
from src.services.session.session_service import SessionService


def _make_orchestrator(appointment_service=None):
    source_router = MagicMock()
    source_router.route.return_value = RoutingDecision(knowledge=True, web=False)

    search_manager = MagicMock()
    search_manager.retrieve.return_value = []
    search_manager.product_match = None

    response_generator = MagicMock()
    response_generator.generate.return_value = {"answer": "Answer.", "citations": []}

    orchestrator = ChatOrchestrator(
        source_router=source_router,
        search_manager=search_manager,
        response_generator=response_generator,
        appointment_service=appointment_service,
    )
    return orchestrator, source_router, search_manager, response_generator


def _make_stateful_orchestrator(appointment_service=None, escalation_service=None):
    """Same collaborators as _make_orchestrator, but with a REAL
    SessionService/SessionContext wired in so pending-action state actually
    carries across turns (Phase 2 — confirmed, stateful workflows)."""
    source_router = MagicMock()
    source_router.route.return_value = RoutingDecision(knowledge=True, web=False)

    search_manager = MagicMock()
    search_manager.retrieve.return_value = []
    search_manager.product_match = None

    response_generator = MagicMock()
    response_generator.generate.return_value = {"answer": "Answer.", "citations": []}

    orchestrator = ChatOrchestrator(
        source_router=source_router,
        search_manager=search_manager,
        response_generator=response_generator,
        appointment_service=appointment_service,
        escalation_service=escalation_service,
        session_service=SessionService(session_context=SessionContext()),
    )
    return orchestrator, source_router, search_manager, response_generator


class TestActionIntentShortCircuit:
    def test_escalation_request_never_reaches_retrieval(self):
        orchestrator, source_router, search_manager, response_generator = _make_orchestrator()

        result = orchestrator.chat("Can you arrange a quick chat with a specialist?")

        source_router.route.assert_not_called()
        search_manager.retrieve.assert_not_called()
        response_generator.generate.assert_not_called()
        assert "arrange" not in result["answer"].lower() or "have" not in result["answer"].lower()

    def test_escalation_answer_never_claims_success(self):
        orchestrator, *_rest = _make_orchestrator()

        result = orchestrator.chat("Can you arrange a quick chat with a specialist?")

        answer_lower = result["answer"].lower()
        for phrase in ("absolutely", "i've set", "i have set", "all set", "arranged for you", "connected you"):
            assert phrase not in answer_lower

    def test_escalation_recommended_flag_set(self):
        orchestrator, *_rest = _make_orchestrator()

        result = orchestrator.chat("Can you arrange a quick chat with a specialist?")

        assert result["escalation_recommended"] is True
        assert result["escalation_reason"] == "explicit_request"

    def test_appointment_request_never_reaches_retrieval(self):
        orchestrator, source_router, search_manager, response_generator = _make_orchestrator()

        orchestrator.chat("I'd like to book an appointment")

        source_router.route.assert_not_called()
        search_manager.retrieve.assert_not_called()
        response_generator.generate.assert_not_called()

    def test_appointment_answer_never_fabricates_a_time(self):
        """Live-confirmed bug: the customer said "1:45pm" — not a real
        bookable slot — and must never see that time echoed back as if it
        were confirmed."""
        mock_appointments = MagicMock()
        mock_appointments.get_availability.return_value = []
        orchestrator, *_rest = _make_orchestrator(appointment_service=mock_appointments)

        result = orchestrator.chat("I'd like to book an appointment")

        assert "1:45" not in result["answer"]
        answer_lower = result["answer"].lower()
        for phrase in ("you're booked", "you are booked", "i've booked", "i have booked", "confirmed for"):
            assert phrase not in answer_lower

    def test_appointment_answer_lists_real_availability(self):
        from types import SimpleNamespace

        mock_appointments = MagicMock()
        mock_appointments.get_availability.return_value = [
            SimpleNamespace(
                date="2026-08-13", day_label="Thu", fully_booked=False,
                slots=[{"time": "09:00", "available": True}, {"time": "10:30", "available": False}],
            ),
        ]
        orchestrator, *_rest = _make_orchestrator(appointment_service=mock_appointments)

        result = orchestrator.chat("I'd like to book an appointment")

        assert "Thu 09:00" in result["answer"]
        assert "Thu 10:30" not in result["answer"]  # not available — must not be offered

    def test_ordinary_product_question_unaffected(self):
        orchestrator, source_router, search_manager, response_generator = _make_orchestrator()

        orchestrator.chat("What does SPIDIFY do?")

        source_router.route.assert_called_once()
        search_manager.retrieve.assert_called_once()
        response_generator.generate.assert_called_once()

    def test_two_turn_live_bug_regression(self):
        """Reproduces the exact reported transcript across two turns in the
        same session — neither turn should ever reach the search manager,
        so neither can produce unrelated web-search content."""
        orchestrator, source_router, search_manager, response_generator = _make_orchestrator()

        r1 = orchestrator.chat("Can you arrange a quick chat with a specialist?", session_id="s1")
        r2 = orchestrator.chat("Today 1:45pm WAT, live chat", session_id="s1")

        search_manager.retrieve.assert_not_called()
        for result in (r1, r2):
            answer_lower = result["answer"].lower()
            for junk in ("los angeles", "chicago", "savvycal", "federal reserve", "white house"):
                assert junk not in answer_lower


class TestStatefulEscalationFlow:
    def test_ack_then_yes_creates_real_escalation(self):
        escalation_service = MagicMock()
        escalation_service.create_direct.return_value = SimpleNamespace(department="Support", assigned_agent_id="a1")
        orchestrator, source_router, search_manager, response_generator = _make_stateful_orchestrator(
            escalation_service=escalation_service
        )

        r1 = orchestrator.chat(
            "Can you arrange a quick chat with a specialist?",
            session_id="s1", workspace_id="w1", workspace_name="Ha-Shem",
        )
        assert "would you like" in r1["answer"].lower()
        escalation_service.create_direct.assert_not_called()  # not yet — awaiting confirmation

        r2 = orchestrator.chat("Yes", session_id="s1", workspace_id="w1", workspace_name="Ha-Shem")

        escalation_service.create_direct.assert_called_once()
        assert "connected" in r2["answer"].lower()
        search_manager.retrieve.assert_not_called()
        response_generator.generate.assert_not_called()

    def test_no_cancels_without_backend_call(self):
        escalation_service = MagicMock()
        orchestrator, *_rest = _make_stateful_orchestrator(escalation_service=escalation_service)

        orchestrator.chat("Can you arrange a quick chat with a specialist?", session_id="s1")
        r2 = orchestrator.chat("No", session_id="s1")

        escalation_service.create_direct.assert_not_called()
        assert "cancelled" in r2["answer"].lower()

    def test_bare_hi_then_yes_with_no_pending_action_triggers_nothing(self):
        """Safety requirement: a bare "Yes" must never be misread as
        confirming an action that was never proposed."""
        escalation_service = MagicMock()
        orchestrator, source_router, search_manager, response_generator = _make_stateful_orchestrator(
            escalation_service=escalation_service
        )

        orchestrator.chat("Hi", session_id="s1")
        orchestrator.chat("Yes", session_id="s1")

        escalation_service.create_direct.assert_not_called()
        # "Yes" with no pending action falls through to the ordinary pipeline.
        search_manager.retrieve.assert_called()


class TestStatefulAppointmentFlow:
    def test_full_flow_collects_slot_name_email_then_books(self):
        appointment_service = MagicMock()
        appointment_service.get_availability.return_value = [
            SimpleNamespace(date="2026-08-13", day_label="Thu", fully_booked=False, slots=[{"time": "09:00", "available": True}]),
        ]
        appointment_service.book.return_value = SimpleNamespace(appointment_date="2026-08-13", time_slot="09:00")
        orchestrator, *_rest = _make_stateful_orchestrator(appointment_service=appointment_service)

        r1 = orchestrator.chat("I'd like to book an appointment", session_id="s1")
        assert "Thu 09:00" in r1["answer"]

        r2 = orchestrator.chat("Thu 09:00", session_id="s1")
        assert "name" in r2["answer"].lower()

        r3 = orchestrator.chat("Jane Doe", session_id="s1")
        assert "email" in r3["answer"].lower()

        r4 = orchestrator.chat("jane@example.com", session_id="s1")
        assert "would you like me to confirm" in r4["answer"].lower()

        r5 = orchestrator.chat("Yes", session_id="s1")
        appointment_service.book.assert_called_once_with("2026-08-13", "09:00", "Jane Doe", "jane@example.com", workspace_id=None)
        assert "confirmed" in r5["answer"].lower()


class TestStatefulDemoFlow:
    def test_known_product_from_session_skips_product_question(self):
        from unittest.mock import patch

        response_generator = MagicMock()
        response_generator.generate.return_value = {"answer": "SPIDIFY does X [1].", "citations": []}
        search_manager = MagicMock()
        search_manager.retrieve.return_value = []
        search_manager.product_match = None
        source_router = MagicMock()
        source_router.route.return_value = RoutingDecision(knowledge=True, web=False)

        session_service = SessionService(session_context=SessionContext())
        orchestrator = ChatOrchestrator(
            source_router=source_router,
            search_manager=search_manager,
            response_generator=response_generator,
            session_service=session_service,
        )
        # Simulate the session having already discussed SPIDIFY this turn.
        session_service.record_products("s1", ["SPIDIFY"])

        r1 = orchestrator.chat("I want a demo", session_id="s1")

        assert "which havisiq" not in r1["answer"].lower()
        assert "name" in r1["answer"].lower()

    def test_full_flow_submits_demo_request_on_confirmation(self):
        from unittest.mock import patch

        orchestrator, *_rest = _make_stateful_orchestrator()

        r1 = orchestrator.chat("I want a demo", session_id="s1")
        assert "which havisiq" in r1["answer"].lower()

        r2 = orchestrator.chat("SPIDIFY", session_id="s1")
        assert "name" in r2["answer"].lower()

        r3 = orchestrator.chat("Jane Doe", session_id="s1")
        assert "email" in r3["answer"].lower()

        r4 = orchestrator.chat("jane@example.com", session_id="s1")
        assert "company" in r4["answer"].lower()

        r5 = orchestrator.chat("skip", session_id="s1")
        assert "would you like me to submit" in r5["answer"].lower()

        with patch("src.api.services.demo_requests.submit_demo_request") as mock_submit:
            mock_submit.return_value = {"id": "d1"}
            r6 = orchestrator.chat("Yes", session_id="s1")

        mock_submit.assert_called_once_with(
            name="Jane Doe", email="jane@example.com", company=None, use_case="I want a demo", product="SPIDIFY",
        )
        assert "submitted" in r6["answer"].lower()
