"""Tests for ChatOrchestrator's Phase 19 advisory-layer wiring.

Focused on what's new this phase — the clarification short-circuit, the
recommendation-driven primary/complementary framing, and next_actions
attachment — not a full re-test of the retrieval/generation pipeline
(already covered by SearchManager/ResponseGenerator's own suites).
"""

from __future__ import annotations

from unittest.mock import MagicMock

from src.api.schemas import ChatResponse
from src.orchestrator.chat_orchestrator import ChatOrchestrator
from src.services.advisory.advisory_layer import AdvisoryResult
from src.services.advisory.intent_engine import BusinessIntent
from src.services.advisory.next_actions import NextAction
from src.services.advisory.recommendation_engine import Recommendation
from src.services.routing.source_router import RoutingDecision


def _make_orchestrator(*, advisory_layer=None, evidence=None, generate_return=None):
    if advisory_layer is not None:
        # MagicMock() auto-creates attributes returning a truthy MagicMock
        # by default — without this, the new zero-signal guard clause
        # (ChatOrchestrator._chat_new_pipeline) would incorrectly
        # short-circuit every test in this file that passes a mocked
        # advisory_layer, since `check_zero_signal(...) is not None` would
        # always be True. A test that specifically wants to exercise the
        # zero-signal-fires path can still override this afterward.
        advisory_layer.check_zero_signal.return_value = None

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
    ), response_generator


class TestChatOrchestratorZeroSignalGuard:
    """The pre-Step-1 guard added to fix the live-confirmed bug: a vague
    recommendation ask must never reach SourceRouter/SearchManager at
    all — a real skip, not a post-hoc discard of search results."""

    def test_zero_signal_short_circuits_without_calling_search_or_generation(self):
        mock_advisory = MagicMock()
        orchestrator, response_generator = _make_orchestrator(advisory_layer=mock_advisory)
        # _make_orchestrator defaults check_zero_signal to None — override
        # afterward for this specific test, which wants the firing path.
        mock_advisory.check_zero_signal.return_value = "Which business problem are you trying to solve?"

        result = orchestrator.chat("Recommend the best solution for my business")

        assert result["answer"] == "Which business problem are you trying to solve?"
        assert result["sources"] == []
        assert result["next_actions"] == []
        assert result["escalation_recommended"] is False
        orchestrator._source_router.route.assert_not_called()
        orchestrator._search_manager.retrieve.assert_not_called()
        response_generator.generate.assert_not_called()

    def test_non_zero_signal_question_still_searches_normally(self):
        mock_advisory = MagicMock()
        mock_advisory.check_zero_signal.return_value = None
        mock_advisory.build.return_value = AdvisoryResult(intent=BusinessIntent(question="q"))
        orchestrator, response_generator = _make_orchestrator(advisory_layer=mock_advisory)

        orchestrator.chat("Tell me about SPIDIFY")

        orchestrator._source_router.route.assert_called_once()
        orchestrator._search_manager.retrieve.assert_called_once()
        response_generator.generate.assert_called_once()

    def test_no_advisory_layer_skips_guard_entirely(self):
        orchestrator, response_generator = _make_orchestrator()

        orchestrator.chat("Recommend the best solution for my business")

        orchestrator._source_router.route.assert_called_once()
        orchestrator._search_manager.retrieve.assert_called_once()


class TestChatOrchestratorNoAdvisoryLayer:
    """advisory_layer=None must behave exactly like pre-Phase-19 code."""

    def test_no_next_actions_attached(self):
        orchestrator, _ = _make_orchestrator()
        result = orchestrator.chat("What are your office hours?")
        assert result["next_actions"] == []

    def test_via_theme_fallback_still_drives_framing(self):
        from src.services.routing.product_router import ProductMatch

        orchestrator, response_generator = _make_orchestrator()
        orchestrator._search_manager.product_match = ProductMatch(
            products=("ZivaAIRA", "STAAS"), confidence="ambiguous", primary="ZivaAIRA", via_theme=True,
        )
        orchestrator.chat("We want to modernize our HR operations")
        response_generator.generate.assert_called_once()
        kwargs = response_generator.generate.call_args.kwargs
        assert kwargs["primary_product"] == "ZivaAIRA"
        assert kwargs["complementary_products"] == ["STAAS"]


