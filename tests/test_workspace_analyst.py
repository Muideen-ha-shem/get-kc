"""Tests for workspace_analyst — "Ask HavisIQ" for Workspace Admins.

ResponseGenerator is mocked (no real LLM calls). Confirms: the real metrics
snapshot is passed as evidence (not fabricated), the FACT/ANALYSIS/
RECOMMENDATION + no-invented-numbers instructions are present in the
question sent to generate(), and workspace_id is never taken from
anywhere but the caller's own argument."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.services.admin.workspace_analyst import answer_question, daily_briefing

_FIXTURE_REPORT = {
    "conversation_count": 10,
    "escalation_count": 4,
    "resolution_rate": 0.5,
    "knowledge_gaps": None,
    "knowledge_tracking_note": "Not tracked yet.",
}


def _make_analytics_service(report=None):
    service = MagicMock()
    service.workspace_operational_report.return_value = report or _FIXTURE_REPORT
    return service


def _make_generator(answer="FACT: 4 escalations this week."):
    generator = MagicMock()
    generator.generate.return_value = {"answer": answer}
    return generator


class TestAnswerQuestion:
    def test_gathers_real_snapshot_and_scopes_to_workspace(self):
        analytics_service = _make_analytics_service()
        generator = _make_generator()

        answer_question("w1", "How did support perform?", analytics_service=analytics_service, response_generator=generator)

        analytics_service.workspace_operational_report.assert_called_once_with("w1")

    def test_snapshot_is_passed_as_evidence(self):
        analytics_service = _make_analytics_service()
        generator = _make_generator()

        answer_question("w1", "How did support perform?", analytics_service=analytics_service, response_generator=generator)

        evidence = generator.generate.call_args.kwargs["context"]
        assert len(evidence) == 1
        assert '"resolution_rate": 0.5' in evidence[0].content
        assert '"conversation_count": 10' in evidence[0].content

    def test_question_carries_fact_analysis_recommendation_instructions(self):
        analytics_service = _make_analytics_service()
        generator = _make_generator()

        answer_question("w1", "How did support perform?", analytics_service=analytics_service, response_generator=generator)

        question = generator.generate.call_args.kwargs["question"]
        assert "How did support perform?" in question
        assert "FACT" in question
        assert "ANALYSIS" in question
        assert "RECOMMENDATION" in question
        assert "never state a number that isn't present" in question.lower()
        assert "don't have that data tracked yet" in question.lower()

    def test_returns_the_generated_answer(self):
        analytics_service = _make_analytics_service()
        generator = _make_generator(answer="FACT: 4 escalations. ANALYSIS: up from 2 last week.")

        result = answer_question("w1", "How did we do?", analytics_service=analytics_service, response_generator=generator)

        assert result == {"answer": "FACT: 4 escalations. ANALYSIS: up from 2 last week."}


class TestDailyBriefing:
    def test_is_a_thin_variant_of_answer_question(self):
        analytics_service = _make_analytics_service()
        generator = _make_generator(answer="Yesterday: 184 conversations, 27 escalations.")

        result = daily_briefing("w1", analytics_service=analytics_service, response_generator=generator)

        analytics_service.workspace_operational_report.assert_called_once_with("w1")
        question = generator.generate.call_args.kwargs["question"]
        assert "operational summary" in question.lower()
        assert result == {"answer": "Yesterday: 184 conversations, 27 escalations."}
