"""Tests for AdvisoryResponseLayer."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.services.advisory.advisory_layer import AdvisoryResponseLayer, AdvisoryResult
from src.services.advisory.intent_engine import BusinessIntent
from src.services.routing.product_router import ProductMatch


class TestAdvisoryResponseLayerRealComponents:
    """End-to-end with the real sub-engines (no mocks) — proves the pieces
    actually compose correctly, not just that each works in isolation."""

    def test_single_product_recommendation(self):
        layer = AdvisoryResponseLayer()
        result = layer.build("Tell me about SPIDIFY", [])
        assert result.needs_clarification is False
        assert result.primary_product == "SPIDIFY"
        assert result.complementary_products == []
        assert len(result.next_actions) > 0

    def test_business_theme_recommendation(self):
        layer = AdvisoryResponseLayer()
        result = layer.build("We want to modernize our HR operations", [])
        assert result.primary_product == "ZivaAIRA"
        assert set(result.complementary_products) == {"STAAS", "Havis Vacay", "PayCheq", "WeCare", "Havis iReport"}

    def test_explicit_comparison_is_not_clarified(self):
        layer = AdvisoryResponseLayer()
        result = layer.build("Compare SPIDIFY and ZivaAIRA", [])
        assert result.needs_clarification is False
        assert result.primary_product in ("SPIDIFY", "ZivaAIRA")

    def test_no_signal_question_has_no_recommendations(self):
        layer = AdvisoryResponseLayer()
        result = layer.build("What are your office hours?", [])
        assert result.recommendations == []
        assert result.primary_product is None
        assert result.next_actions == []

    def test_reuses_already_computed_product_match(self):
        layer = AdvisoryResponseLayer()
        match = ProductMatch(products=("PayCheq",), confidence="high")
        result = layer.build("How much does it cost?", [], product_match=match)
        assert result.primary_product == "PayCheq"


class TestAdvisoryResponseLayerClarification:
    def test_ambiguous_keyword_match_triggers_clarification(self):
        layer = AdvisoryResponseLayer()
        mock_intent_engine = MagicMock()
        mock_intent_engine.detect.return_value = BusinessIntent(
            question="q",
            products=("AppManage", "Havis eCertify"),
            confidence="ambiguous",
            via_theme=False,
            named_explicitly=False,
        )
        layer = AdvisoryResponseLayer(intent_engine=mock_intent_engine)
        result = layer.build("q", [])
        assert result.needs_clarification is True
        assert result.clarification is not None
        assert result.recommendations == []
        assert result.next_actions == []


class TestAdvisoryResponseLayerZeroSignal:
    """check_zero_signal() — the pre-retrieval guard used by
    ChatOrchestrator to ask before searching for a genuinely vague
    recommendation ask."""

    def test_fires_end_to_end_with_real_sub_engines(self):
        layer = AdvisoryResponseLayer()
        question = layer.check_zero_signal("Recommend the best solution for my business")
        assert question is not None
        assert "business problem" in question.lower()

    def test_named_product_question_does_not_fire(self):
        layer = AdvisoryResponseLayer()
        assert layer.check_zero_signal("Tell me about SPIDIFY") is None

    def test_ambiguous_two_product_question_does_not_fire(self):
        # Genuinely produces confidence="ambiguous", products=("SPIDIFY", "ZivaAIRA")
        # via the real classifier — confirmed by direct inspection, not assumed.
        layer = AdvisoryResponseLayer()
        assert layer.check_zero_signal("we need identity verification or recruitment help") is None

    def test_plain_knowledge_question_does_not_fire(self):
        layer = AdvisoryResponseLayer()
        assert layer.check_zero_signal("What are your office hours?") is None

    def test_intent_engine_failure_returns_none_not_exception(self):
        mock_intent_engine = MagicMock()
        mock_intent_engine.detect.side_effect = RuntimeError("boom")
        layer = AdvisoryResponseLayer(intent_engine=mock_intent_engine)
        assert layer.check_zero_signal("Recommend the best solution for my business") is None


class TestAdvisoryResponseLayerFailureIsolation:
    def test_recommendation_engine_failure_does_not_break_build(self):
        mock_rec_engine = MagicMock()
        mock_rec_engine.recommend.side_effect = RuntimeError("boom")
        layer = AdvisoryResponseLayer(recommendation_engine=mock_rec_engine)
        result = layer.build("Tell me about SPIDIFY", [])
        assert result.recommendations == []
        # next actions still attempted with an empty recommendation list
        assert isinstance(result.next_actions, list)

    def test_next_actions_engine_failure_does_not_break_build(self):
        mock_next_actions = MagicMock()
        mock_next_actions.generate.side_effect = RuntimeError("boom")
        layer = AdvisoryResponseLayer(next_actions_engine=mock_next_actions)
        result = layer.build("Tell me about SPIDIFY", [])
        assert result.next_actions == []
        assert result.primary_product == "SPIDIFY"  # recommendations still built

    def test_clarification_engine_failure_falls_through_to_normal_flow(self):
        mock_clarification = MagicMock()
        mock_clarification.check.side_effect = RuntimeError("boom")
        layer = AdvisoryResponseLayer(clarification_engine=mock_clarification)
        result = layer.build("Tell me about SPIDIFY", [])
        assert result.needs_clarification is False

    def test_intent_engine_failure_returns_blank_intent(self):
        mock_intent_engine = MagicMock()
        mock_intent_engine.detect.side_effect = RuntimeError("boom")
        layer = AdvisoryResponseLayer(intent_engine=mock_intent_engine)
        result = layer.build("Tell me about SPIDIFY", [])
        assert result.intent.products == ()
        assert result.recommendations == []


class TestAdvisoryResponseLayerAnalytics:
    def test_records_recommendation_and_business_problem(self):
        mock_analytics = MagicMock()
        layer = AdvisoryResponseLayer(analytics=mock_analytics)
        layer.build("Tell me about SPIDIFY", [])
        mock_analytics.record_recommendation.assert_any_call("SPIDIFY")
        mock_analytics.record_business_problem.assert_called()

    def test_records_comparison_for_two_plus_products(self):
        mock_analytics = MagicMock()
        layer = AdvisoryResponseLayer(analytics=mock_analytics)
        layer.build("Compare SPIDIFY and ZivaAIRA", [])
        mock_analytics.record_comparison.assert_called_once()
        call_args = mock_analytics.record_comparison.call_args[0][0]
        assert set(call_args) == {"SPIDIFY", "ZivaAIRA"}

    def test_analytics_failure_never_breaks_build(self):
        mock_analytics = MagicMock()
        mock_analytics.record_recommendation.side_effect = RuntimeError("boom")
        layer = AdvisoryResponseLayer(analytics=mock_analytics)
        result = layer.build("Tell me about SPIDIFY", [])
        assert result.primary_product == "SPIDIFY"

    def test_no_analytics_configured_is_fine(self):
        layer = AdvisoryResponseLayer(analytics=None)
        result = layer.build("Tell me about SPIDIFY", [])
        assert result.primary_product == "SPIDIFY"


class TestAdvisoryResultProperties:
    def test_primary_and_complementary_from_recommendations_order(self):
        from src.services.advisory.recommendation_engine import Recommendation

        recs = [
            Recommendation(product="A", confidence="high", reason="r", primary_benefit="b"),
            Recommendation(product="B", confidence="medium", reason="r", primary_benefit="b"),
        ]
        result = AdvisoryResult(intent=BusinessIntent(question="q"), recommendations=recs)
        assert result.primary_product == "A"
        assert result.complementary_products == ["B"]

    def test_empty_recommendations_yields_none_and_empty_list(self):
        result = AdvisoryResult(intent=BusinessIntent(question="q"))
        assert result.primary_product is None
        assert result.complementary_products == []

    def test_theme_with_explicit_primary_uses_intent_primary(self):
        from src.services.advisory.recommendation_engine import Recommendation

        # Recommendation order need not match intent.primary — the result
        # must still defer to the intent's real primary designation.
        recs = [
            Recommendation(product="STAAS", confidence="medium", reason="r", primary_benefit="b"),
            Recommendation(product="ZivaAIRA", confidence="high", reason="r", primary_benefit="b"),
        ]
        intent = BusinessIntent(
            question="q", products=("STAAS", "ZivaAIRA"), confidence="ambiguous",
            primary="ZivaAIRA", via_theme=True,
        )
        result = AdvisoryResult(intent=intent, recommendations=recs)
        assert result.primary_product == "ZivaAIRA"
        assert result.complementary_products == ["STAAS"]

    def test_theme_with_no_primary_never_picks_an_arbitrary_leader(self):
        """Confirmed live bug this guards: digital_transformation (7
        products, deliberately no single dominant one) was picking
        whichever product happened to be first in the theme's tuple as if
        it were a real recommendation — contradicting the theme's own
        design and silencing ResponseGenerator's "no single dominant"
        framing entirely."""
        from src.services.advisory.recommendation_engine import Recommendation

        recs = [
            Recommendation(product="ZivaAIRA", confidence="medium", reason="r", primary_benefit="b"),
            Recommendation(product="STAAS", confidence="low", reason="r", primary_benefit="b"),
        ]
        intent = BusinessIntent(
            question="q", products=("ZivaAIRA", "STAAS"), confidence="ambiguous",
            primary=None, via_theme=True,
        )
        result = AdvisoryResult(intent=intent, recommendations=recs)
        assert result.primary_product is None
        assert set(result.complementary_products) == {"ZivaAIRA", "STAAS"}
