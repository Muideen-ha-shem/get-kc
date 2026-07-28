"""Tests for SessionService — the thin adapter ChatOrchestrator depends on."""

from __future__ import annotations

from src.services.advisory.session_context import SessionContext
from src.services.session.session_service import SessionService


class TestSessionServiceBasics:
    def test_new_session_id_is_unique(self):
        a, b = SessionService.new_session_id(), SessionService.new_session_id()
        assert a != b

    def test_resolve_reference_without_session_id_returns_question_unchanged(self):
        service = SessionService()
        assert service.resolve_reference(None, "How much does it cost?") == "How much does it cost?"

    def test_get_state_without_session_id_returns_none(self):
        service = SessionService()
        assert service.get_state(None) is None

    def test_record_methods_are_no_ops_without_session_id(self):
        service = SessionService()
        # Must not raise.
        service.record_products(None, ["SPIDIFY"])
        service.record_recommendation(None, "SPIDIFY")
        service.record_comparison(None, ["SPIDIFY", "ZivaAIRA"])
        service.record_business_problem(None, "identity verification")


class TestSessionServiceDelegatesToSessionContext:
    def test_pronoun_resolution_after_recording_a_product(self):
        context = SessionContext()
        service = SessionService(session_context=context)
        session_id = "s1"

        service.record_products(session_id, ["SPIDIFY"])
        resolved = service.resolve_reference(session_id, "How much does it cost?")

        assert "SPIDIFY" in resolved

    def test_get_state_reflects_recorded_recommendation(self):
        context = SessionContext()
        service = SessionService(session_context=context)
        session_id = "s1"

        service.record_recommendation(session_id, "SPIDIFY")
        state = service.get_state(session_id)

        assert state is not None
        assert "SPIDIFY" in state.recommended_products
