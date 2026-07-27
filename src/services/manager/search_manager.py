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
* Two optional refinement stages sit after ``ContextMerger.merge()``: a
  ``semantic_reranker`` (passed through to the lazily-built ``EphemeralRAG``
  for live-page chunks) and a ``source_ranker`` (applied to the final merged
  evidence). Both default to ``None``, which preserves the exact prior
  behaviour — ``retrieve()``'s signature and return type are unchanged.
* Three more optional stages, all also ``None``-by-default: a
  ``query_rewriter`` (turns the question into a search-engine-friendly
  query before it's sent to Tavily/Brave), a ``domain_filter`` (drops/
  reorders candidate live-page URLs by domain quality before they're
  fetched), and a ``response_cache`` (a ``TTLCache`` shared across
  rewritten queries, search results, and fetched pages, so repeated
  questions within the cache TTL skip redundant network calls).
* Live-page downloads run concurrently (bounded by ``fetch_concurrency``)
  via ``asyncio.to_thread`` over the same synchronous ``PageFetcher.fetch``
  used before — this reuses its retry/SSL/timeout/logging behaviour
  unchanged, it just runs several fetches at once instead of one at a time.
  If a caller invokes ``retrieve()`` from inside a thread that already has
  a running asyncio event loop, this falls back to sequential fetching
  rather than raising.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Sequence

from ...shared.logging import get_logger
from ..routing.source_router import SourceRouter, RoutingDecision
from ..merger.context_merger import ContextMerger, EvidenceItem, _CONFIDENCE_THRESHOLD

logger: logging.Logger = get_logger(__name__)