class TestChatOrchestratorWithAdvisoryLayer:
    def test_clarification_short_circuits_without_calling_response_generator(self):
        mock_advisory = MagicMock()
        mock_advisory.build.return_value = AdvisoryResult(
            intent=BusinessIntent(question="q"),
            clarification="Are you looking for X or Y?",
        )
        orchestrator, response_generator = _make_orchestrator(advisory_layer=mock_advisory)

        result = orchestrator.chat("some ambiguous need")

        assert result["answer"] == "Are you looking for X or Y?"
        assert result["sources"] == []
        assert result["next_actions"] == []
        response_generator.generate.assert_not_called()

    def test_recommendation_drives_primary_and_complementary(self):
        mock_advisory = MagicMock()
        mock_advisory.build.return_value = AdvisoryResult(
            intent=BusinessIntent(question="q", products=("SPIDIFY",), confidence="high"),
            recommendations=[Recommendation(product="SPIDIFY", confidence="high", reason="r", primary_benefit="b")],
            next_actions=[NextAction(label="Learn more", action_type="learn_more", target="SPIDIFY")],
        )
        orchestrator, response_generator = _make_orchestrator(advisory_layer=mock_advisory)

        result = orchestrator.chat("We need identity verification")

        kwargs = response_generator.generate.call_args.kwargs
        assert kwargs["primary_product"] == "SPIDIFY"
        assert kwargs["complementary_products"] == []
        assert result["next_actions"] == [{"label": "Learn more", "action_type": "learn_more", "target": "SPIDIFY"}]

    def test_advisory_layer_receives_evidence_and_product_match(self):
        from src.services.routing.product_router import ProductMatch

        mock_advisory = MagicMock()
        mock_advisory.build.return_value = AdvisoryResult(intent=BusinessIntent(question="q"))
        match = ProductMatch(products=("SPIDIFY",), confidence="high")

        orchestrator, _ = _make_orchestrator(advisory_layer=mock_advisory, evidence=["ev1", "ev2"])
        orchestrator._search_manager.product_match = match

        orchestrator.chat("Tell me about SPIDIFY")

        mock_advisory.build.assert_called_once_with("Tell me about SPIDIFY", ["ev1", "ev2"], product_match=match)

    def test_empty_next_actions_still_reaches_final_response(self):
        mock_advisory = MagicMock()
        mock_advisory.build.return_value = AdvisoryResult(intent=BusinessIntent(question="q"))
        orchestrator, _ = _make_orchestrator(advisory_layer=mock_advisory)
        result = orchestrator.chat("generic question")
        assert result["next_actions"] == []


class TestProcessRequestResponseNextActions:
    def test_next_actions_included_in_chat_response(self):
        mock_advisory = MagicMock()
        mock_advisory.build.return_value = AdvisoryResult(
            intent=BusinessIntent(question="q", products=("SPIDIFY",), confidence="high"),
            recommendations=[Recommendation(product="SPIDIFY", confidence="high", reason="r", primary_benefit="b")],
            next_actions=[NextAction(label="Learn more", action_type="learn_more", target="SPIDIFY")],
        )
        orchestrator, _ = _make_orchestrator(advisory_layer=mock_advisory)

        response = orchestrator.process_request_response("We need identity verification")

        assert isinstance(response, ChatResponse)
        assert response.next_actions is not None
        assert response.next_actions[0].label == "Learn more"
        assert response.next_actions[0].action_type == "learn_more"

    def test_no_next_actions_yields_none_not_empty_list(self):
        orchestrator, _ = _make_orchestrator()  # no advisory_layer
        response = orchestrator.process_request_response("What are your office hours?")
        assert response.next_actions is None

    def test_clarification_response_has_no_sources_or_next_actions(self):
        mock_advisory = MagicMock()
        mock_advisory.build.return_value = AdvisoryResult(
            intent=BusinessIntent(question="q"), clarification="Which one did you mean?",
        )
        orchestrator, _ = _make_orchestrator(advisory_layer=mock_advisory)
        response = orchestrator.process_request_response("ambiguous question")
        assert response.answer == "Which one did you mean?"
        assert response.sources == []
        assert response.next_actions is None
