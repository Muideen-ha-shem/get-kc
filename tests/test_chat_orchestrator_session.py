"""Tests for ChatOrchestrator's Phase 20 session wiring — pronoun
resolution, session recording, session_id passthrough, and personalization
via profile_context. All additive: no session_service configured must
behave exactly like Phase 19."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.orchestrator.chat_orchestrator import ChatOrchestrator
from src.services.advisory.advisory_layer import AdvisoryResult
from src.services.advisory.intent_engine import BusinessIntent
from src.services.advisory.session_context import SessionContext
from src.services.advisory.recommendation_engine import Recommendation
from src.services.routing.source_router import RoutingDecision
from src.services.session.session_service import SessionService


def _make_orchestrator(*, advisory_layer=None, session_service=None, evidence=None, generate_return=None):
    source_router = MagicMock()
    source_router.route.return_value = RoutingDecision(knowledge=True, web=False)

    search_manager = MagicMock()
    search_manager.retrieve.return_value = evidence or []
    search_manager.product_match = None

    response_generator = MagicMock()
    response_generator.generate.return_value = generate_return or {"answer": "Answer.", "citations": []}

    return ChatOrchestrator(
        source_router=source_router,
        search_manager=search_manager,
        response_generator=response_generator,
        advisory_layer=advisory_layer,
        session_service=session_service,
    ), search_manager, response_generator


class TestNoSessionServiceIsUnchanged:
    def test_result_has_no_session_id_when_service_absent(self):
        orchestrator, _, _ = _make_orchestrator()
        result = orchestrator.chat("What are your office hours?")
        assert result["session_id"] is None

    def test_clarification_short_circuit_still_has_session_id_key(self):
        mock_advisory = MagicMock()
        mock_advisory.build.return_value = AdvisoryResult(
            intent=BusinessIntent(question="q"), clarification="Which one?",
        )
        orchestrator, _, _ = _make_orchestrator(advisory_layer=mock_advisory)
        result = orchestrator.chat("ambiguous")
        assert result["session_id"] is None


class TestSessionIdGeneration:
    def test_new_session_id_generated_when_service_present_but_none_given(self):
        service = SessionService(session_context=SessionContext())
        orchestrator, _, _ = _make_orchestrator(session_service=service)

        result = orchestrator.chat("What are your office hours?")

        assert result["session_id"] is not None

    def test_process_request_response_echoes_session_id(self):
        service = SessionService(session_context=SessionContext())
        orchestrator, _, _ = _make_orchestrator(session_service=service)

        response = orchestrator.process_request_response("hello", session_id="fixed-session")

        assert response.session_id == "fixed-session"


class TestPronounResolution:
    def test_it_resolves_to_last_discussed_product_before_retrieval(self):
        context = SessionContext()
        context.record_products("s1", ["SPIDIFY"])
        service = SessionService(session_context=context)

        mock_advisory = MagicMock()
        mock_advisory.build.return_value = AdvisoryResult(intent=BusinessIntent(question="q"))
        orchestrator, search_manager, _ = _make_orchestrator(advisory_layer=mock_advisory, session_service=service)

        orchestrator.chat("How much does it cost?", session_id="s1")

        retrieved_question = search_manager.retrieve.call_args[0][0]
        assert "SPIDIFY" in retrieved_question

    def test_no_session_history_leaves_question_unchanged(self):
        service = SessionService(session_context=SessionContext())
        mock_advisory = MagicMock()
        mock_advisory.build.return_value = AdvisoryResult(intent=BusinessIntent(question="q"))
        orchestrator, search_manager, _ = _make_orchestrator(advisory_layer=mock_advisory, session_service=service)

        orchestrator.chat("How much does it cost?", session_id="fresh-session")

        retrieved_question = search_manager.retrieve.call_args[0][0]
        assert retrieved_question == "How much does it cost?"


class TestSessionRecording:
    def test_discussed_product_recorded_after_turn(self):
        context = SessionContext()
        service = SessionService(session_context=context)
        mock_advisory = MagicMock()
        mock_advisory.build.return_value = AdvisoryResult(
            intent=BusinessIntent(question="q", products=("SPIDIFY",), confidence="high"),
            recommendations=[Recommendation(product="SPIDIFY", confidence="high", reason="r", primary_benefit="b")],
        )
        orchestrator, _, _ = _make_orchestrator(advisory_layer=mock_advisory, session_service=service)

        orchestrator.chat("Tell me about SPIDIFY", session_id="s1")

        state = context.get("s1")
        assert "SPIDIFY" in state.discussed_products
        assert "SPIDIFY" in state.recommended_products

    def test_clarification_turn_does_not_record_session_state(self):
        context = SessionContext()
        service = SessionService(session_context=context)
        mock_advisory = MagicMock()
        mock_advisory.build.return_value = AdvisoryResult(
            intent=BusinessIntent(question="q", products=("AppManage", "Havis eCertify")),
            clarification="Which one?",
        )
        orchestrator, _, _ = _make_orchestrator(advisory_layer=mock_advisory, session_service=service)

        orchestrator.chat("ambiguous need", session_id="s1")

        state = context.get("s1")
        assert state.discussed_products == []


class TestPersonalization:
    def test_profile_context_prefixed_only_for_advisory_question(self):
        mock_advisory = MagicMock()
        mock_advisory.build.return_value = AdvisoryResult(intent=BusinessIntent(question="q"))
        orchestrator, search_manager, response_generator = _make_orchestrator(advisory_layer=mock_advisory)

        orchestrator.chat("We need customer onboarding", profile_context="ABC Bank — Financial Services")

        advisory_question = mock_advisory.build.call_args[0][0]
        assert advisory_question.startswith("ABC Bank — Financial Services")
        assert "We need customer onboarding" in advisory_question

        retrieved_question = search_manager.retrieve.call_args[0][0]
        assert retrieved_question == "We need customer onboarding"

        generation_question = response_generator.generate.call_args.kwargs["question"]
        assert generation_question == "We need customer onboarding"

    def test_no_profile_context_leaves_advisory_question_unchanged(self):
        mock_advisory = MagicMock()
        mock_advisory.build.return_value = AdvisoryResult(intent=BusinessIntent(question="q"))
        orchestrator, _, _ = _make_orchestrator(advisory_layer=mock_advisory)

        orchestrator.chat("We need customer onboarding")

        advisory_question = mock_advisory.build.call_args[0][0]
        assert advisory_question == "We need customer onboarding"