_DEFAULT_FETCH_CONCURRENCY: int = 3


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
            method.  When omitted, the real ``EphemeralRAG`` is used (built
            with ``semantic_reranker`` below, if one was given).
        semantic_reranker: An object with a
            ``rank(question, chunks, top_k=...) -> list | None`` method
            (see ``services.rag.SemanticReranker``). Only used when this
            manager builds its own default ``EphemeralRAG`` — ignored if an
            ``ephemeral_rag`` instance is injected directly, since that
            instance owns its own configuration.
        source_ranker: An object with a
            ``rank(evidence, question=...) -> list[EvidenceItem]`` method
            (see ``services.ranking.SourceRanker``). When given, it re-scores
            and trims ``ContextMerger``'s merged evidence before it's
            returned. When ``None`` (the default), the merged evidence is
            returned as-is — unchanged from prior behaviour.
        query_rewriter: An object with a ``rewrite(question) -> str`` method
            (see ``services.query.QueryRewriter``). When given, its output
            is sent to the search provider instead of the raw question.
        domain_filter: An object with a ``filter(urls) -> list[str]`` method
            (see ``services.filtering.DomainQualityFilter``). When given,
            it runs on live-search URLs before ``PageFetcher`` downloads
            them, dropping/reordering by domain quality.
        response_cache: A ``TTLCache``-like object with ``get(key, default)``
            and ``set(key, value)`` methods (see ``shared.cache.TTLCache``).
            When given, it's checked before rewriting a query, calling the
            search provider, or fetching a page, and populated after —
            shared across all three keyspaces via key prefixes.
        fetch_concurrency: Max concurrent page fetches (default 3). Only
            relevant when more than one live-page URL is being downloaded.
        product_router: An object with a ``classify(question) -> ProductMatch``
            method (see ``services.routing.ProductRouter``). When given and
            it identifies one or more products, knowledge-base retrieval is
            scoped to exactly that set via ``product_filter`` (requires
            ``scripts/sql/002_product_knowledge_schema.sql`` to have been
            applied — see that file's docstring). When ``None`` (the
            default) or no product is identified, knowledge retrieval is
            unscoped — unchanged from prior behaviour.
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
        semantic_reranker: Any = None,
        source_ranker: Any = None,
        query_rewriter: Any = None,
        domain_filter: Any = None,
        response_cache: Any = None,
        fetch_concurrency: int = _DEFAULT_FETCH_CONCURRENCY,
        product_router: Any = None,
        live_search_max_results: int = 5,
        live_page_max_fetch: int = 3,
    ) -> None:
        self._source_router = source_router or SourceRouter()
        self._context_merger = context_merger or ContextMerger()
        self._live_search_max_results = live_search_max_results
        self._live_page_max_fetch = live_page_max_fetch
        self._fetch_concurrency = max(1, fetch_concurrency)

        # Lazy-import real services only when needed
        self._knowledge_service: Any = knowledge_service
        self._search_service: Any = search_service
        self._page_fetcher: Any = page_fetcher
        self._ephemeral_rag: Any = ephemeral_rag
        self._semantic_reranker: Any = semantic_reranker
        self._source_ranker: Any = source_ranker
        self._query_rewriter: Any = query_rewriter
        self._domain_filter: Any = domain_filter
        self._response_cache: Any = response_cache
        self._product_router: Any = product_router

        logger.info(
            "SearchManager ready (router=%s, merger=%s, semantic_reranker=%s, source_ranker=%s, "
            "query_rewriter=%s, domain_filter=%s, response_cache=%s, fetch_concurrency=%d, "
            "product_router=%s).",
            type(self._source_router).__name__,
            type(self._context_merger).__name__,
            type(self._semantic_reranker).__name__ if self._semantic_reranker else "None",
            type(self._source_ranker).__name__ if self._source_ranker else "None",
            type(self._query_rewriter).__name__ if self._query_rewriter else "None",
            type(self._domain_filter).__name__ if self._domain_filter else "None",
            type(self._response_cache).__name__ if self._response_cache else "None",
            self._fetch_concurrency,
            type(self._product_router).__name__ if self._product_router else "None",
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
            # Confidence-based routing: if KB results are low-confidence,
            # automatically fall back to live search
            from ..merger.context_merger import ContextMerger
            kb_confidence = ContextMerger.compute_knowledge_confidence(knowledge_evidence)
            logger.info(
                "SearchManager: KB confidence=%.4f (threshold=%.2f).",
                kb_confidence,
                _CONFIDENCE_THRESHOLD,
            )
            if kb_confidence < _CONFIDENCE_THRESHOLD and not actual_decision.web:
                logger.info(
                    "SearchManager: KB confidence %.4f below threshold %.2f — "
                    "triggering live search fallback.",
                    kb_confidence,
                    _CONFIDENCE_THRESHOLD,
                )
                actual_decision = RoutingDecision(knowledge=True, web=True)
                web_search_results = self._retrieve_web_search(question)
                live_page_chunks = self._retrieve_live_pages(question, web_search_results)

        if actual_decision.web:
            web_search_results = self._retrieve_web_search(question)
            live_page_chunks = self._retrieve_live_pages(question, web_search_results)

        # --- Step 3: Enterprise fallback ---
        # If the routing didn't include web search but we have no KB evidence,
        # try web search as a last resort before returning empty.
        if not knowledge_evidence and not web_search_results and not live_page_chunks:
            logger.info(
                "SearchManager: no evidence from any source — attempting live search fallback."
            )
            web_search_results = self._retrieve_web_search(question)
            live_page_chunks = self._retrieve_live_pages(question, web_search_results)

        # --- Step 4: Merge with freshness awareness ---
        evidence = self._context_merger.merge(
            knowledge=knowledge_evidence,
            web_search=web_search_results,
            live_pages=live_page_chunks,
            question=question,
        )

        # --- Step 5: Intelligent source ranking (optional refinement) ---
        if self._source_ranker is not None and evidence:
            try:
                evidence = self._source_ranker.rank(evidence, question=question)
            except Exception as exc:
                logger.error(
                    "SearchManager: source ranking failed — %s. Using merged evidence as-is.",
                    exc,
                    exc_info=True,
                )

        logger.info(
            "SearchManager.retrieve: returning %d evidence items "
            "(knowledge=%s, web=%s, live_pages=%s).",
            len(evidence),
            knowledge_evidence is not None,
            web_search_results is not None,
            live_page_chunks is not None,
        )
        return evidence

    # ------------------------------------------------------------------
    # Per-source retrieval
    # ------------------------------------------------------------------

    def _retrieve_knowledge(self, question: str) -> list[dict[str, Any]] | None:
        """Query the internal knowledge base (Supabase vector search)."""
        try:
            svc = self._get_knowledge_service()
            product_filter = self._classify_product(question)

            if product_filter and len(product_filter) > 1:
                # Multiple products matched (e.g. "compare SPIDIFY and
                # ZivaAIRA") — query each separately and merge, rather than
                # one combined ranked list. A single similarity ranking
                # across products can starve one of them entirely (whichever
                # embeds marginally closer to the question takes every
                # match_count slot); querying per-product guarantees each
                # gets a fair share of the results.
                matches = self._retrieve_knowledge_per_product(svc, question, product_filter)
            else:
                matches, _similarities, _urls = svc.retrieve_context(
                    question, product_filter=product_filter
                )

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

    # Per-product retrieval requests more candidates than the single-source
    # default (3). Short, boilerplate-heavy chunks (nav text, security
    # badges) from one product can look like a near-duplicate of an
    # unrelated short chunk from a *different* product to ContextMerger's
    # bigram dedup pass; a larger candidate pool makes it far more likely
    # at least one substantive, genuinely distinct chunk per product
    # survives that pass.
    _PER_PRODUCT_MATCH_COUNT = 6

    @staticmethod
    def _retrieve_knowledge_per_product(
        svc: Any, question: str, products: list[str]
    ) -> list[dict[str, Any]]:
        """Query each product in *products* separately and concatenate matches."""
        matches: list[dict[str, Any]] = []
        for product in products:
            try:
                product_matches, _similarities, _urls = svc.retrieve_context(
                    question,
                    product_filter=[product],
                    match_count=SearchManager._PER_PRODUCT_MATCH_COUNT,
                )
                matches.extend(SearchManager._dedupe_by_url_prefer_longest(product_matches))
            except Exception as exc:
                logger.warning(
                    "SearchManager: per-product knowledge retrieval failed for %s — %s.",
                    product,
                    exc,
                )
        return matches

    @staticmethod
    def _dedupe_by_url_prefer_longest(
        matches: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Collapse *matches* to one per ``parent_url``, keeping the longest chunk.

        ContextMerger also dedupes by URL, but it keeps whichever chunk has
        the higher similarity score — and a short, boilerplate-heavy chunk
        (nav text, security badges) can score marginally higher than a
        longer, substantive chunk from the same page purely by chance. That
        short survivor then has a much higher risk of tripping ContextMerger's
        bigram near-duplicate check against an unrelated product's equally
        short boilerplate. Doing our own URL dedup first — preferring the
        longest chunk, which best represents the page and is least likely to
        false-positive on bigram overlap — avoids ceding that choice to score
        alone.
        """
        best_by_url: dict[str, dict[str, Any]] = {}
        order: list[str] = []
        no_url: list[dict[str, Any]] = []
        for match in matches:
            url = match.get("parent_url") or ""
            if not url:
                no_url.append(match)
                continue
            existing = best_by_url.get(url)
            if existing is None:
                order.append(url)
                best_by_url[url] = match
            elif len(match.get("chunk_content", "")) > len(existing.get("chunk_content", "")):
                best_by_url[url] = match
        return [best_by_url[url] for url in order] + no_url

    def _classify_product(self, question: str) -> list[str] | None:
        """Return a product filter for *question*, if the router found any match.

        Scopes retrieval to every product the router identified — one for a
        "high" confidence match, several for "ambiguous" (e.g. "compare
        SPIDIFY and ZivaAIRA" names both). Narrowing to the matched set
        rather than only ever narrowing to a single product matters for
        comparison-style questions: an unscoped search has to rank a
        multi-product question's chunks against the *entire* knowledge
        base, which can starve one of the mentioned products of any
        top-`match_count` slot; scoping to just the mentioned products
        removes that competition. Only a question with zero product signal
        (``confidence == "none"``) stays fully unscoped.
        """
        if self._product_router is None:
            return None
        try:
            match = self._product_router.classify(question)
        except Exception as exc:
            logger.warning("SearchManager: product classification failed — %s.", exc)
            return None
        if match.products:
            logger.info(
                "SearchManager: scoping knowledge retrieval to product(s) %s (%s).",
                match.products,
                match.confidence,
            )
            return list(match.products)
        return None

    def _retrieve_web_search(self, question: str) -> list[Any] | None:
        """Perform a live web search."""
        search_query = self._rewrite_query(question)

        cache_key = f"search:{search_query}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            logger.info("SearchManager: web search cache hit for %r.", search_query)
            return cached

        try:
            svc = self._get_search_service()
            results = svc.search(search_query, max_results=self._live_search_max_results)
            if results:
                logger.info(
                    "SearchManager: web search returned %d results.", len(results)
                )
            else:
                logger.info("SearchManager: web search returned no results.")
            # Cache the real (possibly empty) result list — caching only
            # "results or None" would collapse a legitimate "no results for
            # this query" answer into a permanent cache miss, defeating the
            # cache for exactly the queries that are cheapest to remember.
            self._cache_set(cache_key, results)
            return results or None
        except Exception as exc:
            logger.error(
                "SearchManager: web search failed — %s", exc, exc_info=True
            )
            return None

    def _rewrite_query(self, question: str) -> str:
        """Rewrite *question* into a search-engine query, if a rewriter is set."""
        if self._query_rewriter is None:
            return question

        cache_key = f"rewrite:{question}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            rewritten = self._query_rewriter.rewrite(question)
        except Exception as exc:
            logger.warning(
                "SearchManager: query rewriting failed — %s. Using original question.", exc
            )
            return question

        self._cache_set(cache_key, rewritten)
        return rewritten

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

        # Drop/reorder by domain quality before spending a fetch on them
        if self._domain_filter is not None:
            try:
                urls = self._domain_filter.filter(urls)
            except Exception as exc:
                logger.warning(
                    "SearchManager: domain filtering failed — %s. Using unfiltered URLs.", exc
                )

        urls = urls[: self._live_page_max_fetch]
        if not urls:
            logger.info("SearchManager: no URLs survived domain filtering.")
            return None

        pages = self._fetch_pages(urls)
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
    # Page fetching (concurrent, with caching)
    # ------------------------------------------------------------------

    def _fetch_pages(self, urls: list[str]) -> list[str]:
        """Fetch *urls*, concurrently when possible, using the cache first.

        Falls back to sequential fetching if this is called from a thread
        that already has a running asyncio event loop (``asyncio.run()``
        cannot be nested) — degradation, never an error.
        """
        fetcher = self._get_page_fetcher()

        # Serve whatever we can from cache first; only the misses need a
        # network round-trip (concurrent or not).
        to_fetch: list[str] = []
        cached_pages: dict[str, str] = {}
        for url in urls:
            cached = self._cache_get(f"page:{url}")
            if cached is not None:
                cached_pages[url] = cached
            else:
                to_fetch.append(url)

        fetched_pages: dict[str, str] = {}
        if to_fetch:
            if len(to_fetch) == 1 or self._event_loop_already_running():
                fetched_pages = self._fetch_pages_sequential(fetcher, to_fetch)
            else:
                try:
                    fetched_pages = asyncio.run(self._fetch_pages_concurrently(fetcher, to_fetch))
                except RuntimeError:
                    logger.warning(
                        "SearchManager: asyncio.run() unavailable — "
                        "falling back to sequential page fetching."
                    )
                    fetched_pages = self._fetch_pages_sequential(fetcher, to_fetch)

            for url, html in fetched_pages.items():
                self._cache_set(f"page:{url}", html)

        # Preserve the original URL order in the returned page list.
        pages: list[str] = []
        for url in urls:
            if url in cached_pages:
                pages.append(cached_pages[url])
            elif url in fetched_pages:
                pages.append(fetched_pages[url])
        return pages

    @staticmethod
    def _event_loop_already_running() -> bool:
        """True if called from a thread with a running asyncio event loop.

        ``asyncio.run()`` cannot be nested inside a running loop — checking
        this upfront avoids ever constructing (and then abandoning
        un-awaited) the concurrent-fetch coroutine in that case, rather than
        finding out via a caught ``RuntimeError`` after the fact.
        """
        try:
            asyncio.get_running_loop()
            return True
        except RuntimeError:
            return False

    async def _fetch_pages_concurrently(self, fetcher: Any, urls: list[str]) -> dict[str, str]:
        semaphore = asyncio.Semaphore(self._fetch_concurrency)

        async def _fetch_one(url: str) -> tuple[str, str | None]:
            async with semaphore:
                try:
                    html = await asyncio.to_thread(fetcher.fetch, url)
                    logger.info("SearchManager: fetched %d bytes from %s.", len(html), url)
                    return url, html
                except Exception as exc:
                    logger.warning("SearchManager: failed to fetch %s — %s", url, exc)
                    return url, None

        results = await asyncio.gather(*(_fetch_one(url) for url in urls))
        # Only exclude genuine failures (None) — matches the sequential
        # path's behaviour of keeping whatever PageFetcher.fetch() returned.
        return {url: html for url, html in results if html is not None}

    def _fetch_pages_sequential(self, fetcher: Any, urls: list[str]) -> dict[str, str]:
        pages: dict[str, str] = {}
        for url in urls:
            try:
                html = fetcher.fetch(url)
                pages[url] = html
                logger.info("SearchManager: fetched %d bytes from %s.", len(html), url)
            except Exception as exc:
                logger.warning("SearchManager: failed to fetch %s — %s", url, exc)
        return pages

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _cache_get(self, key: str) -> Any:
        if self._response_cache is None:
            return None
        try:
            return self._response_cache.get(key)
        except Exception as exc:
            logger.warning("SearchManager: cache get failed for %r — %s.", key, exc)
            return None

    def _cache_set(self, key: str, value: Any) -> None:
        if self._response_cache is None or value is None:
            return
        try:
            self._response_cache.set(key, value)
        except Exception as exc:
            logger.warning("SearchManager: cache set failed for %r — %s.", key, exc)

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
            self._ephemeral_rag = EphemeralRAG(semantic_reranker=self._semantic_reranker)
        return self._ephemeral_rag