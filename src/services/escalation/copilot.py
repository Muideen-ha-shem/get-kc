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

from typing import Any

from ...shared.product_registry import PRODUCT_REGISTRY
from ..generator.response_generator import ResponseGenerator
from ..knowledge.knowledge_service import KnowledgeService
from ..merger.context_merger import ContextMerger
from ..validation.citation_validator import CitationValidator


def suggest_reply(
    *,
    workspace_id: str,
    question: str,
    knowledge_service: KnowledgeService | None = None,
    response_generator: ResponseGenerator | None = None,
) -> dict[str, Any]:
    """Drafts a suggested reply grounded in the workspace's own knowledge
    base — the same evidence the customer-facing AI would have used.
    Returns ``{"draft": str, "citations": list[dict]}``. If retrieval finds
    nothing, ``ResponseGenerator.generate()`` already short-circuits to its
    existing "not enough information" answer — surfaced as-is, not replaced
    with a new fallback.
    """
    knowledge_service = knowledge_service or KnowledgeService()
    response_generator = response_generator or ResponseGenerator(citation_validator=CitationValidator())

    matches, _similarities, _urls = knowledge_service.retrieve_context(question, workspace_id=workspace_id)
    evidence = ContextMerger().merge(knowledge=matches, question=question)

    result = response_generator.generate(question=question, context=evidence)
    return {"draft": result.get("answer", ""), "citations": result.get("citations", [])}


def recommend_documentation(product: str) -> str | None:
    """Trivial reuse of the product registry's own doc URL — no new logic."""
    info = PRODUCT_REGISTRY.get(product)
    return info["url"] if info else None
