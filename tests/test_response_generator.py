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
# ResponseGenerator — citation_validator integration
# ---------------------------------------------------------------------------


class TestResponseGeneratorCitationValidator:
    def test_no_validator_injected_returns_citations_unchanged(self):
        from src.services.generator.response_generator import ResponseGenerator

        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "Answer [1]."

        with patch("groq.Groq") as mock_groq:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_groq.return_value = mock_client

            gen = ResponseGenerator(api_key="test-key")  # citation_validator=None
            result = gen.generate(
                question="test",
                context=[_make_evidence(url="Unknown URL")],
            )

        assert result["citations"][0]["url"] == "Unknown URL"

    def test_validator_applied_to_returned_citations(self):
        from src.services.generator.response_generator import ResponseGenerator

        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "Answer [1][2]."

        mock_validator = MagicMock()
        mock_validator.validate.return_value = [{"url": "https://kept.example.com"}]

        with patch("groq.Groq") as mock_groq:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_groq.return_value = mock_client

            gen = ResponseGenerator(api_key="test-key", citation_validator=mock_validator)
            result = gen.generate(
                question="test",
                context=[
                    _make_evidence(url="Unknown URL"),
                    _make_evidence(url="https://kept.example.com"),
                ],
            )

        assert result["citations"] == [{"url": "https://kept.example.com"}]
        mock_validator.validate.assert_called_once()

    def test_answer_text_untouched_by_citation_validation(self):
        """The validator only cleans the returned citation list — never the LLM's answer text."""
        from src.services.generator.response_generator import ResponseGenerator

        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "The full answer with [1] inline."

        mock_validator = MagicMock()
        mock_validator.validate.return_value = []  # drop everything

        with patch("groq.Groq") as mock_groq:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_groq.return_value = mock_client

            gen = ResponseGenerator(api_key="test-key", citation_validator=mock_validator)
            result = gen.generate(question="test", context=[_make_evidence()])

        assert result["answer"] == "The full answer with [1] inline."
        assert result["citations"] == []

    def test_validator_failure_falls_back_to_unfiltered_citations(self):
        from src.services.generator.response_generator import ResponseGenerator

        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "Answer [1]."

        mock_validator = MagicMock()
        mock_validator.validate.side_effect = RuntimeError("validator exploded")

        with patch("groq.Groq") as mock_groq:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_groq.return_value = mock_client

            gen = ResponseGenerator(api_key="test-key", citation_validator=mock_validator)
            result = gen.generate(
                question="test",
                context=[_make_evidence(url="https://example.com")],
            )

        # Falls back to the unfiltered citation rather than raising/dropping it
        assert len(result["citations"]) == 1
        assert result["citations"][0]["url"] == "https://example.com"

    def test_empty_context_never_calls_validator(self):
        from src.services.generator.response_generator import ResponseGenerator

        mock_validator = MagicMock()
        gen = ResponseGenerator(api_key="test-key", citation_validator=mock_validator)
        result = gen.generate(question="test", context=[])

        assert result["citations"] == []
        mock_validator.validate.assert_not_called()


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


# ---------------------------------------------------------------------------
# Phase 17 — business-recommendation framing (primary_product /
# complementary_products). Every existing caller omits these two params, so
# the first priority is proving that omitting them changes nothing.
# ---------------------------------------------------------------------------


