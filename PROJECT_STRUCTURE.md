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
    - `schemas.py` — `ChatRequest`/`ChatResponse` and `DemoRequest`/`DemoRequestResponse` models
    - routes/
      - `chat.py` — `POST /chat` endpoint
      - `demo_request.py` — `POST /demo-request` endpoint (backs every
        "Request a demo"/"Contact sales"/"Talk to an expert" CTA in the
        frontend); returns 503 with a friendly message if the
        `demo_requests` table hasn't been created yet, rather than leaking
        a raw database error
    - services/
      - `embeddings.py` — Gemini embedding calls
      - `generator.py` — Groq LLM generation
      - `retrieval.py` — vector search & context retrieval
      - `demo_requests.py` — persists demo/contact-sales leads to Supabase
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
      - `product_router.py` — classifies a question against named
        solutions in the catalog (SPIDIFY, ZivaAIRA, and any future
        additions) so knowledge-base retrieval can be scoped to one of
        them; built and unit-tested but **not** wired into the default
        `chat_orchestrator` singleton yet (see note below)
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

> **Multi-product knowledge base (SPIDIFY, ZivaAIRA):** `ProductRouter`
> and the `product_filter` plumbing through `KnowledgeService` /
> `retrieve_context()` / the new `match_documents_by_product` RPC are
> fully built and tested, but **not** wired into the default
> `chat_orchestrator` singleton, and the SQL migration that adds the
> required columns/function (`scripts/sql/002_product_knowledge_schema.sql`)
> has **not** been run against production. Wiring `ProductRouter` in before
> that migration is applied would break knowledge retrieval for the
> now-recognised product questions. See **Scripts and Utilities** below for
> the ingestion order; once the migration is applied and
> `scripts/crawl_spidify.py` / `scripts/crawl_zivaaira.py` have populated
> the knowledge base, pass `product_router=ProductRouter()` to the
> `SearchManager(...)` construction in `chat_orchestrator.py` to go live.

## Scripts and Utilities
- scripts/ — standalone tools, run manually, not imported by the API
  - `__init__.py`
  - `crawl.py` — crawls ha-shem.com via crawl4ai; also exposes a reusable
    `crawl_site(url, max_depth=2)` used by the product crawl scripts below
  - `crawl_spidify.py` — crawls https://havisspidify.com/ into `crawled_pages`
  - `crawl_zivaaira.py` — crawls https://aira.havis360.com/ into `crawled_pages`
  - `product_metadata.py` — maps a crawled URL's domain to product metadata
    (`product`, `category`, `source_type`); single source of truth for the
    SPIDIFY/ZivaAIRA site URLs, used by the crawl scripts and `upload_vectors.py`
  - `chunk_runner.py` — chunks cleaned content
  - `upload_vectors.py` — embeds and uploads chunks to Supabase; attaches
    product metadata automatically via `product_metadata.py` when the
    chunk's source URL matches a known product domain (no-op for
    general ha-shem.com content, so this is a backward-compatible change)
  - `test_clean.py` — exercises `intensive_cleaner`
  - sql/
    - `002_product_knowledge_schema.sql` — **not executed by any script.**
      Adds `product`/`category`/`source_type` columns to
      `documentation_chunks` and a new `match_documents_by_product` RPC
      function (additive — does not touch the existing `match_documents`).
      Run this yourself (e.g. via the Supabase SQL editor) before running
      the solution crawl scripts or wiring `ProductRouter` into
      `chat_orchestrator`. Also includes the `demo_requests` table (see
      003 below — that file is a standalone extract of the same table for
      when you only want demo requests working).
    - `003_demo_requests.sql` — **not executed by any script or by Claude**
      (no DDL access with the credentials in `.env` — only PostgREST via
      `SUPABASE_URL`/`SUPABASE_KEY`, which can't run `CREATE TABLE`). A
      standalone extract of just the `demo_requests` table, independent of
      002. Once this exists, `POST /demo-request` works immediately with
      no code changes.

**Multi-solution ingestion order** (SPIDIFY / ZivaAIRA), each step manual:
1. Run `scripts/sql/002_product_knowledge_schema.sql` in Supabase.
2. `python -m scripts.crawl_spidify` and `python -m scripts.crawl_zivaaira`
   (each populates `crawled_pages`, same as `crawl.py` does for ha-shem.com).
3. `python -m scripts.test_clean` (cleans all rows in `crawled_pages`,
   including the new solution pages, into `cleaned_output/`).
4. `python -m scripts.upload_vectors` (chunks, embeds, and uploads
   everything in `cleaned_output/` — solution metadata attached automatically).

**Demo requests**, independent of the above: run
`scripts/sql/003_demo_requests.sql` in Supabase — `POST /demo-request`
starts working immediately, no other steps needed.

## Frontend
HavisIQ — "AI Solutions Advisor for the Ha-Shem ecosystem." The UI is
organised around a scalable **solution catalog**, not individual products:
SPIDIFY and ZivaAIRA are the first two entries (`status: 'live'`, each with
its own knowledge base and site), alongside advisory categories
(cybersecurity, cloud services, software development, managed services,
training) that Ha-Shem already delivers on without a dedicated product yet
(`status: 'advisory'`). Adding a new solution — including promoting an
advisory category to "live" once it has its own site — is a one-line
addition to `src/solutions.ts`; no other file needs to change.

- frontend/
  - `index.html`
  - `package.json`, `package-lock.json`
  - `postcss.config.js`, `tailwind.config.js` — `ink`/`paper`/`gold` brand
    tokens and the `font-display` (Georgia-based serif) type family
  - `vite.config.ts`
  - `tsconfig.json`, `tsconfig.app.json`, `tsconfig.node.json`
  - public/
    - logo/ (legacy Ha-Shem PNG logo — unused; the HavisIQ mark is now an
      inline SVG component, not a static asset)
  - src/
    - `App.tsx` — main application: hero, solution catalog grid, chat
      widget (client-side typewriter reveal of `/chat` responses),
      support/appointment sections
    - `solutions.ts` — the solution catalog data (single source of truth
      for the catalog grid, the compare view, and demo-request context)
    - `main.tsx`
    - `styles.css`
    - `vite-env.d.ts`
    - components/
      - `HavisIQMark.tsx` — the brand mark (H monogram, broken crossbar,
        gold node). Colors are set inline, not via Tailwind utility
        classes — this is a small, fixed-identity element that must never
        depend on the Tailwind build picking up a config change
      - `DemoRequestModal.tsx` — the shared form behind every "Request a
        demo"/"Contact sales"/"Talk to an expert" CTA; posts to
        `POST /demo-request`, pre-fills solution context when opened from
        a specific catalog card, and shows a friendly inline error (not a
        raw fetch failure) if the backend returns one
      - `CompareSolutionsModal.tsx` — read-only side-by-side view of the
        full catalog, each card also opening `DemoRequestModal`

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
  - `test_product_router.py`
  - `test_product_metadata.py`
  - `test_retrieval.py`
  - `test_knowledge_service.py`
  - `test_demo_requests.py`
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
