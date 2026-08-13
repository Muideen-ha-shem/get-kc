"""Tests for segment_message — deterministic clause-splitting for compound
customer messages.

Live-confirmed bug this fixes: "I want to understand SPIDIFY, compare it
with V-Login, and then book a demo." jumped straight into the demo
workflow, silently dropping the two knowledge requests that came first."""

from __future__ import annotations

from src.services.routing.message_segmentation import segment_message


class TestSplitsOnExplicitAnchor:
    def test_the_reported_example(self):
        message = "I want to understand SPIDIFY, compare it with V-Login, and then book a demo."
        assert segment_message(message) == [
            "I want to understand SPIDIFY",
            "compare it with V-Login",
            "book a demo.",
        ]

    def test_comma_then_anchor(self):
        assert segment_message("Tell me about SPIDIFY, then book a demo") == [
            "Tell me about SPIDIFY",
            "book a demo",
        ]

    def test_bare_and_then_anchor_no_comma(self):
        assert segment_message("Book a demo and then talk to a specialist") == [
            "Book a demo",
            "talk to a specialist",
        ]


class TestStaysSingleSegmentWithoutAnchor:
    def test_two_product_comparison_unaffected(self):
        assert segment_message("Compare SPIDIFY and V-Login") == ["Compare SPIDIFY and V-Login"]

    def test_appositive_commas_unaffected(self):
        message = "SPIDIFY, our identity verification product, is popular"
        assert segment_message(message) == [message]

    def test_oxford_comma_list_without_anchor_unaffected(self):
        message = "I need help with onboarding, payroll, and compliance"
        assert segment_message(message) == [message]

    def test_ordinary_question_unaffected(self):
        assert segment_message("What does SPIDIFY do?") == ["What does SPIDIFY do?"]


class TestEdgeCases:
    def test_empty_string(self):
        assert segment_message("") == [""]

    def test_none(self):
        assert segment_message(None) == [None]

    def test_anchor_with_nothing_after_it_stays_single_segment(self):
        assert segment_message("Tell me about SPIDIFY, then") == ["Tell me about SPIDIFY, then"]
