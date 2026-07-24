"""ChatOrchestrator — coordinates the full chat pipeline end-to-end.

This is the top-level entry point for the Ha-Shem AI Support Platform chat
flow.  It integrates all phases of the pipeline:

    1. **SourceRouter**     — decide which knowledge sources to query.
    2. **SearchManager**    — execute the routing decision across retrievers.
    3. **ContextMerger**    — deduplicate, rank, and normalise evidence.
    4. **ResponseGenerator** — generate a grounded answer with citations.
    5. **BackgroundLearning** — (optional) ingest new pages after responding.

Backward compatibility
----------------------
The public API (``process_request`` → ``{answer, sources}``) is preserved.
The legacy path (knowledge base → SupportService) remains available when no
new services are injected, making this a safe, incremental refactor.

Design decisions
----------------
* All services are injected at construction time (dependency injection),
  making the orchestrator trivially testable with mocks.
* The ``chat()`` method is the primary entry point.  It returns a dict that
  includes ``answer``, ``sources`` (list of URLs), and ``citations`` (rich
  metadata).  The ``sources`` field preserves the schema contract.
* Background learning is fire-and-forget — it runs in a background thread
  so it never blocks the response.
"""

from __future__ import annotations

import logging
from typing import Any

from ..api.schemas import ChatResponse
from ..services.knowledge import KnowledgeService
from ..services.support import SupportService
from ..services.routing import SourceRouter
from ..services.manager import SearchManager
from ..services.merger import ContextMerger
from ..services.generator import ResponseGenerator
from ..shared.logging import get_logger

logger: logging.Logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# ChatOrchestrator
# ---------------------------------------------------------------------------


