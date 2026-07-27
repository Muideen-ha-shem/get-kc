"""ResponseGenerator — generates grounded answers from unified evidence.

This service sits at the final stage of the retrieval pipeline.  It receives
unified evidence (a list of :class:`~services.merger.EvidenceItem`) and a
user question, formats a prompt that instructs the LLM to answer using *only*
the provided evidence, and returns a structured response with inline citations.

Design decisions
----------------
* The LLM is called with ``temperature=0.1`` for deterministic, factual answers.
* The prompt explicitly instructs the model to cite sources using ``[1]``, ``[2]``
  notation, making citations traceable back to the evidence list.
* If the evidence is insufficient, the model is instructed to say so rather than
  fabricate an answer.
* The service is independent of which retriever produced the evidence — it works
  with any list of :class:`EvidenceItem`.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Sequence

from dotenv import load_dotenv

load_dotenv()

from ...shared.logging import get_logger
from ..merger.context_merger import EvidenceItem

logger: logging.Logger = get_logger(__name__)

# System prompt template.  ``{num_sources}`` and ``{evidence_block}`` are
# substituted at call time.
_SYSTEM_PROMPT_TEMPLATE: str = """\
You are a strict, helpful corporate assistant.  Answer the user's question \
using ONLY the evidence provided below.  The evidence is organised into \
{num_sources} numbered item(s), each with an optional source URL.

Rules:
1.  Base your answer *only* on the evidence.  Do NOT use any external knowledge.
2.  When you use information from a specific item, cite it with its number in \
square brackets — for example ``[1]``, ``[2]``.
3.  If multiple items support the same statement, cite all of them.
4.  If the evidence does not contain enough information to answer the question \
fully, say so clearly.  Do NOT guess or make up information.
5.  Include the source URLs at the end of your answer under a "Sources" heading.

