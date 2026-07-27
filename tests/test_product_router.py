"""Tests for ProductRouter."""

from __future__ import annotations

import pytest

from src.services.routing.product_router import ProductRouter, ProductMatch
from src.shared.product_registry import PRODUCT_REGISTRY


# ---------------------------------------------------------------------------
# Explicit product-name mentions
# ---------------------------------------------------------------------------


class TestProductRouterExplicitNames:
    def test_spidify_named_directly(self):
        router = ProductRouter()
        match = router.classify("Tell me about SPIDIFY")
        assert match.products == ("SPIDIFY",)
        assert match.confidence == "high"

    def test_zivaaira_named_directly(self):
        router = ProductRouter()
        match = router.classify("Tell me about ZivaAIRA")
        assert match.products == ("ZivaAIRA",)
        assert match.confidence == "high"

    def test_case_insensitive(self):
        router = ProductRouter()
        assert router.classify("what is spidify?").products == ("SPIDIFY",)
        assert router.classify("WHAT IS ZIVAAIRA").products == ("ZivaAIRA",)

    def test_aira_alias_matches_zivaaira(self):
        router = ProductRouter()
        match = router.classify("How does Aira handle interviews?")
        assert match.products == ("ZivaAIRA",)

    def test_both_named_is_ambiguous(self):
        router = ProductRouter()
        match = router.classify("Compare SPIDIFY and ZivaAIRA")
        assert set(match.products) == {"SPIDIFY", "ZivaAIRA"}
        assert match.confidence == "ambiguous"

    def test_named_mention_overrides_conflicting_keywords(self):
        """Explicit naming wins even if the question also contains the
        other product's intent keywords."""
        router = ProductRouter()
        match = router.classify("Does SPIDIFY help with recruitment too?")
        assert match.products == ("SPIDIFY",)
        assert match.confidence == "high"


# ---------------------------------------------------------------------------
# Intent-keyword classification (per the spec's intent table)
# ---------------------------------------------------------------------------


class TestProductRouterIntentKeywords:
    def test_recruitment_intent_maps_to_zivaaira(self):
        router = ProductRouter()
        match = router.classify("We need recruitment software for our company")
        assert match.products == ("ZivaAIRA",)
        assert match.confidence == "high"

    def test_hiring_automation_maps_to_zivaaira(self):
        router = ProductRouter()
        match = router.classify("Looking for hiring automation tools")
        assert match.products == ("ZivaAIRA",)

    def test_talent_acquisition_maps_to_zivaaira(self):
        router = ProductRouter()
        match = router.classify("How can we improve talent acquisition?")
        assert match.products == ("ZivaAIRA",)

    def test_hr_management_maps_to_zivaaira(self):
        router = ProductRouter()
        match = router.classify("We need better HR management")
        assert match.products == ("ZivaAIRA",)

    def test_identity_verification_maps_to_spidify(self):
        router = ProductRouter()
        match = router.classify("How do we verify users securely in our app?")
        assert match.products == ("SPIDIFY",)
        assert match.confidence == "high"

    def test_kyc_maps_to_spidify(self):
        router = ProductRouter()
        match = router.classify("Do you support KYC compliance?")
        assert match.products == ("SPIDIFY",)

    def test_secure_access_maps_to_spidify(self):
        router = ProductRouter()
        match = router.classify("We need secure access for our platform")
        assert match.products == ("SPIDIFY",)

    def test_spec_example_verify_users(self):
        """Exact example from the spec."""
        router = ProductRouter()
        match = router.classify("How do we verify users securely in our app?")
        assert match.products == ("SPIDIFY",)

    def test_spec_example_recruitment_software(self):
        """Exact example from the spec."""
        router = ProductRouter()
        match = router.classify("We need recruitment software for our company")
        assert match.products == ("ZivaAIRA",)


# ---------------------------------------------------------------------------
# Ambiguous / no signal
# ---------------------------------------------------------------------------


class TestProductRouterAmbiguousOrNone:
    def test_generic_question_returns_no_product(self):
        router = ProductRouter()
        match = router.classify("What are your business hours?")
        assert match.products == ()
        assert match.confidence == "none"
        assert match.any_active() is False

    def test_empty_question_returns_no_product(self):
        router = ProductRouter()
        assert router.classify("").confidence == "none"
        assert router.classify("   ").confidence == "none"

    def test_never_raises_on_none_question(self):
        router = ProductRouter()
        match = router.classify(None)  # type: ignore[arg-type]
        assert match == ProductMatch()

    def test_any_active_true_when_product_found(self):
        router = ProductRouter()
        match = router.classify("Tell me about SPIDIFY")
        assert match.any_active() is True


# ---------------------------------------------------------------------------
# Custom configuration
# ---------------------------------------------------------------------------


class TestProductRouterCustomConfig:
    def test_custom_product_names_and_keywords(self):
        router = ProductRouter(
            product_names={"Widget": ("widgetpro",)},
            product_keywords={"Widget": ("manufacturing automation",)},
        )
        assert router.classify("Tell me about WidgetPro").products == ("Widget",)
        assert router.classify("We need manufacturing automation").products == ("Widget",)
        # Defaults are fully replaced, not merged
        assert router.classify("Tell me about SPIDIFY").confidence == "none"