class ChatOrchestrator:
    """Coordinates the chat flow while keeping the API layer thin.

    Args:
        knowledge_service:  A :class:`~services.knowledge.KnowledgeService`
            instance (used in the legacy path).  If ``None``, a default is
            created.
        support_service:    A :class:`~services.support.SupportService`
            instance (used in the legacy path).  If ``None``, a default is
            created.

    Keyword Args:
        source_router:     A :class:`~services.routing.SourceRouter` instance.
        search_manager:    A :class:`~services.manager.SearchManager` instance.
        context_merger:    A :class:`~services.merger.ContextMerger` instance.
        response_generator: A :class:`~services.generator.ResponseGenerator`
            instance.  When provided, it replaces the legacy
            ``support_service`` for answer generation.
        background_learning: A :class:`~services.learning.BackgroundLearning`
            instance.  When provided, new pages are ingested after responding.
        enable_background_learning: Whether to trigger background ingestion
            after each response.  Defaults to ``True`` when
            ``background_learning`` is provided.

    Typical usage::

        orchestrator = ChatOrchestrator(
            search_manager=SearchManager(),
            response_generator=ResponseGenerator(),
        )
        result = orchestrator.chat("What services do you offer?")
        print(result["answer"])
    """

    def __init__(
        self,
        knowledge_service: KnowledgeService | None = None,
        support_service: SupportService | None = None,
        *,
        source_router: Any = None,
        search_manager: Any = None,
        context_merger: Any = None,
        response_generator: Any = None,
        background_learning: Any = None,
        enable_background_learning: bool | None = None,
    ) -> None:
        # Legacy services
        self._knowledge_service = knowledge_service or KnowledgeService()
        self._support_service = support_service or SupportService()

        # New pipeline services (optional — when injected, they replace the
        # legacy path)
        self._source_router = source_router
        self._search_manager = search_manager
        self._context_merger = context_merger
        self._response_generator = response_generator
        self._background_learning = background_learning

        # Whether to trigger background learning after responses
        if enable_background_learning is None:
            self._enable_background_learning = background_learning is not None
        else:
            self._enable_background_learning = enable_background_learning

        self._using_new_pipeline = any([
            source_router,
            search_manager,
            context_merger,
            response_generator,
        ])

        if self._using_new_pipeline:
            logger.info(
                "ChatOrchestrator: using new multi-source pipeline "
                "(router=%s, manager=%s, merger=%s, generator=%s).",
                type(source_router).__name__ if source_router else "None",
                type(search_manager).__name__ if search_manager else "None",
                type(context_merger).__name__ if context_merger else "None",
                type(response_generator).__name__ if response_generator else "None",
            )
        else:
            logger.info("ChatOrchestrator: using legacy KB-only pipeline.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chat(self, message: str) -> dict[str, Any]:
        """Process a user message and return a response.

        This is the primary entry point.  It routes the question, retrieves
        evidence, generates an answer, and optionally triggers background
        learning.

        Args:
            message: The user's natural-language message.

        Returns:
            A dict with keys:
                ``answer`` (str):   The generated answer.
                ``sources`` (list[str]):  List of source URLs (backward
                    compatible with the ``ChatResponse`` schema).
                ``citations`` (list[dict]):  Rich source metadata (when
                    using the new pipeline).
        """
        if self._using_new_pipeline:
            return self._chat_new_pipeline(message)
        return self._chat_legacy(message)

    def process_request(self, message: str) -> dict[str, Any]:
        """Legacy alias for :meth:`chat` — preserved for backward compatibility.

        Returns:
            A dict with ``answer`` and ``sources`` keys.
        """
        return self.chat(message)

    def process_request_response(self, message: str) -> ChatResponse:
        """Process a request and return a Pydantic ``ChatResponse``.

        This method is used by the FastAPI route handler.

        Args:
            message: The user's natural-language message.

        Returns:
            A :class:`~api.schemas.ChatResponse` instance.
        """
        result = self.chat(message)
        return ChatResponse(
            answer=result["answer"],
            sources=result.get("sources", []),
        )

    # ------------------------------------------------------------------
    # Legacy pipeline (unchanged behaviour)
    # ------------------------------------------------------------------

    def _chat_legacy(self, message: str) -> dict[str, Any]:
        """Original pipeline: knowledge base → SupportService."""
        matches, _, parent_urls = self._knowledge_service.retrieve_context(message)
        if not matches:
            return {
                "answer": "I couldn't find enough relevant context in the knowledge base for that question.",
                "sources": [],
            }

        context_text = "\n".join(
            match.get("chunk_content", "") for match in matches if match.get("chunk_content")
        )
        result = self._support_service.generate_answer(message, context_text, parent_urls)
        return result

    # ------------------------------------------------------------------
    # New multi-source pipeline
    # ------------------------------------------------------------------

    def _chat_new_pipeline(self, message: str) -> dict[str, Any]:
        """Full multi-source pipeline with router, manager, merger, generator."""
        # --- Step 1: Route (SourceRouter) ---
        if self._source_router:
            decision = self._source_router.route(message)
        else:
            # If no router was injected, default to both
            from ..services.routing.source_router import RoutingDecision
            decision = RoutingDecision(knowledge=True, web=True)

        # --- Step 2: Retrieve (SearchManager) ---
        if self._search_manager:
            evidence = self._search_manager.retrieve(message, decision=decision)
        else:
            # Fallback: use legacy knowledge service
            matches, _, _ = self._knowledge_service.retrieve_context(message)
            if self._context_merger:
                evidence = self._context_merger.merge(knowledge=matches)
            else:
                evidence = []

        # --- Step 3: Generate answer (ResponseGenerator) ---
        if self._response_generator:
            result = self._response_generator.generate(
                question=message,
                context=evidence,
            )
            answer = result.get("answer", "")
            citations = result.get("citations", [])
        else:
            # Fallback: use legacy support service
            if evidence:
                context_text = "\n\n".join(e.content for e in evidence if e.content)
                sources = list({e.url for e in evidence if e.url})
                result = self._support_service.generate_answer(message, context_text, sources)
                answer = result.get("answer", "")
                citations = []
            else:
                answer = "I couldn't find enough relevant context to answer that question."
                citations = []

        # --- Step 4: Background learning (fire-and-forget) ---
        if self._enable_background_learning and self._background_learning:
            if citations:
                self._trigger_background_learning(citations)

        # --- Build response ---
        sources = list({
            c["url"] for c in citations if c and c.get("url")
        })

        return {
            "answer": answer,
            "sources": sources,
            "citations": citations,
        }

    # ------------------------------------------------------------------
    # Background learning
    # ------------------------------------------------------------------

    def _trigger_background_learning(self, citations: list[dict[str, object]]) -> None:
        """Ingest new URLs in a background thread.

        Only URLs that are not already in the knowledge base are ingested.
        This is fire-and-forget — errors are logged but never propagated.
        """
        import threading

        def _ingest() -> None:
            for citation in citations:
                url = citation.get("url", "")
                if not url:
                    continue
                try:
                    self._background_learning.ingest(url)  # type: ignore[union-attr]
                except Exception as exc:
                    logger.warning(
                        "BackgroundLearning: failed to ingest %s — %s", url, exc
                    )

        thread = threading.Thread(target=_ingest, daemon=True, name="bg-learn")
        thread.start()
        logger.debug("ChatOrchestrator: background learning thread started.")


# Module-level singleton (imported by ``src.api.routes.chat``).
#
# Wired to the multi-source pipeline (SourceRouter -> SearchManager ->
# ContextMerger -> ResponseGenerator). Each component builds its own
# dependencies lazily from environment settings (Settings.from_environment())
# on first use, so this is safe to construct at import time even before
# .env is loaded. If TAVILY_API_KEY/BRAVE_SEARCH_API_KEY are unset, web
# search calls fail individually and SearchManager falls back to
# knowledge-base-only evidence — the chat flow degrades gracefully rather
# than breaking. process_request/process_request_response/chat() all keep
# their existing signatures and return shapes, preserving backward
# compatibility with the FastAPI route handler and CLI.
chat_orchestrator = ChatOrchestrator(
    source_router=SourceRouter(),
    search_manager=SearchManager(),
    context_merger=ContextMerger(),
    response_generator=ResponseGenerator(),
)
