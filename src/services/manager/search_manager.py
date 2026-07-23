"""SearchManager — executes the routing decision and coordinates retrievers.

This service sits at the top of the retrieval pipeline.  It receives a
:class:`~services.routing.RoutingDecision`, invokes the appropriate
retrievers, and returns a unified collection of evidence (via the
:class:`~services.merger.ContextMerger`).

Workflow
--------
1. Receive a user question (implicitly or explicitly via a routing decision).
2. Use :class:`~services.routing.SourceRouter` to decide which sources to query.
3. For each active source, call the corresponding retriever.
4. Pass all results through :class:`~services.merger.ContextMerger` for
   deduplication, ranking, and normalisation.
5. Return a list of :class:`~services.merger.EvidenceItem`.

Design decisions
----------------
* All retrievers are injected at construction time (dependency injection),
  making the service trivially testable with mocks.
* No answer generation happens here — the manager's job ends when it has
  gathered evidence.
* The search provider (Tavily/Brave) is configured externally and passed in
  via ``SearchService``.
"""

from __future__ import annotations

import logging
from typing import Any, Sequence

from ...shared.logging import get_logger
from ..routing.source_router import SourceRouter, RoutingDecision
from ..merger.context_merger import ContextMerger, EvidenceItem

logger: logging.Logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# SearchManager
# ---------------------------------------------------------------------------


