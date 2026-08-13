"""Keyword-coverage tests for the escalation intent classifiers."""

from __future__ import annotations

from src.services.escalation.intent import (
    detect_critical_intent,
    detect_human_request,
    detect_sentiment_hint,
)


class TestDetectHumanRequest:
    def test_positive_examples(self):
        examples = [
            "I want to speak to support",
            "Talk to a human",
            "Connect me to an agent",
            "Can someone call me?",
            "I need technical support",
            "I'd like to speak with Sales",
        ]
        for example in examples:
            assert detect_human_request(example) is True, example

    def test_negative_example(self):
        assert detect_human_request("What does SPIDIFY cost?") is False

    def test_live_confirmed_action_hallucination_transcript(self):
        """Live-confirmed bug: neither turn of this real transcript matched
        any keyword before this fix, so nothing flagged it as a human-
        request at all — it fell straight through to retrieval and a web
        search instead."""
        assert detect_human_request("Can you arrange a quick chat with a specialist?") is True
        assert detect_human_request("Today 1:45pm WAT, live chat") is True

    def test_no_collision_with_product_catalog(self):
        """None of the new keywords ("specialist", "live chat", "quick
        chat", "arrange a chat/call") should false-positive on an ordinary
        product question — confirmed no product in the catalog is named or
        described using any of these phrases."""
        assert detect_human_request("What does SPIDIFY cost?") is False
        assert detect_human_request("Compare PayCheq with Xpend") is False


class TestDetectCriticalIntent:
    def test_billing(self):
        assert detect_critical_intent("I was overcharged this month") == "billing"

    def test_security_incident(self):
        assert detect_critical_intent("Our account was hacked") == "security_incident"

    def test_no_match(self):
        assert detect_critical_intent("What does SPIDIFY cost?") is None


class TestDetectSentimentHint:
    def test_frustrated(self):
        assert detect_sentiment_hint("This is ridiculous, nothing works!!!") == "frustrated"

    def test_neutral(self):
        assert detect_sentiment_hint("What does SPIDIFY cost?") == "neutral"
