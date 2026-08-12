"""Tests for detect_confirmation — the bare yes/no detector for a pending
action confirmation. Deliberately exact-match, not substring — see the
module docstring for why "contextual" enforcement is really the caller's
job (only consulted when a pending action exists)."""

from __future__ import annotations

import pytest

from src.services.routing.confirmation_intent import detect_confirmation


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
