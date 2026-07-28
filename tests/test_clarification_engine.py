"""Tests for ClarificationEngine."""

from __future__ import annotations

from src.services.advisory.clarification_engine import ClarificationEngine
from src.services.advisory.intent_engine import BusinessIntent


class TestClarificationEngineFires:
    def test_two_products_keyword_matched_no_theme_no_naming(self):
        engine = ClarificationEngine()
        intent = BusinessIntent(
            question="we need something for records",
            products=("AppManage", "Havis eCertify"),
            confidence="ambiguous",
            via_theme=False,
            named_explicitly=False,
        )
        question = engine.check(intent)
        assert question is not None
        assert "Software licensing" in question or "Employee training" in question


class TestClarificationEngineDoesNotFire:
    def test_business_theme_match_never_clarifies(self):
        """Phase 17's deliberate multi-product bundles must keep working —
        asking "which one?" would break "we're digitizing our company"."""
        engine = ClarificationEngine()
        intent = BusinessIntent(
            question="We are digitizing our company",
            products=("ZivaAIRA", "STAAS", "Havis Vacay", "PayCheq", "WeCare", "Havis iReport", "Havis Xpend"),
            confidence="ambiguous",
            via_theme=True,
            named_explicitly=False,
        )
        assert engine.check(intent) is None

    def test_explicit_comparison_never_clarifies(self):
        """Confirmed live bug this guards: "Compare X and Y" must not be
        turned into a clarifying question — the user already knows what
        they asked for."""
        engine = ClarificationEngine()
        intent = BusinessIntent(
            question="Compare AppManage and Havis eCertify",
            products=("AppManage", "Havis eCertify"),
            confidence="ambiguous",
            via_theme=False,
            named_explicitly=True,
        )
        assert engine.check(intent) is None

    def test_high_confidence_single_product_never_clarifies(self):
        engine = ClarificationEngine()
        intent = BusinessIntent(question="Tell me about SPIDIFY", products=("SPIDIFY",), confidence="high")
        assert engine.check(intent) is None

    def test_no_signal_never_clarifies(self):
        engine = ClarificationEngine()
        intent = BusinessIntent(question="What are your office hours?")
        assert engine.check(intent) is None

    def test_comparison_via_business_problem_language_never_clarifies(self):
        """Confirmed live bug this guards: "Compare payroll and expense
        management solutions" — one of the spec's own required
        verification questions — was incorrectly turned into a clarifying
        question, because no product is *named*, only described. The
        "compare" phrasing itself is just as deliberate as naming."""
        engine = ClarificationEngine()
        intent = BusinessIntent(
            question="Compare payroll and expense management solutions.",
            products=("Havis Xpend", "PayCheq"),
            confidence="ambiguous",
            via_theme=False,
            named_explicitly=False,
        )
        assert engine.check(intent) is None

    def test_versus_phrasing_never_clarifies(self):
        engine = ClarificationEngine()
        intent = BusinessIntent(
            question="Payroll vs expense management — which is better?",
            products=("PayCheq", "Havis Xpend"),
            confidence="ambiguous",
            via_theme=False,
            named_explicitly=False,
        )
        assert engine.check(intent) is None

    def test_more_than_two_ambiguous_products_without_theme_skips(self):
        """Rare edge case — not cleanly askable as one either/or question,
        so it falls through to normal per-product handling instead."""
        engine = ClarificationEngine()
        intent = BusinessIntent(
            question="q",
            products=("AppManage", "Havis eCertify", "KwikAlert"),
            confidence="ambiguous",
            via_theme=False,
            named_explicitly=False,
        )
        assert engine.check(intent) is None


class TestClarificationEngineQuestionText:
    def test_question_grounded_in_registry_business_problems(self):
        from src.shared.product_registry import PRODUCT_REGISTRY

        engine = ClarificationEngine()
        intent = BusinessIntent(
            question="q",
            products=("V-Login", "KwikAlert"),
            confidence="ambiguous",
            via_theme=False,
            named_explicitly=False,
        )
        question = engine.check(intent)
        assert PRODUCT_REGISTRY["V-Login"]["business_problem"] in question
        assert PRODUCT_REGISTRY["KwikAlert"]["business_problem"] in question

    def test_unregistered_product_falls_back_to_name(self):
        engine = ClarificationEngine()
        intent = BusinessIntent(
            question="q", products=("Alpha", "Beta"), confidence="ambiguous", via_theme=False, named_explicitly=False,
        )
        question = engine.check(intent)
        assert "Alpha" in question
        assert "Beta" in question
