"""Tests for is_self_identity_question — the shared detector used by
SourceRouter and SearchManager to prevent a "tell me about {workspace}"
question from ever reaching an unscoped web search."""

from __future__ import annotations

import pytest

from src.services.routing.self_identity import is_self_identity_question


class TestPositiveMatches:
    @pytest.mark.parametrize(
        "question",
        [
            "Tell me about Ha-Shem",
            "tell me about ha-shem",
            "What is Ha-Shem?",
            "who is Ha-Shem",
            "Ha-Shem company profile",
            "What does Ha-Shem do?",
            "Can you tell us about Ha-Shem",
            "Who runs Ha-Shem",
            "Give me some information about Ha-Shem",
        ],
    )
    def test_matches(self, question):
        assert is_self_identity_question(question, "Ha-Shem") is True


class TestNegativeMatches:
    @pytest.mark.parametrize(
        "question",
        [
            "What is Ha-Shem's pricing for STAAS?",
            "Compare Ha-Shem's STAAS to Salesforce",
            "What is the latest news about Ha-Shem partners",
            "What is the weather today",
            "How do I reset my STAAS password",
        ],
    )
    def test_does_not_match(self, question):
        assert is_self_identity_question(question, "Ha-Shem") is False

    def test_empty_question(self):
        assert is_self_identity_question("", "Ha-Shem") is False

    def test_none_question(self):
        assert is_self_identity_question(None, "Ha-Shem") is False

    def test_no_workspace_name(self):
        assert is_self_identity_question("Tell me about Ha-Shem", None) is False

    def test_blank_workspace_name(self):
        assert is_self_identity_question("Tell me about Ha-Shem", "   ") is False

    def test_word_boundary_not_substring_match(self):
        # "Ha-Shemsomething" must not satisfy the \bHa-Shem\b boundary check.
        assert is_self_identity_question("Tell me about Ha-Shemsomething", "Ha-Shem") is False

    def test_wrong_workspace_name(self):
        assert is_self_identity_question("Tell me about Ha-Shem", "Acme") is False
