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
    - `deps.py` — (Phase 20) `get_current_user_optional` /
      `get_current_user_required` FastAPI dependencies; decode the
      `Authorization: Bearer` header via `AuthService.get_user()`. Optional
      is used on routes that must keep working anonymously (`/chat`);
      required is used on genuinely protected routes (`/profile`,
      `/conversations`)
    - `schemas.py` — `ChatRequest`/`ChatResponse`, `NextActionSchema`
      (Phase 19 — optional, additive `next_actions` field on
      `ChatResponse`), `SolutionSummary` (Phase 18),
      `DemoRequest`/`DemoRequestResponse` models, and (Phase 20)
      `ChatRequest.session_id`/`conversation_id` (additive, optional),
      `ChatResponse.session_id` (additive, optional), plus
      `SignUpRequest`/`SignInRequest`/`PasswordResetRequest`/
      `AuthSessionResponse`, `CustomerProfileSchema`/`UpdateProfileRequest`,
      `ConversationSummary`/`ConversationDetail`/`ConversationMessageSchema`
    - routes/
      - `chat.py` — `POST /chat` endpoint. Phase 20: resolves the optional
        bearer token to a user (or `None`), builds a short
        company/industry `profile_context` hint for authenticated users
        with a profile on file, forwards `session_id`/`profile_context` to
        `ChatOrchestrator`, and — best-effort, never breaking the
        response — persists the turn via `ConversationService` when the
        caller is authenticated and passed a `conversation_id`
      - `solutions.py` — `GET /solutions` (Phase 18) — the Public Portal's
        catalog, read straight from `PRODUCT_REGISTRY`
      - `demo_request.py` — `POST /demo-request` endpoint (backs every
        "Request a demo"/"Contact sales"/"Talk to an expert" CTA in the
        frontend); returns 503 with a friendly message if the
        `demo_requests` table hasn't been created yet, rather than leaking
        a raw database error. Phase 21: also fires a best-effort
        notification when the requester happens to be signed in
      - `auth.py` — (Phase 20) `POST /auth/sign-up`, `/auth/sign-in`,
        `/auth/sign-out`, `/auth/password-reset`, `GET /auth/me`
      - `profile.py` — (Phase 20) `GET`/`PATCH /profile` (auth required)
      - `conversations.py` — (Phase 20) `GET /conversations` (Phase 21:
        accepts `?search=` — an `ilike` filter on title), `POST
        /conversations`, `GET`/`PATCH`/`DELETE /conversations/{id}` (auth
        required)
      - `saved_items.py` — `GET`/`POST /saved-comparisons`,
        `DELETE /saved-comparisons/{id}`, `GET`/`POST /saved-recommendations`,
        `DELETE /saved-recommendations/{id}` (auth required). Phase 21:
        saving a recommendation also fires a best-effort notification to
        its owner
      - `appointments.py` — `GET /appointments/availability` (public),
        `POST /appointments` (public — records `user_id` when the booker
        happens to be signed in, but never requires it; Phase 21: also
        fires a best-effort notification when the booker is signed in)
      - `feedback.py` — (Phase 21) `POST /chat/feedback` — 👍/👎 + optional
        comment on a chat answer. Public, same precedent as
        `demo_requests`/`appointments`; records `user_id` when the rater
        happens to be signed in
      - `notifications.py` — (Phase 21) `GET /notifications`,
        `GET /notifications/unread-count`,
        `POST /notifications/{id}/read`, `POST /notifications/read-all`
        (auth required)
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
      - `response_generator.py` — generates cited answers from merged
        evidence; accepts optional `primary_product`/`complementary_products`
        (Phase 17, extended Phase 19) to frame the answer as a business
        recommendation
    - advisory/ (Phase 19 — "Intelligent Business Advisor")
      - `intent_engine.py` — `BusinessIntentEngine`/`BusinessIntent`: wraps
        `ProductRouter` (doesn't duplicate its keyword tables) and enriches
        its `ProductMatch` with registry business-problem/category text,
        plus a `named_explicitly` flag distinguishing "Compare X and Y"
        (deliberate) from a need-phrased question that happens to match
        two products' keywords (genuinely ambiguous)
      - `recommendation_engine.py` — `RecommendationEngine`/`Recommendation`:
        ranked, grounded recommendations. Never recommends a product
        outside `PRODUCT_REGISTRY`; confidence is downgraded unless the
        current retrieval evidence actually contains that product's own
        content (checked via `product_metadata_for_url`, no new coupling
        to `ContextMerger`/`EvidenceItem` needed)
      - `clarification_engine.py` — `ClarificationEngine`: asks a
        registry-grounded either/or question instead of guessing, but
        *only* for a genuinely ambiguous two-product keyword match — never
        for a business-theme bundle, an explicitly-named comparison, or a
        comparison phrased via business-problem language ("compare payroll
        and expense management solutions")
      - `next_actions.py` — `NextActionsEngine`/`NextAction`: deterministic
        next-step suggestions (Learn More/Compare/Request Demo/Talk to an
        Expert/Build a Custom Solution/Contact Sales), never hardcoded into
        a response template
      - `advisory_layer.py` — `AdvisoryResponseLayer`/`AdvisoryResult`:
        orchestrates the above for `ChatOrchestrator`; every sub-step is
        failure-isolated (a bug in one stage degrades to "skip that
        enrichment", never breaks the chat response). Optional and purely
        additive — `ChatOrchestrator(advisory_layer=None)` behaves exactly
        as it did before this phase
      - `session_context.py` — `SessionContext`/`SessionState`:
        session-scoped conversation awareness (discussed products,
        recommendations, comparisons, current business problem), built on
        the same `TTLCache` every other in-memory cache in this codebase
        uses. Wired into the live `/chat` endpoint as of Phase 20 via
        `SessionService` (`src/services/session/`) — the pronoun-reference
        resolver now runs for real, e.g. "Tell me about SPIDIFY" then
        "How much does it cost?" resolves "it" to SPIDIFY without a second
        retrieval call
      - `analytics_service.py` — `AnalyticsService`: optional, in-memory,
        anonymous usage counters (recommended/accepted products, compared
        pairs, business problems, demo CTAs, custom-software requests);
        `record_safely()` means a failure here can never break a response
    - auth/ (Phase 20)
      - `auth_service.py` — `AuthService`/`AuthUser`/`AuthSession`/
        `AuthError`: thin wrapper over `supabase-py`'s `client.auth.*`,
        no server-side session state. `sign_out` uses
        `client.auth.admin.sign_out(token, "global")` since the API only
        ever has the caller's bearer token, not a full session with a
        refresh token — non-fatal if the configured Supabase key isn't
        service-role (logs and returns; the frontend clearing its local
        token already achieves sign-out for the user)
    - profile/ (Phase 20)
      - `profile_service.py` — `ProfileService`/`CustomerProfile`: CRUD
        over `customer_profiles`. `get_or_create` handles both the
        DB-trigger-already-created-it case and the trigger-didn't-exist-yet
        case
    - conversation/ (Phase 20)
      - `conversation_repository.py` — `ConversationRepository`: raw
        Supabase access for `conversations`/`conversation_messages`, every
        query explicitly scoped by `user_id` (defense in depth regardless
        of whether the configured key is anon+RLS or service-role).
        `list_conversations` takes an optional `search` (Phase 21 — an
        `ilike` filter on `title`, skipped entirely when not given)
      - `conversation_service.py` — `ConversationService`: conversation
        lifecycle (auto-titling from the first message, `record_turn` for
        persisting a user+assistant pair, ownership-checked reads)
    - session/ (Phase 20)
      - `session_service.py` — `SessionService`: thin adapter
        `ChatOrchestrator` depends on so it doesn't need to know about
        session-id generation or `SessionContext`'s constructor directly;
        every method is a no-op when `session_id` is `None`, so it's safe
        to always inject
    - saved_items/
      - `saved_comparison_service.py` — `SavedComparisonService`: CRUD over
        `saved_comparisons`. Stores only the product-id selection a
        comparison was built from — no comparison rendering logic lives
        here; reopening one just replays those ids through the existing
        `CompareSolutionsModal`
      - `saved_recommendation_service.py` — `SavedRecommendationService`:
        CRUD over `saved_recommendations` (products, the user's question,
        the recommendation text)
    - appointments/
      - `appointment_service.py` — `AppointmentService`: availability is
        *computed*, never stored — each call derives candidate dates from
        "today" forward and subtracts what's booked in `appointments` for
        those dates, which is what gives "availability resets the next
        day" for free (no cron, no explicit reset). `SLOT_TEMPLATE` is the
        one place a real calendar-provider integration would plug in
        later. `book()` pre-checks for a clearer error message, but the
        table's `unique (appointment_date, time_slot)` constraint is the
        actual race guard — `SlotAlreadyBookedError` is raised either way
    - feedback/ (Phase 21)
      - `feedback_service.py` — `FeedbackService`: inserts into
        `message_feedback`. Public — no RLS, no auth required, same
        precedent as `demo_requests`/`appointments`
    - notifications/ (Phase 21)
      - `notification_service.py` — `NotificationService`: `notify`/
        `list_for_user`/`unread_count`/`mark_read`/`mark_all_read` over
        `notifications`. `notify()` is deliberately best-effort (logs and
        returns `None` on failure) since every caller of it is triggering
        a notification as a side effect of some other action (booking,
        saving a recommendation, ...) that must never fail because of it.
        Designed for future realtime support — every caller goes through
        this one class, so swapping polling for a push subscription later
        doesn't touch anything outside it
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

> **Multi-product knowledge base:** `ProductRouter` **is** wired into the
> default `chat_orchestrator` singleton (`product_router=ProductRouter()`
> passed to `SearchManager(...)`), and
> `scripts/sql/002_product_knowledge_schema.sql` has been applied. Product
> identity, aliases, and intent keywords for every product — SPIDIFY,
> ZivaAIRA, and the 11-product HAVIS-360 catalog — live in
> `src/shared/product_registry.py`, the single source of truth `ProductRouter`,
> `SourceRouter`, and `product_metadata.py` all derive from. A product whose
> pages haven't been crawled/uploaded yet (see **Scripts and Utilities**
> below for the ingestion order) simply won't have any chunks to retrieve —
> nothing breaks, the question just falls through to general knowledge/web
> search same as before that product existed.

> **Intelligent Business Advisor (Phase 19):** `AdvisoryResponseLayer`
> (`src/services/advisory/`) **is** wired into the default
> `chat_orchestrator` singleton, sitting between retrieval and generation.
> It can short-circuit with a deterministic clarifying question (zero LLM
> calls) for genuine ambiguity, or drive `ResponseGenerator`'s
> `primary_product`/`complementary_products` framing for *any*
> high-confidence recommendation — not just business-theme matches as in
> Phase 17 — and attaches a `next_actions` list to the API response
> (`ChatResponse.next_actions`, additive/optional — old clients unaffected).
> `AnalyticsService` is wired and records in-memory-only, anonymous usage
> counters alongside every response.

> **Customer Identity Foundation (Phase 20):** 100% additive on top of the
> above — anonymous `/chat` usage is byte-for-byte unchanged when no
> `session_id`/`conversation_id`/bearer token is sent. New, independently
> injectable collaborators: `AuthService`, `ProfileService`,
> `ConversationService` (+ `ConversationRepository`), and `SessionService`
> (the live wiring for Phase 19's previously-unwired `SessionContext`).
> `ChatOrchestrator.chat()` gained two optional keyword args —
> `session_id` (pronoun resolution + session recording) and
> `profile_context` (personalization: a short "Company — Industry" hint
> that only biases business-intent classification, built by lightly
> prefixing the question text handed to the *unmodified* Phase 19 advisory
> engines, since those engines are explicitly out of scope to modify this
> phase). Conversation persistence happens in the `/chat` **route**, not
> the orchestrator, keeping `ChatOrchestrator` free of auth/DB coupling.
> New tables (`customer_profiles`, `conversations`, `conversation_messages`
> — see `scripts/sql/004_customer_identity.sql`) are additive; RLS keyed on
> `auth.uid()` for defense in depth, with every repository query also
> explicitly scoped by `user_id` regardless of which Supabase key is
> configured.

## Scripts and Utilities
- scripts/ — standalone tools, run manually, not imported by the API
  - `__init__.py`
  - `crawl.py` — crawls ha-shem.com via crawl4ai; also exposes a reusable
    `crawl_site(url, max_depth=2)` used by the product crawl scripts below
  - `crawl_spidify.py` / `crawl_zivaaira.py` — crawl SPIDIFY/ZivaAIRA's own
    dedicated product sites (deep-crawled, `max_depth` unset)
  - `crawl_vlogin.py`, `crawl_staas.py`, `crawl_wecare.py`,
    `crawl_havis_xpend.py`, `crawl_havis_vacay.py`, `crawl_havis_ireport.py`,
    `crawl_havis_rema.py`, `crawl_havis_ecertify.py`, `crawl_kwikalert.py`,
    `crawl_appmanage.py`, `crawl_paycheq.py` — each crawls one HAVIS-360
    product's single page on ha-shem.com (`max_depth=0`, no link-following —
    these aren't dedicated multi-page sites like SPIDIFY/ZivaAIRA)
  - `product_metadata.py` — maps a crawled URL to product metadata
    (`product`, `category`, `source_type`) for `upload_vectors.py`; matches
    by domain (SPIDIFY/ZivaAIRA, each on their own domain) or by domain +
    path prefix (the HAVIS-360 catalog, all sharing ha-shem.com). Sources
    its data from `src/shared/product_registry.py` — **that** is the actual
    single source of truth (also used by `ProductRouter`); this module is
    just the URL-matching layer on top of it
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
    - `004_customer_identity.sql` — **not executed by any script or by
      Claude** (same no-DDL-access constraint as 002/003). Additive-only:
      creates `customer_profiles`, `conversations`, `conversation_messages`
      plus RLS policies and a trigger that auto-creates a blank profile row
      on `auth.users` insert. Requires Supabase Auth's built-in `auth.users`
      table, which exists by default in every Supabase project. Run this
      yourself before using any `/auth`, `/profile`, or `/conversations`
      route.
    - `005_saved_items.sql` — **not executed by any script or by Claude**
      (same no-DDL-access constraint). Additive-only: creates
      `saved_comparisons`, `saved_recommendations` (RLS, same `auth.uid()`
      pattern as 004) and `appointments` (no RLS — public booking, same
      precedent as `demo_requests`; a `unique (appointment_date, time_slot)`
      constraint guards against double-booking). Run this yourself before
      using `/saved-comparisons`, `/saved-recommendations`, or
      `/appointments`.
    - `006_feedback_notifications.sql` — **not executed by any script or by
      Claude** (same no-DDL-access constraint). Additive-only: creates
      `message_feedback` (no RLS — public, same precedent as
      `demo_requests`) and `notifications` (RLS, same `auth.uid()` pattern
      as 004/005). Run this yourself before using `/chat/feedback` or
      `/notifications`.

**Multi-solution ingestion order** (13 products: SPIDIFY, ZivaAIRA, and the
11-product HAVIS-360 catalog — V-Login, STAAS, WeCare, Havis Xpend, Havis
Vacay, Havis iReport, Havis REMA, Havis eCertify, KwikAlert, AppManage,
PayCheq), each step manual:
1. Run `scripts/sql/002_product_knowledge_schema.sql` in Supabase (only
   needed once — the `product` column is free-text, so no migration is
   needed when adding new products, only the first time this schema is set up).
2. Run each `python -m scripts.crawl_<product>` script (e.g.
   `scripts.crawl_vlogin`, `scripts.crawl_staas`, ...) — each populates
   `crawled_pages`, same as `crawl.py` does for ha-shem.com.
3. `python -m scripts.test_clean` (cleans all rows in `crawled_pages`,
   including the new solution pages, into `cleaned_output/`).
4. `python -m scripts.upload_vectors` (chunks, embeds, and uploads
   everything in `cleaned_output/` — solution metadata attached automatically).

**Adding product #14 and beyond:** add one entry to
`src/shared/product_registry.py` (`PRODUCT_REGISTRY`) with its URL, domain,
optional path prefix, category, aliases, and intent keywords, then create
one `crawl_<product>.py` script mirroring the pattern above. No changes are
needed to `ProductRouter`, `SourceRouter`, `product_metadata.py`, or any
retrieval code — they all derive their product-specific behavior from the
registry.

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
  - `package.json`, `package-lock.json` — Phase 20 adds `react-router-dom`
  - `postcss.config.js`, `tailwind.config.js` — `ink`/`paper`/`gold` brand
    tokens and the `font-display` (Georgia-based serif) type family
  - `vite.config.ts`
  - `tsconfig.json`, `tsconfig.app.json`, `tsconfig.node.json`
  - public/
    - logo/ (legacy Ha-Shem PNG logo — unused; the HavisIQ mark is now an
      inline SVG component, not a static asset)
  - src/
    - `App.tsx` — main application: hero, solution catalog grid, chat
      widget (client-side typewriter reveal of `/chat` responses, sending a
      persistent `session_id`; an animated three-dot loading state instead
      of a second "thinking" bubble; each real Q&A turn gets `MessageActions`
      — Copy/Regenerate/👍👎 — plus a "Save Recommendation" button when the
      message names a recommended product; a header Export button downloads
      the visible conversation as Markdown), Support Center (real
      `AppointmentScheduler`), and a Sign In / Dashboard header control
    - `solutions.ts` — the solution catalog data (single source of truth
      for the catalog grid, the compare view, and demo-request context)
    - `main.tsx` — (Phase 20) wraps the app in `BrowserRouter` +
      `AuthProvider`; routes: `/` → `App`, `/dashboard` → `DashboardPage`
      behind `ProtectedRoute`
    - `styles.css`
    - `vite-env.d.ts`
    - pages/
      - `DashboardPage.tsx` — authenticated Customer Dashboard, sticky
        sidebar (profile avatar/name/email + nav + unread-notification bell
        badge always visible; only the content area and, within the
        Conversations section, the conversation list itself scroll
        independently): Recent Conversations (debounced search-as-you-type
        via `?search=`, resume/rename/delete, `MessageActions` + Export on
        each turn), New Conversation, Profile, Saved Recommendations
        (expand to read, remove), Saved Comparisons (Open reopens
        `CompareSolutionsModal` preloaded via `initialSelectedIds`, remove),
        and Notifications (real inbox — unread highlighted, mark
        one/all read). Skeleton placeholders (not "Loading..." text) while
        each section's first fetch is in flight
    - lib/
      - `detectProduct.ts`, `parseMessage.ts`, `useSolutions.ts`
      - `apiClient.ts` — (Phase 20) `API_BASE_URL`, stored-token helpers,
        and `apiFetch`/`apiJson` (attach `Authorization: Bearer` when a
        token is stored)
      - `authContext.tsx` — (Phase 20) `AuthProvider`/`useAuth` — sign
        up/in/out/reset against the backend's `/auth/*` routes, persists
        the access token in `localStorage`
      - `sessionId.ts` — (Phase 20) per-tab `session_id`
        (`crypto.randomUUID`, `sessionStorage`) sent with every `/chat`
        request so the backend can resolve pronouns/stay conversation-aware
      - `exportConversation.ts` — (Phase 21) `messagesToMarkdown`/
        `downloadMarkdown` — plain-text Markdown transcript generation and
        a browser download trigger, shared by the floating widget's and
        the Dashboard's Export buttons
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
      - `CompareSolutionsModal.tsx` — side-by-side comparison view of the
        catalog, each card also opening `DemoRequestModal`. Accepts either
        `initialSelectedId` (single, from a catalog card's "Compare"
        button) or `initialSelectedIds` (multiple, used by the dashboard to
        reopen a saved comparison) — the latter takes priority when both
        are given. Shows a "Save Comparison" button once 2+ solutions are
        selected and the visitor is signed in, posting to
        `POST /saved-comparisons`
      - `AppointmentScheduler.tsx` — the Support Center's real booking
        widget: fetches `GET /appointments/availability`, lets the visitor
        pick a date/time and book via `POST /appointments`, disables
        already-booked slots and fully-booked dates, and optimistically
        marks the just-booked slot unavailable before the follow-up
        refetch confirms it — no page refresh needed
      - auth/ (Phase 20)
        - `AuthModal.tsx` — sign in / sign up / password reset, one modal
          with a mode switch (same visual language as `DemoRequestModal`)
        - `ProtectedRoute.tsx` — redirects to `/` if `useAuth().user` is
          `null` once the initial `/auth/me` check resolves
      - message/
        - `MessageContent.tsx` — renders `parseMessage.ts`'s structured
          blocks (headings, paragraphs, KPI stat chips, feature cards,
          checklists, a numbered-step timeline, pricing cards, and
          comparison tables — sticky header + row-hover as of Phase 21) as
          premium components instead of raw Markdown; also renders the
          product header card via `detectProduct.ts`
        - `SourceChips.tsx` — clickable source/citation chips built from
          the API response's `sources` array
        - `MessageActions.tsx` — (Phase 21) Copy / optional Regenerate /
          👍👎 feedback (thumbs-down reveals an optional comment field)
          row, shared verbatim by the floating chat widget and the
          Dashboard's conversation view — one `POST /chat/feedback` call
          site, not two

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
  - `test_auth_service.py` (Phase 20)
  - `test_profile_service.py` (Phase 20)
  - `test_conversation_service.py` (Phase 20)
  - `test_session_service.py` (Phase 20)
  - `test_chat_orchestrator_session.py` (Phase 20 — pronoun resolution,
    session recording, session_id passthrough, personalization)
  - `test_phase20_routes.py` (Phase 20 — `/auth`, `/profile`,
    `/conversations`, and the updated `/chat` contract, end-to-end through
    FastAPI's `TestClient` with `dependency_overrides` faking auth)
  - `test_rls_authenticated_client.py` (Phase 20 — regression coverage for
    a real bug: `ProfileService`/`ConversationRepository` must route
    RLS-protected calls through `get_authenticated_client(access_token)`,
    not the module's own anon-key client, or Postgres rejects the write)
  - `test_saved_items_services.py` — `SavedComparisonService`/
    `SavedRecommendationService`, including the same authenticated-client
    threading as above
  - `test_appointment_service.py` — `AppointmentService`: availability
    derivation, booked-slot/fully-booked-day flagging, the "window
    advances with today" automatic-reset behaviour, and both the
    pre-check and unique-constraint paths for a double-booking
  - `test_saved_items_appointments_routes.py` — `/saved-comparisons`,
    `/saved-recommendations` (auth required), and `/appointments` (public;
    booking still records `user_id` when the caller happens to be signed in)
  - `test_feedback_service.py` (Phase 21) — `FeedbackService`: public
    submission, optional context (user/session/conversation id), both
    rating values
  - `test_notification_service.py` (Phase 21) — `NotificationService`:
    `notify`/`list_for_user`/`unread_count`/`mark_read`/`mark_all_read`,
    the authenticated-client threading, and that a `notify()` failure
    returns `None` instead of raising
  - `test_feedback_notifications_routes.py` (Phase 21) — `/chat/feedback`
    (public, records `user_id` when signed in), `/notifications/*` (auth
    required), and the notification triggers wired into `/appointments`,
    `/saved-recommendations`, and `/demo-request` (each fires only when the
    caller is authenticated)

## Notes
- The backend follows a layered structure: API, orchestrator, services,
  infrastructure, shared utilities, and configuration modules.
- Legacy compatibility modules (`src/chat.py`, `src/sb.py`, `src/chunk.py`,
  `src/intensive_cleaner.py`) remain in place and are actively used by
  `scripts/` and the CLI; they are not dead code.
- Data output directories (`cleaned_output/`, `final_chunks_inspection/`) are
  generated locally by the ingestion scripts and are gitignored — they will
  not exist in a fresh checkout until you run the scripts.
