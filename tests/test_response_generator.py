"""Tests for ResponseGenerator.

All LLM calls are mocked — no real API calls are made.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_evidence(content="Test content", score=0.9, title="", url="", source_type="knowledge_base"):
    """Build an EvidenceItem for testing."""
    from src.services.merger.context_merger import EvidenceItem
    return EvidenceItem(content=content, score=score, title=title, url=url, source_type=source_type)


# ---------------------------------------------------------------------------
# ResponseGenerator — construction
# ---------------------------------------------------------------------------


class TestResponseGeneratorConstruction:
    def test_default_construction(self):
        from src.services.generator.response_generator import ResponseGenerator

        gen = ResponseGenerator(api_key="test-key")
        assert gen._model == "openai/gpt-oss-120b"
        assert gen._temperature == pytest.approx(0.1)
        assert gen._max_tokens == 1024

    def test_custom_model(self):
        from src.services.generator.response_generator import ResponseGenerator

        gen = ResponseGenerator(model="llama3-8b-8192", temperature=0.5, max_tokens=512, api_key="test-key")
        assert gen._model == "llama3-8b-8192"
        assert gen._temperature == pytest.approx(0.5)
        assert gen._max_tokens == 512

    def test_no_api_key_logs_warning(self):
        from src.services.generator.response_generator import ResponseGenerator

        with patch.dict("os.environ", {}, clear=True):
            gen = ResponseGenerator(api_key=None)
            assert gen._api_key is None


# ---------------------------------------------------------------------------
# ResponseGenerator — generate with mocked LLM
# ---------------------------------------------------------------------------


class TestResponseGeneratorGenerate:
    def test_generate_with_evidence(self):
        from src.services.generator.response_generator import ResponseGenerator

        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "Ha-Shem offers cloud services [1]."

        with patch("groq.Groq") as mock_groq:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_groq.return_value = mock_client

            gen = ResponseGenerator(api_key="test-key")
            result = gen.generate(
                question="What does Ha-Shem offer?",
                context=[
                    _make_evidence(content="Ha-Shem offers cloud services.", title="About Us", url="https://ha-shem.com/about"),
                ],
            )

        assert result["answer"] == "Ha-Shem offers cloud services [1]."
        assert len(result["citations"]) == 1
        assert result["citations"][0]["url"] == "https://ha-shem.com/about"
        assert result["citations"][0]["title"] == "About Us"

    def test_generate_multiple_evidence_items(self):
        from src.services.generator.response_generator import ResponseGenerator

        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "Services: cloud [1] and AI [2]."

        with patch("groq.Groq") as mock_groq:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_groq.return_value = mock_client

            gen = ResponseGenerator(api_key="test-key")
            result = gen.generate(
                question="List services",
                context=[
                    _make_evidence(content="Cloud services available.", url="https://example.com/cloud"),
                    _make_evidence(content="AI platform available.", url="https://example.com/ai"),
                ],
            )

        assert result["answer"] == "Services: cloud [1] and AI [2]."
        assert len(result["citations"]) == 2

    def test_generate_empty_context(self):
        from src.services.generator.response_generator import ResponseGenerator

        gen = ResponseGenerator(api_key="test-key")
        result = gen.generate(question="Anything?", context=[])

        assert "don't have enough information" in result["answer"]
        assert result["citations"] == []

    def test_generate_none_context(self):
        from src.services.generator.response_generator import ResponseGenerator

        gen = ResponseGenerator(api_key="test-key")
        result = gen.generate(question="Anything?", context=None)

        assert "don't have enough information" in result["answer"]

    def test_empty_question_raises_error(self):
        from src.services.generator.response_generator import ResponseGenerator

        gen = ResponseGenerator(api_key="test-key")
        with pytest.raises(ValueError, match="non-empty"):
            gen.generate(question="", context=[_make_evidence()])

    def test_no_api_key_raises_error(self):
        from src.services.generator.response_generator import ResponseGenerator

        # Create generator without api_key and ensure GROQ_API_KEY env var is absent
        with patch.dict("os.environ", {}, clear=True):
            gen = ResponseGenerator(api_key=None)
            with pytest.raises(ValueError, match="GROQ_API_KEY"):
                gen.generate(question="test", context=[_make_evidence()])

    def test_llm_failure_graceful_fallback(self):
        from src.services.generator.response_generator import ResponseGenerator

        with patch("groq.Groq") as mock_groq:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = RuntimeError("API unavailable")
            mock_groq.return_value = mock_client

            gen = ResponseGenerator(api_key="test-key")
            result = gen.generate(
                question="test",
                context=[_make_evidence(content="Some data", url="https://example.com")],
            )

        assert "encountered an error" in result["answer"]
        # Citations should still be returned even though LLM failed
        assert len(result["citations"]) == 1

    def test_llm_returns_empty_string(self):
        from src.services.generator.response_generator import ResponseGenerator

        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = ""

        with patch("groq.Groq") as mock_groq:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_groq.return_value = mock_client

            gen = ResponseGenerator(api_key="test-key")
            result = gen.generate(
                question="test",
                context=[_make_evidence()],
            )

        assert "couldn't generate" in result["answer"]


# ---------------------------------------------------------------------------
# ResponseGenerator — evidence formatting
# ---------------------------------------------------------------------------


class TestResponseGeneratorFormatting:
    def test_format_evidence_empty(self):
        from src.services.generator.response_generator import ResponseGenerator

        block, citations = ResponseGenerator._format_evidence([])
        assert block == ""
        assert citations == []

    def test_format_evidence_single(self):
        from src.services.generator.response_generator import ResponseGenerator

        item = _make_evidence(content="Hello world", url="https://example.com", title="Test Title")
        block, citations = ResponseGenerator._format_evidence([item])

        assert "[1]" in block
        assert "Hello world" in block
        assert "https://example.com" in block
        assert "Test Title" in block
        assert len(citations) == 1
        assert citations[0]["url"] == "https://example.com"

    def test_format_evidence_multiple(self):
        from src.services.generator.response_generator import ResponseGenerator

        items = [
            _make_evidence(content="First", url="https://a.com"),
            _make_evidence(content="Second", url="https://b.com"),
        ]
        block, citations = ResponseGenerator._format_evidence(items)

        assert "[1]" in block
        assert "[2]" in block
        assert "First" in block
        assert "Second" in block
        assert len(citations) == 2

    def test_format_evidence_no_url(self):
        from src.services.generator.response_generator import ResponseGenerator

        item = _make_evidence(content="No URL item")
        block, citations = ResponseGenerator._format_evidence([item])

        assert "[1]" in block
        assert "source:" not in block  # No URL shown
        assert citations[0]["url"] == ""

    def test_format_evidence_score(self):
        from src.services.generator.response_generator import ResponseGenerator

        item = _make_evidence(content="Scored item", score=0.85)
        block, citations = ResponseGenerator._format_evidence([item])

        assert citations[0]["score"] == pytest.approx(0.85)

    def test_format_evidence_no_score(self):
        from src.services.generator.response_generator import ResponseGenerator

        item = _make_evidence(content="No score", score=0.0)
        block, citations = ResponseGenerator._format_evidence([item])

        assert citations[0]["score"] is None