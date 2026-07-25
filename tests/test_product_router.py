"""Tests for ProductRouter."""

from __future__ import annotations

from src.services.routing.product_router import ProductRouter, ProductMatch


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
