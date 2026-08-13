"""Tests for EscalationService.generate_resolution_summary — the AI-drafted
resolution summary shown to the agent on Resolve, before Close.

Reuses ResponseGenerator (mocked here, no real LLM calls) — not a second
generation system. Must never raise: a summary failure is always best-effort,
never allowed to block the Resolve action that calls it."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.services.escalation.escalation_repository import EscalationRepository
from src.services.escalation.escalation_service import EscalationService


def _message(sender_type: str, content: str):
    return MagicMock(sender_type=sender_type, content=content)


class TestGenerateResolutionSummary:
    def test_returns_none_when_no_messages(self):
        repo = MagicMock(spec=EscalationRepository)
        repo.list_messages.return_value = []
        service = EscalationService(repository=repo)

        assert service.generate_resolution_summary("e1") is None

    def test_grounds_the_prompt_in_the_real_transcript(self):
        repo = MagicMock(spec=EscalationRepository)
        repo.list_messages.return_value = [
            _message("customer", "I can't access V-Login"),
            _message("agent", "Reset your password and try again"),
            _message("customer", "That worked, thanks!"),
        ]
        service = EscalationService(repository=repo)

        generator = MagicMock()
        generator.generate.return_value = {"answer": "Customer had a V-Login access issue, resolved via password reset."}

        result = service.generate_resolution_summary("e1", response_generator=generator)

        assert result == "Customer had a V-Login access issue, resolved via password reset."
        call_kwargs = generator.generate.call_args.kwargs
        evidence = call_kwargs["context"]
        assert len(evidence) == 1
        assert "V-Login" in evidence[0].content
        assert "Reset your password" in evidence[0].content
        assert "never invent" in call_kwargs["question"].lower()

    def test_never_raises_on_repository_failure(self):
        repo = MagicMock(spec=EscalationRepository)
        repo.list_messages.side_effect = RuntimeError("db down")
        service = EscalationService(repository=repo)

        assert service.generate_resolution_summary("e1") is None

    def test_never_raises_on_generation_failure(self):
        repo = MagicMock(spec=EscalationRepository)
        repo.list_messages.return_value = [_message("customer", "help")]
        service = EscalationService(repository=repo)

        generator = MagicMock()
        generator.generate.side_effect = RuntimeError("LLM down")

        assert service.generate_resolution_summary("e1", response_generator=generator) is None

    def test_empty_llm_answer_returns_none_not_empty_string(self):
        repo = MagicMock(spec=EscalationRepository)
        repo.list_messages.return_value = [_message("customer", "help")]
        service = EscalationService(repository=repo)

        generator = MagicMock()
        generator.generate.return_value = {"answer": ""}

        assert service.generate_resolution_summary("e1", response_generator=generator) is None
