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


class TestDeicticSelfReference:
    """Live-confirmed bug: "Tell me the core values of this company" (no
    workspace name mentioned) must be recognized as a self-identity
    question regardless of whether workspace_name is known."""

    @pytest.mark.parametrize(
        "question",
        [
            "Tell me the core values of this company",
            "Who runs this platform?",
            "What is that organization about?",
            "Tell me about this organisation",
            "What does this business do?",
            "Tell me about the company",
            "How does the platform work?",
            "What is your company's mission?",
            "Does your platform support SSO?",
            "Who are you guys?",
        ],
    )
    def test_matches_without_workspace_name(self, question):
        assert is_self_identity_question(question, None) is True

    @pytest.mark.parametrize(
        "question",
        [
            "Tell me the core values of this company",
            "Who runs this platform?",
        ],
    )
    def test_matches_with_workspace_name_too(self, question):
        assert is_self_identity_question(question, "Ha-Shem") is True

    def test_deictic_match_is_case_insensitive(self):
        assert is_self_identity_question("TELL ME ABOUT THIS COMPANY", None) is True
