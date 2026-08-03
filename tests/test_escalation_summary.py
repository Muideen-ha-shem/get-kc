"""Tests for build_summary — given a fake AdvisoryResult, asserts the exact shape."""

from __future__ import annotations

from src.services.advisory.advisory_layer import AdvisoryResult
from src.services.advisory.intent_engine import BusinessIntent
from src.services.advisory.next_actions import NextAction
from src.services.advisory.recommendation_engine import Recommendation
from src.services.escalation.summary import build_summary


def _advisory() -> AdvisoryResult:
    intent = BusinessIntent(
        question="How do I verify identity?",
        products=("SPIDIFY",),
        confidence="high",
        categories=("Identity Verification",),
    )
    return AdvisoryResult(
        intent=intent,
        recommendations=[
            Recommendation(
                product="SPIDIFY", confidence="high", reason="Identity verification made simple.",
                primary_benefit="Faster onboarding.", alternatives=[], related=[],
            )
        ],
        next_actions=[NextAction(label="Book a demo", action_type="demo_request")],
    )


class TestBuildSummary:
    def test_shape_with_advisory(self):
        summary = build_summary(
            workspace_name="Ha-Shem",
            customer_company="ABC Bank",
            advisory=_advisory(),
            question="Unable to complete identity verification.",
            sentiment="frustrated",
        )

        assert summary == {
            "customer": "ABC Bank",
            "workspace": "Ha-Shem",
            "intent": ["Identity Verification"],
            "sentiment": "frustrated",
            "products": ["SPIDIFY"],
            "problem": "Unable to complete identity verification.",
            "actions_already_taken": [{"label": "Book a demo", "action_type": "demo_request"}],
            "suggested_resolution": [{"product": "SPIDIFY", "reason": "Identity verification made simple."}],
        }

    def test_defaults_without_advisory(self):
        summary = build_summary(
            workspace_name="Ha-Shem", customer_company=None, advisory=None,
            question="What is SPIDIFY?", sentiment="neutral",
        )

        assert summary["customer"] == "Unknown"
        assert summary["intent"] == []
        assert summary["products"] == []
        assert summary["actions_already_taken"] == []
        assert summary["suggested_resolution"] == []