class SearchManager:
    """Coordinates multi-source retrieval based on a routing decision.

    Args:
        source_router:   A :class:`~services.routing.SourceRouter` instance.
                         If ``None``, a default one is created.
        context_merger:  A :class:`~services.merger.ContextMerger` instance.
                         If ``None``, a default one is created.

    Keyword Args:
        knowledge_service: An object with a ``retrieve_context(question)``
            method returning ``(matches, similarities, parent_urls)``.  When
            omitted, the real ``KnowledgeService`` is imported and used.
        search_service: An object with a ``search(query, max_results)`` method
            returning ``list[SearchResult]``.  When omitted, the real
            ``SearchService`` is imported and used (requires configured keys).
        page_fetcher: An object with a ``fetch(url) -> str`` method.  When
            omitted, the real ``PageFetcher`` is used.
        ephemeral_rag: An object with a ``retrieve(question, pages) -> list``
            method.  When omitted, the real ``EphemeralRAG`` is used.
        live_search_max_results: Max results per live search call (default 5).
        live_page_max_fetch: Max live pages to download for RAG (default 3).

    Typical usage::

        manager = SearchManager()

        # Simple entry point — router decides the strategy
        evidence = manager.retrieve("What are the latest product prices?")

        # Or pass a pre-computed routing decision
        decision = RoutingDecision(knowledge=False, web=True)
        evidence = manager.retrieve("latest news", decision=decision)
    """

    def __init__(
        self,
        source_router: SourceRouter | None = None,
        context_merger: ContextMerger | None = None,
        *,
        knowledge_service: Any = None,
        search_service: Any = None,
        page_fetcher: Any = None,
        ephemeral_rag: Any = None,
        live_search_max_results: int = 5,
        live_page_max_fetch: int = 3,
    ) -> None:
        self._source_router = source_router or SourceRouter()
        self._context_merger = context_merger or ContextMerger()
        self._live_search_max_results = live_search_max_results
        self._live_page_max_fetch = live_page_max_fetch

        # Lazy-import real services only when needed
        self._knowledge_service: Any = knowledge_service
        self._search_service: Any = search_service
        self._page_fetcher: Any = page_fetcher
        self._ephemeral_rag: Any = ephemeral_rag

        logger.info(
            "SearchManager ready (router=%s, merger=%s).",
            type(self._source_router).__name__,
            type(self._context_merger).__name__,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve(
        self,
        question: str,
        decision: RoutingDecision | None = None,
    ) -> list[EvidenceItem]:
        """Execute the retrieval plan for *question* and return evidence.

        Args:
            question: The user's natural-language question.
            decision: An optional pre-computed routing decision.  When
                      ``None``, the ``SourceRouter`` is called automatically.

        Returns:
            A list of :class:`~services.merger.EvidenceItem` ordered by
            relevance (highest score first).  An empty list is returned if
            no evidence is found or the question is blank.

        Raises:
            ValueError: If ``question`` is empty after stripping.
        """
        # --- Step 1: Route ---
        actual_decision = decision if decision is not None else self._source_router.route(question)
        logger.info(
            "SearchManager.retrieve: question=%r, decision=%s.",
            question,
            actual_decision.to_dict(),
        )

        if not actual_decision.any_active():
            logger.warning("SearchManager.retrieve: routing decision has no active sources.")
            return []

        # --- Step 2: Retrieve from each active source ---
        knowledge_evidence: list[dict[str, Any]] | None = None
        web_search_results: list[Any] | None = None
        live_page_chunks: list[Any] | None = None

        if actual_decision.knowledge:
            knowledge_evidence = self._retrieve_knowledge(question)

        if actual_decision.web:
            web_search_results = self._retrieve_web_search(question)
            live_page_chunks = self._retrieve_live_pages(question, web_search_results)

        # --- Step 3: Merge ---
        evidence = self._context_merger.merge(
            knowledge=knowledge_evidence,
            web_search=web_search_results,
            live_pages=live_page_chunks,
        )

        logger.info(
            "SearchManager.retrieve: returning %d evidence items.",
            len(evidence),
        )
        return evidence

    # ------------------------------------------------------------------
    # Per-source retrieval
    # ------------------------------------------------------------------

    def _retrieve_knowledge(self, question: str) -> list[dict[str, Any]] | None:
        """Query the internal knowledge base (Supabase vector search)."""
        try:
            svc = self._get_knowledge_service()
            matches, _similarities, _urls = svc.retrieve_context(question)
            if matches:
                logger.info(
                    "SearchManager: knowledge base returned %d matches.", len(matches)
                )
            else:
                logger.info("SearchManager: knowledge base returned no matches.")
            return matches or None
        except Exception as exc:
            logger.error(
                "SearchManager: knowledge retrieval failed — %s", exc, exc_info=True
            )
            return None

    def _retrieve_web_search(self, question: str) -> list[Any] | None:
        """Perform a live web search."""
        try:
            svc = self._get_search_service()
            results = svc.search(question, max_results=self._live_search_max_results)
            if results:
                logger.info(
                    "SearchManager: web search returned %d results.", len(results)
                )
            else:
                logger.info("SearchManager: web search returned no results.")
            return results or None
        except Exception as exc:
            logger.error(
                "SearchManager: web search failed — %s", exc, exc_info=True
            )
            return None

    def _retrieve_live_pages(
        self,
        question: str,
        web_results: list[Any] | None,
    ) -> list[Any] | None:
        """Download top web results and run in-memory RAG."""
        if not web_results:
            return None

        # Collect URLs from search results
        urls: list[str] = []
        for result in web_results:
            url = getattr(result, "url", None)
            if not url and isinstance(result, dict):
                url = result.get("url", "")
            if url:
                urls.append(str(url))

        if not urls:
            return None

        # Download pages (up to the configured limit)
        fetcher = self._get_page_fetcher()
        pages: list[str] = []
        for url in urls[: self._live_page_max_fetch]:
            try:
                html = fetcher.fetch(url)
                pages.append(html)
                logger.info("SearchManager: fetched %d bytes from %s.", len(html), url)
            except Exception as exc:
                logger.warning(
                    "SearchManager: failed to fetch %s — %s", url, exc
                )

        if not pages:
            logger.info("SearchManager: no live pages could be fetched.")
            return None

        # Run ephemeral RAG against the downloaded pages
        rag = self._get_ephemeral_rag()
        try:
            chunks = rag.retrieve(question, pages)
            logger.info(
                "SearchManager: ephemeral RAG returned %d chunks from %d pages.",
                len(chunks),
                len(pages),
            )
            return chunks or None
        except Exception as exc:
            logger.error(
                "SearchManager: ephemeral RAG failed — %s", exc, exc_info=True
            )
            return None

    # ------------------------------------------------------------------
    # Lazy service accessors
    # ------------------------------------------------------------------

    def _get_knowledge_service(self) -> Any:
        if self._knowledge_service is None:
            from ..knowledge.knowledge_service import KnowledgeService
            self._knowledge_service = KnowledgeService()
        return self._knowledge_service

    def _get_search_service(self) -> Any:
        if self._search_service is None:
            from ...config.settings import Settings
            settings = Settings.from_environment()
            self._search_service = settings.build_search_service()
        return self._search_service

    def _get_page_fetcher(self) -> Any:
        if self._page_fetcher is None:
            from ...config.settings import Settings
            settings = Settings.from_environment()
            self._page_fetcher = settings.build_page_fetcher()
        return self._page_fetcher

    def _get_ephemeral_rag(self) -> Any:
        if self._ephemeral_rag is None:
            from ..rag.ephemeral_rag import EphemeralRAG  # type: ignore[import]
            self._ephemeral_rag = EphemeralRAG()
        return self._ephemeral_rag