Evidence:
{evidence_block}"""


# ---------------------------------------------------------------------------
# ResponseGenerator
# ---------------------------------------------------------------------------


class ResponseGenerator:
    """Generates a grounded, cited answer from unified evidence.

    Args:
        model:         The Groq model identifier.  Defaults to
                       ``"openai/gpt-oss-120b"``.
        temperature:   LLM temperature for generation.  Defaults to ``0.1``.
        max_tokens:    Maximum tokens in the generated response.
                       Defaults to ``1024``.
        api_key:       Groq API key.  If ``None``, read from the
                       ``GROQ_API_KEY`` environment variable.
        citation_validator: An object with a
                       ``validate(citations) -> list[dict]`` method (see
                       ``services.validation.CitationValidator``). When
                       given, it cleans up the citation list (removing
                       duplicates and placeholder URLs such as
                       ``"Unknown URL"``) before it's returned. ``None``
                       (the default) returns citations exactly as built —
                       unchanged from prior behaviour.

    Typical usage::

        from src.services.generator import ResponseGenerator

        generator = ResponseGenerator()
        result = generator.generate(
            question="What services does Ha-Shem offer?",
            context=[evidence_item_1, evidence_item_2],
        )
        print(result["answer"])    # The generated text
        print(result["citations"])  # List of source dicts
    """

    def __init__(
        self,
        model: str = "openai/gpt-oss-120b",
        temperature: float = 0.1,
        max_tokens: int = 1024,
        api_key: str | None = None,
        citation_validator: Any = None,
    ) -> None:
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._api_key = api_key or os.getenv("GROQ_API_KEY")
        self._citation_validator = citation_validator

        if not self._api_key:
            logger.warning(
                "ResponseGenerator: no GROQ_API_KEY set — generate() will raise ValueError."
            )

        logger.info(
            "ResponseGenerator ready (model=%s, temperature=%.1f, max_tokens=%d, citation_validator=%s).",
            model,
            temperature,
            max_tokens,
            type(self._citation_validator).__name__ if self._citation_validator else "None",
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        question: str,
        context: Sequence[EvidenceItem] | None = None,
        primary_product: str | None = None,
        complementary_products: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        """Generate a grounded answer from *question* and *context*.

        Args:
            question: The user's natural-language question.
            context:  A list of :class:`EvidenceItem` objects from the
                      :class:`~services.manager.SearchManager`.  May be
                      empty or ``None``.
            primary_product: When the question matched a business-theme
                      recommendation cluster with a designated primary
                      product (see ``ProductRouter``/``BUSINESS_THEMES``),
                      its name — otherwise ``None``. When set, the prompt
                      asks the model to recommend it as the primary
                      solution and frame the rest as complementary. When
                      ``None`` (the default — every existing caller),
                      behaviour is identical to before this parameter
                      existed.
            complementary_products: The other relevant products for that
                      same business-theme match — either the rest of the
                      cluster (when ``primary_product`` is set) or the
                      whole cluster (when the theme has no single primary,
                      e.g. a company-wide transformation touching several
                      unrelated departments equally). ``None``/empty means
                      no business-theme framing is added to the prompt.

        Returns:
            A dict with keys:
                ``answer`` (str):   The generated answer text.
                ``citations`` (list[dict]):  Source metadata for each
                    evidence item, with keys ``url``, ``title``,
                    ``source_type``, ``score``.
                ``raw`` (str):      The raw LLM response (for debugging).

        Raises:
            ValueError: If ``question`` is empty or ``GROQ_API_KEY`` is
                        not configured.
        """
        question_clean = (question or "").strip()
        if not question_clean:
            raise ValueError("generate() requires a non-empty question.")

        if not self._api_key:
            raise ValueError(
                "GROQ_API_KEY is not set.  Either pass ``api_key`` to the "
                "constructor or set the GROQ_API_KEY environment variable."
            )

        # --- Build evidence block and citations ---
        evidence_list = list(context) if context else []
        evidence_block, citations = self._format_evidence(evidence_list)
        citations = self._validate_citations(citations)

        if not evidence_block:
            logger.info("ResponseGenerator: no evidence provided.")
            return {
                "answer": "I don't have enough information to answer that question.",
                "citations": [],
                "raw": "",
            }

        # --- Assemble prompt ---
        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
            num_sources=len(evidence_list),
            evidence_block=evidence_block,
        )
        system_prompt += self._build_recommendation_framing(primary_product, complementary_products)
        user_prompt = question_clean

        logger.info(
            "ResponseGenerator: generating answer (question=%r, evidence=%d, model=%s).",
            question_clean,
            len(evidence_list),
            self._model,
        )

        # --- Call LLM ---
        try:
            from groq import Groq

            client = Groq(api_key=self._api_key)
            completion = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                stream=False,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
            )
            raw_answer: str = completion.choices[0].message.content or ""

        except Exception as exc:
            logger.error(
                "ResponseGenerator: LLM call failed — %s", exc, exc_info=True
            )
            return {
                "answer": "I encountered an error while generating the response. Please try again.",
                "citations": citations,
                "raw": "",
            }

        answer = raw_answer.strip()
        if not answer:
            answer = "I couldn't generate a grounded response from the available context."

        return {
            "answer": answer,
            "citations": citations,
            "raw": raw_answer,
        }

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_recommendation_framing(
        primary_product: str | None,
        complementary_products: Sequence[str] | None,
    ) -> str:
        """Extra prompt instructions for a business recommendation — empty
        string (no change to the prompt at all) unless the caller passed a
        ``primary_product`` and/or non-empty ``complementary_products``, so
        every existing caller that doesn't pass these two ``generate()``
        params is unaffected."""
        others = ", ".join(complementary_products) if complementary_products else ""

        if primary_product and others:
            return (
                f"\n\nBusiness recommendation framing: this question describes a "
                f"business need best addressed primarily by {primary_product}, with "
                f"{others} as complementary solutions. Structure your answer to: "
                f"(1) recommend {primary_product} as the primary solution, "
                f"(2) explain specifically why it fits the stated need, "
                f"(3) introduce {others} as complementary solutions and explain the "
                f"role each one plays. Base every recommendation and every claim "
                f"strictly on the evidence above — do not invent products, features, "
                f"or capabilities not present in it, and do not recommend a product "
                f"the evidence does not cover."
            )

        if primary_product:
            return (
                f"\n\nBusiness recommendation framing: this question describes a "
                f"business need best addressed by {primary_product}. Recommend it "
                f"directly — for example, \"Based on your use case, I recommend "
                f"{primary_product} because...\" — explain specifically why it fits "
                f"the stated need, and highlight its primary business benefit. Base "
                f"every claim strictly on the evidence above — do not invent "
                f"products, features, or capabilities not present in it."
            )

        if others:
            return (
                f"\n\nBusiness recommendation framing: this question spans multiple "
                f"relevant solutions with no single dominant one — {others}. Structure "
                f"your answer to explain the role each solution plays in addressing the "
                f"need. Base every recommendation and every claim strictly on the "
                f"evidence above — do not invent products, features, or capabilities not "
                f"present in it, do not recommend a product the evidence does not cover, "
                f"and do not present one solution as more important than the others "
                f"unless the evidence itself supports that."
            )

        return ""

    def _validate_citations(self, citations: list[dict[str, object]]) -> list[dict[str, object]]:
        """Run the injected citation validator, if any.

        Applied to the ``citations``/``sources`` metadata returned to
        callers only — never to the LLM's own answer text, which the model
        writes independently (including its own "Sources" section) from the
        original, unfiltered evidence block. A validator failure falls back
        to the unfiltered citations rather than dropping them.
        """
        if self._citation_validator is None or not citations:
            return citations
        try:
            return self._citation_validator.validate(citations)
        except Exception as exc:
            logger.warning("ResponseGenerator: citation validation failed — %s. Using unfiltered citations.", exc)
            return citations

    @staticmethod
    def _format_evidence(
        evidence: list[EvidenceItem],
    ) -> tuple[str, list[dict[str, object]]]:
        """Format evidence items into a prompt block and collect citations.

        Args:
            evidence: The list of :class:`EvidenceItem` objects.

        Returns:
            A ``(evidence_block, citations)`` tuple:
            - evidence_block: A string ready to insert into the system prompt.
            - citations: A list of dicts with source metadata.
        """
        if not evidence:
            return "", []

        lines: list[str] = []
        citations: list[dict[str, object]] = []

        for idx, item in enumerate(evidence, start=1):
            url_part = f" (source: {item.url})" if item.url else ""
            title_part = f" — {item.title}" if item.title else ""
            lines.append(
                f"[{idx}]{title_part}{url_part}\n{item.content}"
            )

            citations.append({
                "url": item.url,
                "title": item.title,
                "source_type": item.source_type,
                "score": round(item.score, 6) if item.score else None,
            })

        return "\n\n".join(lines), citations