# ---------------------------------------------------------------------------
# Phase 16 — HAVIS-360 catalog expansion. These are the exact phrases from
# the spec's "Success Criteria" section: every one must resolve to exactly
# one product at "high" confidence with zero code changes beyond the
# PRODUCT_REGISTRY entries (this is the whole point of deriving
# ProductRouter's defaults from the registry).
# ---------------------------------------------------------------------------


class TestProductRouterHavis360SuccessCriteria:
    @pytest.mark.parametrize(
        "question,expected_product",
        [
            ("What solution manages payroll?", "PayCheq"),
            ("I need visitor management.", "V-Login"),
            ("What helps with employee leave?", "Havis Vacay"),
            ("We need software licensing.", "AppManage"),
            ("We want AI recruitment.", "ZivaAIRA"),
            ("We need identity verification.", "SPIDIFY"),
            ("We need attendance tracking.", "STAAS"),
            ("Our employees submit paper receipts.", "Havis REMA"),
            ("We need company-wide emergency alerts.", "KwikAlert"),
            ("I need employee reporting.", "Havis iReport"),
            ("We want internal certification.", "Havis eCertify"),
            ("I need customer support ticket management.", "WeCare"),
        ],
    )
    def test_success_criteria_phrase_resolves_correctly(self, question, expected_product):
        router = ProductRouter()
        match = router.classify(question)
        assert match.products == (expected_product,), (
            f"{question!r} -> {match.products} (confidence={match.confidence}), "
            f"expected ({expected_product!r},)"
        )
        assert match.confidence == "high"

    @pytest.mark.parametrize(
        "question,expected_product",
        [
            ("What can help us manage attendance?", "STAAS"),
            ("What handles payroll?", "PayCheq"),
            ("I need expense approvals.", "Havis Xpend"),
            ("I need visitor check-in.", "V-Login"),
            ("What product manages leave?", "Havis Vacay"),
            ("What solution helps employee certification?", "Havis eCertify"),
            ("What should we use for emergency notifications?", "KwikAlert"),
        ],
    )
    def test_additional_business_problem_phrasings(self, question, expected_product):
        router = ProductRouter()
        match = router.classify(question)
        assert match.products == (expected_product,)


class TestProductRouterHavis360ExplicitNames:
    @pytest.mark.parametrize(
        "question,expected_product",
        [
            ("Tell me about V-Login", "V-Login"),
            ("What is STAAS?", "STAAS"),
            ("How does WeCare work?", "WeCare"),
            ("Tell me about Havis Xpend", "Havis Xpend"),
            ("What is Havis Vacay?", "Havis Vacay"),
            ("Tell me about Havis iReport", "Havis iReport"),
            ("What is Havis REMA?", "Havis REMA"),
            ("Tell me about Havis eCertify", "Havis eCertify"),
            ("What is KwikAlert?", "KwikAlert"),
            ("Tell me about AppManage", "AppManage"),
            ("What is PayCheq?", "PayCheq"),
        ],
    )
    def test_explicit_name_resolves_at_high_confidence(self, question, expected_product):
        router = ProductRouter()
        match = router.classify(question)
        assert match.products == (expected_product,)
        assert match.confidence == "high"


class TestProductRouterHavis360Comparisons:
    def test_comparing_two_new_products_is_ambiguous_and_scopes_both(self):
        router = ProductRouter()
        match = router.classify("Compare STAAS and WeCare")
        assert set(match.products) == {"STAAS", "WeCare"}
        assert match.confidence == "ambiguous"

    def test_comparing_new_product_with_existing_product(self):
        router = ProductRouter()
        match = router.classify("Compare PayCheq and ZivaAIRA")
        assert set(match.products) == {"PayCheq", "ZivaAIRA"}
        assert match.confidence == "ambiguous"


class TestProductRegistryConsistency:
    """Guards the scalability claim: adding product #12 means adding one
    PRODUCT_REGISTRY entry, nothing else. These tests fail loudly if a
    future entry accidentally collides with an existing one."""

    def test_registry_has_thirteen_products(self):
        assert len(PRODUCT_REGISTRY) == 13

    def test_no_alias_is_shared_across_products(self):
        seen: dict[str, str] = {}
        for product, info in PRODUCT_REGISTRY.items():
            for alias in info["aliases"]:
                assert alias not in seen, (
                    f"alias {alias!r} used by both {seen.get(alias)!r} and {product!r}"
                )
                seen[alias] = product

    def test_no_keyword_is_shared_across_products(self):
        seen: dict[str, str] = {}
        for product, info in PRODUCT_REGISTRY.items():
            for keyword in info["keywords"]:
                assert keyword not in seen, (
                    f"keyword {keyword!r} used by both {seen.get(keyword)!r} and {product!r}"
                )
                seen[keyword] = product

    def test_every_product_router_default_traces_back_to_registry(self):
        """ProductRouter's no-arg defaults must be exactly derived from the
        registry — no separate hand-maintained list drifting out of sync."""
        router = ProductRouter()
        for product in PRODUCT_REGISTRY:
            assert product in router._product_names
            assert product in router._product_keywords
