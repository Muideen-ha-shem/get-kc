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
    - search/
      - `search_service.py`, `models.py`
      - providers/
        - `base.py`, `tavily.py`, `brave.py`
    - rag/
      - `ephemeral_rag.py` — ranks text chunks extracted from freshly
        fetched live pages against the question (lexical overlap, no
        embedding calls); used by `SearchManager` for the live-web path
    - generator/
      - `response_generator.py` — generates cited answers from merged evidence
  - shared/
    - `logging.py`

> **Note:** The `routing/`, `manager/`, `merger/`, `search/`, `retrievers/`,
> `rag/`, and `generator/` packages implement a multi-source (knowledge base +
> live web) retrieval pipeline, and it **is** injected into the module-level
> `chat_orchestrator` singleton used by the API and CLI. Each question is
> routed to the knowledge base, live web search, or both; if no search
> provider key is configured, web search calls fail individually per-request
> and the pipeline falls back to knowledge-base-only evidence rather than
> erroring out. `BackgroundLearning` (fire-and-forget ingestion of new URLs
> after a web-sourced answer) remains referenced by type but unimplemented —
> it stays inert (`background_learning=None`) until a real implementation is
> added.

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