class TestResponseGeneratorRecommendationFraming:
    def test_no_recommendation_params_leaves_prompt_unchanged(self):
        """The exact regression this whole feature must not break: every
        pre-existing call site (SearchManager-only pipeline, no business
        theme) omits primary_product/complementary_products entirely."""
        from src.services.generator.response_generator import ResponseGenerator

        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "Answer [1]."

        with patch("groq.Groq") as mock_groq:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_groq.return_value = mock_client

            gen = ResponseGenerator(api_key="test-key")
            gen.generate(
                question="What does SPIDIFY do?",
                context=[_make_evidence(content="SPIDIFY verifies identity.", url="https://havisspidify.com/")],
            )

            system_prompt = mock_client.chat.completions.create.call_args.kwargs["messages"][0]["content"]

        assert "Business recommendation framing" not in system_prompt

    def test_primary_and_complementary_adds_framing_instruction(self):
        from src.services.generator.response_generator import ResponseGenerator

        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "ZivaAIRA is the primary recommendation [1]."

        with patch("groq.Groq") as mock_groq:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_groq.return_value = mock_client

            gen = ResponseGenerator(api_key="test-key")
            gen.generate(
                question="We want to modernize our HR operations",
                context=[_make_evidence(content="ZivaAIRA automates hiring.", url="https://aira.havis360.com/")],
                primary_product="ZivaAIRA",
                complementary_products=["STAAS", "Havis Vacay", "PayCheq", "WeCare", "Havis iReport"],
            )

            system_prompt = mock_client.chat.completions.create.call_args.kwargs["messages"][0]["content"]

        assert "Business recommendation framing" in system_prompt
        assert "primary" in system_prompt.lower()
        assert "ZivaAIRA" in system_prompt
        assert "STAAS" in system_prompt
        assert "do not invent products" in system_prompt.lower()

    def test_complementary_without_primary_adds_parallel_framing(self):
        """A theme with no single dominant product (e.g. company-wide
        digital transformation) still gets framing, just without
        designating any one product as primary."""
        from src.services.generator.response_generator import ResponseGenerator

        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "Several solutions apply here [1][2]."

        with patch("groq.Groq") as mock_groq:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_groq.return_value = mock_client

            gen = ResponseGenerator(api_key="test-key")
            gen.generate(
                question="We are digitizing our company",
                context=[_make_evidence(content="ZivaAIRA automates hiring.", url="https://aira.havis360.com/")],
                primary_product=None,
                complementary_products=["ZivaAIRA", "STAAS", "Havis Vacay"],
            )

            system_prompt = mock_client.chat.completions.create.call_args.kwargs["messages"][0]["content"]

        assert "Business recommendation framing" in system_prompt
        assert "no single dominant one" in system_prompt
        assert "ZivaAIRA" in system_prompt

    def test_primary_product_alone_adds_single_product_framing(self):
        """Phase 19: a lone primary_product (no complementary products) —
        e.g. "we're struggling to verify identities" -> SPIDIFY alone —
        must still get "recommend X because..." framing, not just the
        primary+complementary combo from Phase 17."""
        from src.services.generator.response_generator import ResponseGenerator

        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "I recommend SPIDIFY [1]."

        with patch("groq.Groq") as mock_groq:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_groq.return_value = mock_client

            gen = ResponseGenerator(api_key="test-key")
            gen.generate(
                question="Tell me about SPIDIFY",
                context=[_make_evidence(content="SPIDIFY verifies identity.", url="https://havisspidify.com/")],
                primary_product="SPIDIFY",
                complementary_products=[],
            )

            system_prompt = mock_client.chat.completions.create.call_args.kwargs["messages"][0]["content"]

        assert "Business recommendation framing" in system_prompt
        assert "SPIDIFY" in system_prompt
        assert "do not invent" in system_prompt.lower()

    def test_build_recommendation_framing_directly(self):
        from src.services.generator.response_generator import ResponseGenerator

        assert ResponseGenerator._build_recommendation_framing(None, None) == ""
        assert ResponseGenerator._build_recommendation_framing(None, []) == ""

        solo = ResponseGenerator._build_recommendation_framing("X", [])
        assert "X" in solo
        assert "Business recommendation framing" in solo

        framed = ResponseGenerator._build_recommendation_framing("V-Login", ["SPIDIFY"])
        assert "V-Login" in framed
        assert "SPIDIFY" in framed
        assert "primary" in framed.lower()


class TestResponseGeneratorCatalogGuardrail:
    """Live-confirmed bug this fixes: a fully vague question (no
    primary_product/complementary_products at all) let the model name
    real third-party competitor products surfaced by a web search. The
    guardrail must be present in the prompt EVEN with no recommendation
    params — that's exactly the case that broke."""

    def test_guardrail_present_even_without_primary_product(self):
        from src.services.generator.response_generator import ResponseGenerator

        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "Answer [1]."

        with patch("groq.Groq") as mock_groq:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_groq.return_value = mock_client

            gen = ResponseGenerator(api_key="test-key")
            gen.generate(
                question="Recommend the best solution for my business",
                context=[_make_evidence(content="Generic business advice.", url="https://example.com/")],
            )

            system_prompt = mock_client.chat.completions.create.call_args.kwargs["messages"][0]["content"]

        assert "Product-catalog guardrail" in system_prompt
        assert "SPIDIFY" in system_prompt
        assert "PayCheq" in system_prompt
        assert "third-party" in system_prompt.lower()
        assert "competitor" in system_prompt.lower()

    def test_guardrail_present_alongside_recommendation_framing_too(self):
        from src.services.generator.response_generator import ResponseGenerator

        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "I recommend SPIDIFY [1]."

        with patch("groq.Groq") as mock_groq:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_groq.return_value = mock_client

            gen = ResponseGenerator(api_key="test-key")
            gen.generate(
                question="Tell me about SPIDIFY",
                context=[_make_evidence(content="SPIDIFY verifies identity.", url="https://havisspidify.com/")],
                primary_product="SPIDIFY",
                complementary_products=[],
            )

            system_prompt = mock_client.chat.completions.create.call_args.kwargs["messages"][0]["content"]

        assert "Business recommendation framing" in system_prompt
        assert "Product-catalog guardrail" in system_prompt

    def test_build_catalog_guardrail_directly(self):
        from src.services.generator.response_generator import ResponseGenerator

        guardrail = ResponseGenerator._build_catalog_guardrail()
        assert "SPIDIFY" in guardrail
        assert "ZivaAIRA" in guardrail
        assert "Dynamics 365" in guardrail

    def test_fallback_guardrail_used_on_registry_failure(self):
        from src.services.generator import response_generator as rg_module
        from src.services.generator.response_generator import ResponseGenerator

        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "Answer [1]."

        with patch("groq.Groq") as mock_groq, \
             patch.object(ResponseGenerator, "_build_catalog_guardrail", side_effect=RuntimeError("boom")):
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_groq.return_value = mock_client

            gen = ResponseGenerator(api_key="test-key")
            gen.generate(
                question="Recommend the best solution for my business",
                context=[_make_evidence(content="Generic business advice.", url="https://example.com/")],
            )

            system_prompt = mock_client.chat.completions.create.call_args.kwargs["messages"][0]["content"]

        assert rg_module._CATALOG_GUARDRAIL_FALLBACK.strip() in system_prompt