"""Tests for detect_action_intent — the shared detector that keeps
live-chat/escalation/appointment requests out of retrieval entirely.

Live-confirmed bug this fixes: "Can you arrange a quick chat with a
specialist?" followed by "Today 1:45pm WAT, live chat" had zero KB evidence
and fell through to a live web search, returning unrelated timezone/city
content."""

from __future__ import annotations

import pytest

from src.services.routing.action_intent import ActionIntentMatch, detect_action_intent


class TestEscalationMatches:
    @pytest.mark.parametrize(
        "question",
        [
            "Can you arrange a quick chat with a specialist?",
            "Today 1:45pm WAT, live chat",
            "I'd like to talk to a human",
            "Connect me to an agent",
            "I need technical support",
        ],
    )
    def test_matches_escalation(self, question):
        result = detect_action_intent(question)
        assert result == ActionIntentMatch("escalation")


class TestAppointmentMatches:
    @pytest.mark.parametrize(
        "question",
        [
            "I'd like to book an appointment for tomorrow",
            "Can we schedule a call?",
            "Let's set up a meeting",
        ],
    )
    def test_matches_appointment(self, question):
        result = detect_action_intent(question)
        assert result == ActionIntentMatch("appointment")


class TestDemoMatches:
    @pytest.mark.parametrize(
        "question",
        [
            "I want to book a demo",
            "Can I see a demo of SPIDIFY?",
            "I want a demo",
            "Request a demo",
        ],
    )
    def test_matches_demo(self, question):
        result = detect_action_intent(question)
        assert result == ActionIntentMatch("demo")


class TestNoMatch:
    @pytest.mark.parametrize(
        "question",
        [
            "What does SPIDIFY do?",
            "Compare PayCheq with Xpend",
            "How much does ZivaAIRA cost?",
            "Tell me about your company",
        ],
    )
    def test_ordinary_questions_do_not_match(self, question):
        assert detect_action_intent(question) is None

    def test_empty_string(self):
        assert detect_action_intent("") is None

    def test_none(self):
        assert detect_action_intent(None) is None

    def test_appointment_checked_before_escalation(self):
        # "book a call" is an appointment phrase — must not be misclassified
        # as escalation even though "call" alone could be read either way.
        result = detect_action_intent("I want to book a call with support")
        assert result == ActionIntentMatch("appointment")
