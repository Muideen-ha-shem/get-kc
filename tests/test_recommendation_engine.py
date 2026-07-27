"""Tests for RecommendationEngine."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.services.advisory.intent_engine import BusinessIntent
from src.services.advisory.recommendation_engine import RecommendationEngine


def _evidence(url: str):
    return SimpleNamespace(url=url)


def _resolver_for(product_by_url: dict[str, str]):
    """A fake product_metadata_resolver — mirrors product_metadata_for_url's
    ``{"product": ..., "category": ..., "source_type": ...}`` shape."""

    def resolve(url: str) -> dict[str, str | None]:
        product = product_by_url.get(url)
        return {"product": product, "category": None, "source_type": "official_product" if product else None}

    return resolve


class TestRecommendationEngineNoIntent:
    def test_no_products_returns_empty_list(self):
        engine = RecommendationEngine(product_metadata_resolver=_resolver_for({}))
        intent = BusinessIntent(question="What are your office hours?")
        assert engine.recommend(intent, []) == []


class TestRecommendationEngineSingleProduct:
    def test_high_confidence_grounded_is_high(self):
        engine = RecommendationEngine(
            product_metadata_resolver=_resolver_for({"https://havisspidify.com/": "SPIDIFY"})
        )
        intent = BusinessIntent(
            question="Tell me about SPIDIFY", products=("SPIDIFY",), confidence="high", named_explicitly=True,
        )
        recs = engine.recommend(intent, [_evidence("https://havisspidify.com/")])
        assert len(recs) == 1
        assert recs[0].product == "SPIDIFY"
        assert recs[0].confidence == "high"
        assert recs[0].grounded is True
        assert "SPIDIFY" in recs[0].reason
        assert recs[0].alternatives == ()
        assert recs[0].related == ()

    def test_high_confidence_ungrounded_is_downgraded(self):
        """No evidence actually contains SPIDIFY content -> never claim
        high confidence even though the name/keyword match was clear."""
        engine = RecommendationEngine(product_metadata_resolver=_resolver_for({}))
        intent = BusinessIntent(question="Tell me about SPIDIFY", products=("SPIDIFY",), confidence="high")
        recs = engine.recommend(intent, [])
        assert recs[0].confidence == "medium"
        assert recs[0].grounded is False

    def test_reason_and_benefit_come_from_registry_text(self):
        engine = RecommendationEngine(product_metadata_resolver=_resolver_for({}))
        intent = BusinessIntent(question="q", products=("PayCheq",), confidence="high")
        recs = engine.recommend(intent, [])
        from src.shared.product_registry import PRODUCT_REGISTRY

        assert PRODUCT_REGISTRY["PayCheq"]["business_problem"] in recs[0].reason
        assert recs[0].primary_benefit == PRODUCT_REGISTRY["PayCheq"]["business_problem"]

    def test_never_recommends_unregistered_product(self):
        engine = RecommendationEngine(product_metadata_resolver=_resolver_for({}))
        intent = BusinessIntent(question="q", products=("NotReal",), confidence="high")
        assert engine.recommend(intent, []) == []


class TestRecommendationEngineAmbiguousNonTheme:
    def test_two_products_no_theme_yields_alternatives(self):
        engine = RecommendationEngine(product_metadata_resolver=_resolver_for({}))
        intent = BusinessIntent(
            question="Compare AppManage and Havis eCertify",
            products=("AppManage", "Havis eCertify"),
            confidence="ambiguous",
            named_explicitly=True,
        )
        recs = engine.recommend(intent, [])
        by_product = {r.product: r for r in recs}
        assert by_product["AppManage"].alternatives == ("Havis eCertify",)
        assert by_product["Havis eCertify"].alternatives == ("AppManage",)
        # Not a theme match — these are competing options, not complements.
        assert by_product["AppManage"].related == ()

    def test_ambiguous_ungrounded_confidence_is_low(self):
        engine = RecommendationEngine(product_metadata_resolver=_resolver_for({}))
        intent = BusinessIntent(
            question="q", products=("AppManage", "Havis eCertify"), confidence="ambiguous",
        )
        recs = engine.recommend(intent, [])
        assert all(r.confidence == "low" for r in recs)


class TestRecommendationEngineBusinessTheme:
    def test_primary_gets_related_complements_not_alternatives(self):
        engine = RecommendationEngine(
            product_metadata_resolver=_resolver_for({"https://aira.havis360.com/": "ZivaAIRA"})
        )
        intent = BusinessIntent(
            question="We want to modernize our HR operations",
            products=("ZivaAIRA", "STAAS", "Havis Vacay", "PayCheq", "WeCare", "Havis iReport"),
            confidence="ambiguous",
            primary="ZivaAIRA",
            via_theme=True,
        )
        recs = engine.recommend(intent, [_evidence("https://aira.havis360.com/")])

        assert recs[0].product == "ZivaAIRA"
        assert recs[0].confidence == "high"  # primary + grounded
        assert recs[0].alternatives == ()
        assert set(recs[0].related) == {"STAAS", "Havis Vacay", "PayCheq", "WeCare", "Havis iReport"}

        staas_rec = next(r for r in recs if r.product == "STAAS")
        assert staas_rec.confidence in ("medium", "low")  # not primary, not grounded here
        assert staas_rec.alternatives == ()

    def test_no_single_primary_all_medium_or_low(self):
        engine = RecommendationEngine(product_metadata_resolver=_resolver_for({}))
        intent = BusinessIntent(
            question="We are digitizing our company",
            products=("ZivaAIRA", "STAAS", "Havis Vacay", "PayCheq", "WeCare", "Havis iReport", "Havis Xpend"),
            confidence="ambiguous",
            primary=None,
            via_theme=True,
        )
        recs = engine.recommend(intent, [])
        assert all(r.confidence in ("medium", "low") for r in recs)
        assert all(r.confidence != "high" for r in recs)

    def test_ordering_puts_primary_first(self):
        engine = RecommendationEngine(product_metadata_resolver=_resolver_for({}))
        intent = BusinessIntent(
            question="q",
            products=("STAAS", "ZivaAIRA", "PayCheq"),
            confidence="ambiguous",
            primary="ZivaAIRA",
            via_theme=True,
        )
        recs = engine.recommend(intent, [])
        assert recs[0].product == "ZivaAIRA"


class TestRecommendationEngineErrorHandling:
    def test_resolver_failure_does_not_raise(self):
        def broken_resolver(url):
            raise RuntimeError("boom")

        engine = RecommendationEngine(product_metadata_resolver=broken_resolver)
        intent = BusinessIntent(question="q", products=("SPIDIFY",), confidence="high")
        recs = engine.recommend(intent, [_evidence("https://havisspidify.com/")])
        assert recs[0].grounded is False

    def test_default_resolver_is_real_product_metadata_for_url(self):
        """No resolver injected -> uses the real
        scripts.product_metadata.product_metadata_for_url, proving the
        default wiring works end-to-end without a mock."""
        engine = RecommendationEngine()
        intent = BusinessIntent(question="q", products=("SPIDIFY",), confidence="high")
        recs = engine.recommend(intent, [_evidence("https://havisspidify.com/features")])
        assert recs[0].grounded is True
