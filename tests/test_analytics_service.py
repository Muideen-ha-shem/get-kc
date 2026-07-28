"""Tests for AnalyticsService."""

from __future__ import annotations

from src.services.advisory.analytics_service import AnalyticsService, record_safely


class TestAnalyticsServiceRecording:
    def test_record_and_query_recommendations(self):
        svc = AnalyticsService()
        svc.record_recommendation("SPIDIFY")
        svc.record_recommendation("SPIDIFY")
        svc.record_recommendation("ZivaAIRA")
        assert svc.top_recommended() == [("SPIDIFY", 2), ("ZivaAIRA", 1)]

    def test_record_accepted_recommendation(self):
        svc = AnalyticsService()
        svc.record_accepted_recommendation("SPIDIFY")
        assert svc.snapshot()["top_accepted"] == [("SPIDIFY", 1)]

    def test_record_business_problem(self):
        svc = AnalyticsService()
        svc.record_business_problem("Identity Verification")
        svc.record_business_problem("Identity Verification")
        assert svc.top_business_problems() == [("Identity Verification", 2)]

    def test_record_comparison_sorted_and_deduped_pair(self):
        svc = AnalyticsService()
        svc.record_comparison(["ZivaAIRA", "SPIDIFY"])
        svc.record_comparison(["SPIDIFY", "ZivaAIRA"])  # same pair, different order
        assert svc.top_compared() == [(("SPIDIFY", "ZivaAIRA"), 2)]

    def test_record_comparison_requires_two_products(self):
        svc = AnalyticsService()
        svc.record_comparison(["SPIDIFY"])
        assert svc.top_compared() == []

    def test_demo_cta_count_per_product_and_total(self):
        svc = AnalyticsService()
        svc.record_demo_cta("SPIDIFY")
        svc.record_demo_cta("SPIDIFY")
        svc.record_demo_cta("ZivaAIRA")
        assert svc.demo_cta_count("SPIDIFY") == 2
        assert svc.demo_cta_count("ZivaAIRA") == 1
        assert svc.demo_cta_count() == 3
        assert svc.demo_cta_count("Unknown") == 0

    def test_custom_software_request_count(self):
        svc = AnalyticsService()
        svc.record_custom_software_request()
        svc.record_custom_software_request()
        assert svc.custom_software_request_count() == 2

    def test_top_n_limits_results(self):
        svc = AnalyticsService()
        for product in ["A", "B", "C"]:
            svc.record_recommendation(product)
        assert len(svc.top_recommended(n=2)) == 2

    def test_snapshot_includes_every_metric(self):
        svc = AnalyticsService()
        svc.record_recommendation("SPIDIFY")
        svc.record_custom_software_request()
        snapshot = svc.snapshot()
        assert "top_recommended" in snapshot
        assert "top_accepted" in snapshot
        assert "top_business_problems" in snapshot
        assert "top_compared" in snapshot
        assert "demo_ctas" in snapshot
        assert snapshot["custom_software_requests"] == 1


class TestRecordSafely:
    def test_none_analytics_is_a_no_op(self):
        record_safely(None, "record_recommendation", "SPIDIFY")  # must not raise

    def test_calls_through_to_real_method(self):
        svc = AnalyticsService()
        record_safely(svc, "record_recommendation", "SPIDIFY")
        assert svc.top_recommended() == [("SPIDIFY", 1)]

    def test_swallows_exceptions_from_the_method(self):
        class Broken:
            def record_recommendation(self, product):
                raise RuntimeError("boom")

        record_safely(Broken(), "record_recommendation", "SPIDIFY")  # must not raise

    def test_swallows_missing_method(self):
        svc = AnalyticsService()
        record_safely(svc, "not_a_real_method", "x")  # must not raise
