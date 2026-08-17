"""AI Copilot for agents (Phase 25) — drafts, never sends.

Reuses the existing knowledge retrieval + generation stack read-only: a
fresh ``KnowledgeService``/``ContextMerger``/``ResponseGenerator`` are
constructed locally here, never the ``chat_orchestrator`` singleton, and
nothing in this module is ever called from the customer-facing `/chat`
path. The agent must review, edit, and explicitly send a draft through the
existing `POST /agent/escalations/{id}/messages` endpoint — this module
never writes a message itself.
"""

from __future__ import annotations

import re
from typing import Any

from ...shared.product_registry import PRODUCT_REGISTRY
from ..generator.response_generator import ResponseGenerator
from ..knowledge.knowledge_service import KnowledgeService
from ..merger.context_merger import ContextMerger, EvidenceItem
from ..validation.citation_validator import CitationValidator

_SOURCES_SECTION_RE = re.compile(r"\n{0,2}\*{0,2}Sources\*{0,2}\s*\n(\[\d+\][^\n]*\n?)*\s*$", re.IGNORECASE)


def clean_dangling_citations(answer: str, citations: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """Drops citation entries with no real URL (e.g. a synthetic
    conversation-transcript evidence item used to ground a summary) and,
    if none remain, strips the model's own trailing "Sources" heading from
    the answer text — never leave a "Sources" section pointing at nothing.
    Real citations (real URLs) are always preserved untouched."""
    real_citations = [c for c in citations if c.get("url")]
    if len(real_citations) == len(citations):
        return answer, citations
    if not real_citations:
        answer = _SOURCES_SECTION_RE.sub("", answer).rstrip()
    return answer, real_citations


def suggest_reply(
    *,
    workspace_id: str,
    question: str,
    conversation_transcript: str | None = None,
    knowledge_service: KnowledgeService | None = None,
    response_generator: ResponseGenerator | None = None,
) -> dict[str, Any]:
    """Drafts a suggested reply grounded in the workspace's own knowledge
    base — the same evidence the customer-facing AI would have used — plus
    the escalation's own conversation transcript when supplied, so
    requests like "summarize this conversation" have something to ground
    on beyond the KB. The transcript is added as a synthetic evidence item
    (not folded into the question) so it stays available even when KB
    retrieval finds nothing — ``ResponseGenerator.generate()`` short-
    circuits to its "not enough information" answer only when *all*
    evidence, including the transcript, is empty. Returns
    ``{"draft": str, "citations": list[dict]}`` with any citation pointing
    at the synthetic transcript item (no real URL) stripped via
    ``clean_dangling_citations``.
    """
    knowledge_service = knowledge_service or KnowledgeService()
    response_generator = response_generator or ResponseGenerator(citation_validator=CitationValidator())

    matches, _similarities, _urls = knowledge_service.retrieve_context(question, workspace_id=workspace_id)
    evidence = ContextMerger().merge(knowledge=matches, question=question)
    if conversation_transcript:
        evidence = [
            EvidenceItem(
                content=conversation_transcript, score=1.0, title="Conversation so far",
                url="", source_type="escalation_transcript",
            ),
            *evidence,
        ]

    result = response_generator.generate(question=question, context=evidence)
    answer, citations = clean_dangling_citations(result.get("answer", ""), result.get("citations", []))
    return {"draft": answer, "citations": citations}


def recommend_documentation(product: str) -> str | None:
    """Trivial reuse of the product registry's own doc URL — no new logic."""
    info = PRODUCT_REGISTRY.get(product)
    return info["url"] if info else None
