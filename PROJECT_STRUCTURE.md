# Project Structure

## Repository Root
- .env (create locally; not committed)
- .gitignore
- requirements.txt
- README.md
- PROJECT_STRUCTURE.md
- Ha-Shem_AI_Support_Platform_Architecture.md (aspirational roadmap — see note in file)
- rules.md (engineering spec behind the multi-source retrieval pipeline)
- .agents/mcp_config.json (sample MCP client config)

## Application Source
- src/
  - `__init__.py`
  - `chat.py` — module entry point (`python -m src.chat`)
  - `chat_cli.py` — interactive CLI wrapping the knowledge base
  - `chunk.py` — semantic chunking helper used by ingestion scripts
  - `intensive_cleaner.py` — markdown/content cleaning helper used by ingestion scripts
  - `sb.py` — Supabase client accessor
  - api/
    - `app.py` — FastAPI app setup, CORS, router registration
    - `schemas.py` — `ChatRequest` / `ChatResponse` models
    - routes/
      - `chat.py` — `POST /chat` endpoint
    - services/
      - `embeddings.py` — Gemini embedding calls
      - `generator.py` — Groq LLM generation
      - `retrieval.py` — vector search & context retrieval
  - config/
    - `settings.py` — `Settings` dataclass (env-driven configuration)
  - infrastructure/
    - database/
      - `supabase.py` — Supabase client + `match_documents` RPC call
  - mcp/
    - `server.py` — MCP server exposing knowledge base / live-search tools
    - tools/
      - `live_search.py`
  - orchestrator/
    - `chat_orchestrator.py` — coordinates the chat request flow; runs the
      legacy KB-only path by default (see note below)
  - services/
    - documents/
      - `document_service.py`
    - knowledge/
      - `knowledge_service.py`
    - support/
      - `support_service.py`
    - routing/
      - `source_router.py` — keyword-based KB-vs-web routing decision
    - manager/
      - `search_manager.py` — executes routing decisions across retrievers
    - merger/
      - `context_merger.py` — dedupes/ranks evidence from multiple sources
    - retrievers/
      - `page_fetcher.py`, `exceptions.py`
      - `ssl_chain_repair.py` — repairs incomplete TLS certificate chains
        (missing intermediate CA) via AIA chasing, without disabling
        verification; used automatically by `PageFetcher`
    - search/
      - `search_service.py`, `models.py`
      - providers/
        - `base.py`, `tavily.py`, `brave.py`
    - rag/
      - `ephemeral_rag.py` — ranks text chunks extracted from freshly
        fetched live pages against the question. Lexical word-overlap by
        default; if a `semantic_reranker` is injected, the top lexical
        candidates are re-scored by embedding cosine similarity, falling
        back to lexical ranking if that fails
      - `semantic_reranker.py` — embedding-based (Gemini) cosine-similarity
        reranking of a text shortlist; returns `None` on any failure
        (missing credentials, network error) so callers can fall back
    - ranking/
      - `source_ranker.py` — re-scores and trims `ContextMerger`'s merged
        evidence using relevance, source-authority tier (official site >
        docs > trusted news > social media), freshness, and a near-duplicate
        penalty; optional, injected into `SearchManager`
    - query/
      - `query_rewriter.py` — deterministic (no LLM) rewriting of a
        question into a concise search-engine query: strips filler words,
        canonicalises the configured company name, appends a freshness
        date token and a `site:` hint when relevant. Falls back to the
        original question on any error
    - filtering/
      - `domain_filter.py` — drops low-quality domains (generic
        dictionaries, Quora, etc.) and prioritises the rest by the same
        authority tier as `SourceRanker`, *before* `PageFetcher` downloads
        anything
    - validation/
      - `citation_validator.py` — removes duplicate and placeholder-URL
        (`"Unknown URL"`) citations from `ResponseGenerator`'s output;
        never touches the LLM's answer text, only the returned
        citations/sources metadata
    - generator/
      - `response_generator.py` — generates cited answers from merged evidence
  - shared/
    - `logging.py`
    - `cache.py` — `TTLCache`, a generic thread-safe time-to-live cache
      used for `SearchManager`'s response cache (rewritten queries, search
      results, fetched pages) and `SemanticReranker`'s embedding cache
    - `domain_classifier.py` — shared domain-authority/quality tier
      classification (official / vendor docs / trusted news / social
      media / low-quality), used by both `SourceRanker` and
      `DomainQualityFilter` so the tier lists exist in exactly one place

> **Note:** The `routing/`, `manager/`, `merger/`, `search/`, `retrievers/`,
> `rag/`, `ranking/`, `query/`, `filtering/`, `validation/`, and
> `generator/` packages implement a multi-source (knowledge base + live
> web) retrieval pipeline with several optional quality and performance
> refinements — query rewriting, domain-quality filtering, semantic
> reranking of live-page chunks, intelligent source ranking, citation
> validation, concurrent page fetching, and TTL-based response/embedding
> caching — and it **is** injected into the module-level `chat_orchestrator`
> singleton used by the API and CLI. Each question is routed to the
> knowledge base, live web search, or both; if no search provider key is
> configured, web search calls fail individually per-request and the
> pipeline falls back to knowledge-base-only evidence rather than erroring
> out. Every refinement stage degrades gracefully on its own failure
> (falls back to lexical ranking, unranked/unfiltered evidence, the
> original question, sequential fetching, etc.) rather than breaking the
> response. `BackgroundLearning` (fire-and-forget ingestion of new URLs
> after a web-sourced answer) remains referenced by type but unimplemented
> — it stays inert (`background_learning=None`) until a real
> implementation is added.

## Scripts and Utilities
- scripts/ — standalone tools, run manually, not imported by the API
  - `__init__.py`
  - `crawl.py` — crawls ha-shem.com via crawl4ai
  - `chunk_runner.py` — chunks cleaned content
  - `upload_vectors.py` — embeds and uploads chunks to Supabase
  - `test_clean.py` — exercises `intensive_cleaner`

## Frontend
- frontend/
  - `index.html`
  - `package.json`, `package-lock.json`
  - `postcss.config.js`, `tailwind.config.js`
  - `vite.config.ts`
  - `tsconfig.json`, `tsconfig.app.json`, `tsconfig.node.json`
  - public/
    - logo/
  - src/
    - `App.tsx` — main chat application (includes client-side typewriter
      reveal of responses)
    - `main.tsx`
    - `styles.css`
    - `vite-env.d.ts`

## Tests
- tests/
  - `test_chat_refactor.py`
  - `test_routing.py`
  - `test_search_manager.py`
  - `test_search_service.py`
  - `test_context_merger.py`
  - `test_response_generator.py`
  - `test_page_fetcher.py`
  - `test_ssl_chain_repair.py`
  - `test_ephemeral_rag.py`
  - `test_semantic_reranker.py`
  - `test_source_ranker.py`
  - `test_query_rewriter.py`
  - `test_domain_filter.py`
  - `test_citation_validator.py`
  - `test_cache.py`
  - `test_mcp_server.py`

## Notes
- The backend follows a layered structure: API, orchestrator, services,
  infrastructure, shared utilities, and configuration modules.
- Legacy compatibility modules (`src/chat.py`, `src/sb.py`, `src/chunk.py`,
  `src/intensive_cleaner.py`) remain in place and are actively used by
  `scripts/` and the CLI; they are not dead code.
- Data output directories (`cleaned_output/`, `final_chunks_inspection/`) are
  generated locally by the ingestion scripts and are gitignored — they will
  not exist in a fresh checkout until you run the scripts.
