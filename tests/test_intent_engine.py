"""Tests for BusinessIntentEngine."""

from __future__ import annotations

import pytest

from src.services.advisory.intent_engine import BusinessIntent, BusinessIntentEngine
from src.services.routing.product_router import ProductMatch, ProductRouter


class TestBusinessIntentEngineDetect:
    def test_single_product_high_confidence(self):
        engine = BusinessIntentEngine()
        intent = engine.detect("I need to automate employee attendance.")
        assert intent.products == ("STAAS",)
        assert intent.confidence == "high"
        assert intent.business_problems == (
            "Staff attendance, clock-in/out, and time tracking",
        )
        assert intent.categories == ("Workforce Attendance",)

    def test_explicit_name_still_works(self):
        engine = BusinessIntentEngine()
        intent = engine.detect("Tell me about SPIDIFY")
        assert intent.products == ("SPIDIFY",)
        assert intent.confidence == "high"
        assert intent.named_explicitly is True

    def test_business_theme_match(self):
        engine = BusinessIntentEngine()
        intent = engine.detect("We want to modernize our HR operations")
        assert intent.via_theme is True
        assert intent.primary == "ZivaAIRA"
        assert set(intent.products) == {
            "ZivaAIRA", "STAAS", "Havis Vacay", "PayCheq", "WeCare", "Havis iReport",
        }

    def test_no_signal_returns_blank_intent(self):
        engine = BusinessIntentEngine()
        intent = engine.detect("What are your office hours?")
        assert intent.products == ()
        assert intent.confidence == "none"
        assert intent.any_active() is False

    def test_blank_question_never_raises(self):
        engine = BusinessIntentEngine()
        intent = engine.detect("")
        assert intent.products == ()
        assert intent.confidence == "none"

    @pytest.mark.parametrize(
        "question,expected_product",
        [
            ("I want to secure customer onboarding.", "SPIDIFY"),
            ("We need a payroll platform.", "PayCheq"),
            ("We're looking for visitor management.", "V-Login"),
        ],
    )
    def test_spec_examples_resolve_correctly(self, question, expected_product):
        engine = BusinessIntentEngine()
        intent = engine.detect(question)
        assert intent.products == (expected_product,)


class TestBusinessIntentEngineNamedExplicitly:
    def test_explicit_comparison_is_named_explicitly(self):
        engine = BusinessIntentEngine()
        intent = engine.detect("Compare AppManage and Havis eCertify")
        assert intent.named_explicitly is True

    def test_keyword_only_match_is_not_named_explicitly(self):
        engine = BusinessIntentEngine()
        intent = engine.detect("We need a payroll platform.")
        assert intent.named_explicitly is False

    def test_theme_match_named_explicitly_reflects_question_text(self):
        engine = BusinessIntentEngine()
        # None of these theme products are named in the question text.
        intent = engine.detect("We are digitizing our company")
        assert intent.named_explicitly is False


class TestBusinessIntentEngineEnrich:
    def test_enrich_avoids_reclassifying(self):
        engine = BusinessIntentEngine()
        match = ProductMatch(products=("SPIDIFY",), confidence="high")
        intent = engine.enrich("Tell me about SPIDIFY", match)
        assert intent.products == ("SPIDIFY",)
        assert intent.business_problems == (
            "Identity verification, KYC, and secure user onboarding",
        )

    def test_enrich_handles_unregistered_product_gracefully(self):
        engine = BusinessIntentEngine()
        match = ProductMatch(products=("NotARealProduct",), confidence="high")
        intent = engine.enrich("test", match)
        assert intent.products == ("NotARealProduct",)
        assert intent.business_problems == ()
        assert intent.categories == ()

    def test_enrich_preserves_primary_and_via_theme(self):
        engine = BusinessIntentEngine()
        match = ProductMatch(
            products=("V-Login", "SPIDIFY"), confidence="ambiguous", primary="V-Login", via_theme=True,
        )
        intent = engine.enrich("We need to securely onboard visitors.", match)
        assert intent.primary == "V-Login"
        assert intent.via_theme is True


class TestBusinessIntentEngineCustomRouter:
    def test_custom_product_router_is_used(self):
        custom_router = ProductRouter(
            product_names={"Widget": ("widgetpro",)},
            product_keywords={"Widget": ("manufacturing automation",)},
        )
        engine = BusinessIntentEngine(product_router=custom_router)
        intent = engine.detect("Tell me about WidgetPro")
        assert intent.products == ("Widget",)
        # Widget isn't in PRODUCT_REGISTRY, so enrichment yields no
        # business_problem/category text — no fabricated data.
        assert intent.business_problems == ()
