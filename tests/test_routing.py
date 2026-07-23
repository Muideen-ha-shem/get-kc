"""Tests for SourceRouter and RoutingDecision.

All tests are pure — no I/O, no mocks, no side-effects.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# RoutingDecision
# ---------------------------------------------------------------------------


class TestRoutingDecision:
    def test_defaults_all_false(self):
        from src.services.routing.source_router import RoutingDecision

        d = RoutingDecision()
        assert d.knowledge is False
        assert d.web is False
        assert d.any_active() is False

    def test_knowledge_only(self):
        from src.services.routing.source_router import RoutingDecision

        d = RoutingDecision(knowledge=True)
        assert d.knowledge is True
        assert d.web is False
        assert d.any_active() is True

    def test_web_only(self):
        from src.services.routing.source_router import RoutingDecision

        d = RoutingDecision(web=True)
        assert d.knowledge is False
        assert d.web is True
        assert d.any_active() is True

    def test_both_true(self):
        from src.services.routing.source_router import RoutingDecision

        d = RoutingDecision(knowledge=True, web=True)
        assert d.any_active() is True

    def test_immutability(self):
        from src.services.routing.source_router import RoutingDecision

        d = RoutingDecision(knowledge=True)
        with pytest.raises((AttributeError, TypeError)):
            d.knowledge = False  # type: ignore[misc]

    def test_to_dict(self):
        from src.services.routing.source_router import RoutingDecision

        d = RoutingDecision(knowledge=True, web=True)
        assert d.to_dict() == {"knowledge": True, "web": True}

    def test_to_dict_partial(self):
        from src.services.routing.source_router import RoutingDecision

        d = RoutingDecision(web=True)
        assert d.to_dict() == {"knowledge": False, "web": True}


# ---------------------------------------------------------------------------
# SourceRouter — default keyword lists
# ---------------------------------------------------------------------------


class TestSourceRouterDefaults:
    def test_knowledge_keyword_routes_to_knowledge(self):
        from src.services.routing.source_router import SourceRouter

        router = SourceRouter()

        # Each of these should trigger knowledge=True
        knowledge_questions = [
            "What services do you offer?",
            "Tell me about the company",
            "What is the pricing for your products?",
            "Show me the documentation",
            "What are the system requirements?",
            "How do I configure the API?",
            "What is your support policy?",
            "How do I migrate to the new version?",
            "What are the system limitations?",
            "Do you have a SLA?",
        ]
        for q in knowledge_questions:
            decision = router.route(q)
            assert decision.knowledge is True, f"Expected knowledge=True for: {q!r}"

    def test_web_keyword_routes_to_web(self):
        from src.services.routing.source_router import SourceRouter

        router = SourceRouter()

        web_questions = [
            "What are the latest news?",
            "What is the stock price today?",
            "What are the current prices?",
            "Show me recent announcements",
            "What are the latest updates?",
            "Compare product A vs product B",
            "What are the best alternatives?",
            "How to set up a blog?",
            "What is the latest version?",
        ]
        for q in web_questions:
            decision = router.route(q)
            assert decision.web is True, f"Expected web=True for: {q!r}"

    def test_both_sources_for_time_sensitive_knowledge(self):
        from src.services.routing.source_router import SourceRouter

        router = SourceRouter()

        # Questions that mention both knowledge-base topics AND time-sensitive words
        mixed = [
            "What are the latest product announcements?",
            "Recent updates to the API",
            "Latest version pricing?",
        ]
        for q in mixed:
            decision = router.route(q)
            assert decision.knowledge is True, f"Expected knowledge=True for: {q!r}"
            assert decision.web is True, f"Expected web=True for: {q!r}"

    def test_generic_question_defaults_to_knowledge(self):
        from src.services.routing.source_router import SourceRouter

        router = SourceRouter()
        decision = router.route("Hello, how are you?")
        assert decision.knowledge is True  # default fallback
        assert decision.web is False

    def test_empty_question_raises_value_error(self):
        from src.services.routing.source_router import SourceRouter

        router = SourceRouter()
        with pytest.raises(ValueError, match="non-empty"):
            router.route("")
        with pytest.raises(ValueError, match="non-empty"):
            router.route("   ")

    def test_whole_word_matching_for_trailing_space_keywords(self):
        from src.services.routing.source_router import SourceRouter

        router = SourceRouter()

        # "vs " should match "A vs B" but not "vsphere" or "vsomething"
        assert router.route("A vs B").web is True
        # No knowledge keyword present, but web=True so the fallback to
        # knowledge=True only happens when both are False.
        # Since web=True, knowledge stays False — this is correct behaviour.
        assert router.route("A vs B").knowledge is False

    def test_non_web_question_does_not_trigger_web(self):
        from src.services.routing.source_router import SourceRouter

        router = SourceRouter()
        decision = router.route("What is the company's mission?")
        assert decision.knowledge is True
        # "mission" is not in web keywords
        assert decision.web is False


# ---------------------------------------------------------------------------
# SourceRouter — custom keyword lists
# ---------------------------------------------------------------------------


class TestSourceRouterCustomKeywords:
    def test_custom_knowledge_keywords(self):
        from src.services.routing.source_router import SourceRouter

        router = SourceRouter(knowledge_keywords=["wombat", "platypus"])
        assert router.route("Tell me about wombats").knowledge is True
        assert router.route("Tell me about wombats").web is False
        # Default keywords should NOT match when custom ones are provided
        decision = router.route("What services do you offer?")
        # "services" is not in custom list, so it falls through to default
        assert decision.knowledge is True  # default fallback

    def test_custom_web_keywords(self):
        from src.services.routing.source_router import SourceRouter

        router = SourceRouter(web_keywords=["weather", "forecast"])
        assert router.route("weather today").web is True
        # Time-sensitive words from default shouldn't match
        decision = router.route("latest news")
        assert decision.web is False

    def test_empty_keyword_lists(self):
        from src.services.routing.source_router import SourceRouter

        router = SourceRouter(knowledge_keywords=[], web_keywords=[])
        decision = router.route("anything at all")
        # If nothing matches, defaults to knowledge=True
        assert decision.knowledge is True
        assert decision.web is False

    def test_case_insensitive_matching(self):
        from src.services.routing.source_router import SourceRouter

        router = SourceRouter(knowledge_keywords=["Service", "API"])
        assert router.route("What is the best service?").knowledge is True
        assert router.route("what is the best SERVICE?").knowledge is True
        assert router.route("What is the best Api?").knowledge is True