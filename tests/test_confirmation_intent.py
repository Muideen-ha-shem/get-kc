"""Tests for detect_confirmation — the bare yes/no detector for a pending
action confirmation. Deliberately exact-match, not substring — see the
module docstring for why "contextual" enforcement is really the caller's
job (only consulted when a pending action exists)."""

from __future__ import annotations

import pytest

from src.services.routing.confirmation_intent import detect_bare_cancellation, detect_confirmation


class TestYes:
    @pytest.mark.parametrize(
        "question",
        ["yes", "Yes", "YES!", "yes please", "sure", "go ahead", "do it", "proceed", "okay", "ok", "that's fine"],
    )
    def test_matches_yes(self, question):
        assert detect_confirmation(question) == "yes"


class TestNo:
    @pytest.mark.parametrize(
        "question",
        ["no", "No.", "nope", "not now", "cancel", "never mind"],
    )
    def test_matches_no(self, question):
        assert detect_confirmation(question) == "no"


class TestBroadenedCancelPhrasing:
    """Live-confirmed bug: "cancel that" fell through to normal RAG because
    the old exact-match "cancel" never matched it."""

    @pytest.mark.parametrize(
        "question",
        ["cancel that", "actually cancel", "please cancel this", "Never mind, forget it", "nevermind that"],
    )
    def test_cancel_phrases_match_as_substring(self, question):
        assert detect_confirmation(question) == "no"


class TestNoMatch:
    @pytest.mark.parametrize(
        "question",
        [
            "yes I know SPIDIFY already",  # not a bare reply — must not match
            "What does SPIDIFY do?",
            "sure thing, tell me more",
        ],
    )
    def test_longer_sentences_do_not_match(self, question):
        assert detect_confirmation(question) is None

    def test_empty_string(self):
        assert detect_confirmation("") is None

    def test_none(self):
        assert detect_confirmation(None) is None


class TestDetectBareCancellation:
    """Live-confirmed bug: after a demo request was already submitted
    (pending action cleared), "Cancel that" fell through to RAG and
    hallucinated an unrelated "cancel your PayCheq subscription" answer."""

    @pytest.mark.parametrize(
        "question",
        ["cancel", "Cancel that", "cancel this", "actually cancel", "stop", "stop that", "never mind", "Nevermind!"],
    )
    def test_matches_bare_phrases(self, question):
        assert detect_bare_cancellation(question) is True

    @pytest.mark.parametrize(
        "question",
        [
            "How do I cancel my PayCheq subscription?",  # a real question — must reach RAG
            "What does SPIDIFY do?",
            "I'd like to cancel my appointment for tomorrow",
        ],
    )
    def test_longer_questions_do_not_match(self, question):
        assert detect_bare_cancellation(question) is False

    def test_empty_and_none(self):
        assert detect_bare_cancellation("") is False
        assert detect_bare_cancellation(None) is False
