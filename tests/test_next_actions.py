"""Tests for NextActionsEngine."""

from __future__ import annotations

from src.services.advisory.intent_engine import BusinessIntent
from src.services.advisory.next_actions import NextActionsEngine
from src.services.advisory.recommendation_engine import Recommendation


def _rec(product: str, **kwargs) -> Recommendation:
    defaults = dict(confidence="high", reason="r", primary_benefit="b")
    defaults.update(kwargs)
    return Recommendation(product=product, **defaults)


class TestNextActionsProductDiscussion:
    def test_single_product_gets_learn_more_demo_expert_no_compare(self):
        engine = NextActionsEngine()
        intent = BusinessIntent(question="Tell me about SPIDIFY", products=("SPIDIFY",), confidence="high")
        actions = engine.generate(intent, [_rec("SPIDIFY")])
        types = [a.action_type for a in actions]
        assert "learn_more" in types
        assert "request_demo" in types
        assert "talk_to_expert" in types
        assert "compare" not in types  # nothing to compare against

    def test_multiple_recommendations_adds_compare(self):
        engine = NextActionsEngine()
        intent = BusinessIntent(
            question="q", products=("ZivaAIRA", "STAAS"), confidence="ambiguous", via_theme=True, primary="ZivaAIRA",
        )
        recs = [_rec("ZivaAIRA", related=("STAAS",)), _rec("STAAS", confidence="medium")]
        actions = engine.generate(intent, recs)
        assert any(a.action_type == "compare" for a in actions)

    def test_theme_with_no_primary_uses_neutral_explore_phrasing(self):
        """Confirmed live bug this guards: a no-single-dominant theme
        (e.g. digital transformation across 7 products) was naming
        whichever product happened to be listed first as if it were "the"
        recommendation to learn more about / demo — arbitrary, not real."""
        engine = NextActionsEngine()
        intent = BusinessIntent(
            question="We are digitizing our company",
            products=("ZivaAIRA", "STAAS", "PayCheq"),
            confidence="ambiguous",
            via_theme=True,
            primary=None,
        )
        recs = [_rec("ZivaAIRA"), _rec("STAAS"), _rec("PayCheq")]
        actions = engine.generate(intent, recs)
        assert all(a.target is None for a in actions)
        assert [a.action_type for a in actions] == ["learn_more", "compare", "request_demo", "talk_to_expert"]
        assert "ZivaAIRA" not in actions[0].label

    def test_primary_recommendation_drives_targets(self):
        engine = NextActionsEngine()
        intent = BusinessIntent(question="q", products=("PayCheq",), confidence="high")
        actions = engine.generate(intent, [_rec("PayCheq")])
        learn_more = next(a for a in actions if a.action_type == "learn_more")
        assert learn_more.target == "PayCheq"


class TestNextActionsCustomSoftware:
    def test_custom_software_keyword_short_circuits_everything_else(self):
        engine = NextActionsEngine()
        intent = BusinessIntent(question="We need software built for our organisation.")
        actions = engine.generate(intent, [])
        assert len(actions) == 1
        assert actions[0].action_type == "custom_solution"

    def test_spec_exact_phrasing_is_detected(self):
        """Confirmed live gap this guards: the phase spec's own example
        question ("software built specifically for our organisation")
        didn't match the original, narrower keyword list."""
        engine = NextActionsEngine()
        intent = BusinessIntent(question="We need software built specifically for our organisation.")
        actions = engine.generate(intent, [])
        assert [a.action_type for a in actions] == ["custom_solution"]

    def test_custom_software_wins_even_with_recommendations_present(self):
        engine = NextActionsEngine()
        intent = BusinessIntent(question="I need custom software")
        actions = engine.generate(intent, [_rec("SPIDIFY")])
        assert [a.action_type for a in actions] == ["custom_solution"]


class TestNextActionsAdvisoryServices:
    def test_service_keyword_without_product_match(self):
        engine = NextActionsEngine()
        intent = BusinessIntent(question="We need cybersecurity services.")
        actions = engine.generate(intent, [])
        types = {a.action_type for a in actions}
        assert types == {"contact_sales", "talk_to_expert"}


class TestNextActionsNoSignal:
    def test_generic_question_returns_no_actions(self):
        engine = NextActionsEngine()
        intent = BusinessIntent(question="What are your office hours?")
        assert engine.generate(intent, []) == []

    def test_empty_question_returns_no_actions(self):
        engine = NextActionsEngine()
        intent = BusinessIntent(question="")
        assert engine.generate(intent, []) == []
