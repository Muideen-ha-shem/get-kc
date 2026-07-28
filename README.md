# HavisIQ — Ha-Shem AI Business Solutions Platform

HavisIQ is the AI Solutions Advisor for the whole Ha-Shem ecosystem — not a chatbot for a single product. Ask it about a business need (identity verification, recruitment, cybersecurity, cloud, software development, managed services, training) and it matches you to the right Ha-Shem solution, grounded in Retrieval-Augmented Generation (RAG) with cited sources. SPIDIFY and ZivaAIRA are the first two entries in a growing solution catalog (`frontend/src/solutions.ts`), not the platform's focus. Built with a React/TypeScript frontend and Python FastAPI backend.

---

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
	- [Linux Setup](#linux-setup)
	- [Windows Setup](#windows-setup)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Usage](#usage)
- [Project Structure](#project-structure)

---

## 🧱 Project Structure Overview

The project has been reorganized into a clearer runtime and utility layout:

```text
project/
├── frontend/                # React + TypeScript UI
├── scripts/                 # standalone data and crawl utilities
├── src/
│   ├── api/                 # FastAPI routes, schemas, and service adapters
│   ├── infrastructure/      # external integrations such as Supabase
│   ├── mcp/                 # Model Context Protocol server (agent/IDE tooling)
│   ├── orchestrator/        # request coordination for the chat flow
│   ├── services/            # business services for knowledge, search, and support
│   └── ...                  # existing runtime modules kept for compatibility
├── tests/                   # regression and validation tests
└── *.md                     # documentation and architecture notes (repo root)
```

Standalone scripts such as crawl, chunking, vector upload, and cleaning utilities now live under the scripts directory rather than inside the production source tree.

> **Note:** `src/services/` also contains a multi-source retrieval pipeline — source
> routing, query rewriting, live web search, domain-quality filtering, in-memory page
> RAG, semantic reranking, intelligent source ranking, citation validation, and
> context merging — and it **is** wired into the default `chat_orchestrator` instance
> used by the API and CLI. Each question is routed to the knowledge base, live web
> search, or both; if `TAVILY_API_KEY`/`BRAVE_SEARCH_API_KEY` are unset, web search
> calls simply fail individually and the pipeline degrades gracefully to
> knowledge-base-only answers. Live-page downloads run concurrently, and search
> results/fetched pages/embeddings are cached in-memory for the process's uptime —
> see [Retrieval Quality & Performance](#-retrieval-quality--performance) below.

> **Multi-solution knowledge base (SPIDIFY, ZivaAIRA):** `ProductRouter`
> (question → solution classification) and solution-scoped retrieval are built
> and tested but **not yet live** — they require a one-time SQL migration and
> a crawl/ingestion run that haven't been executed against production. See
> `PROJECT_STRUCTURE.md`'s "Multi-solution ingestion order" for the exact
> steps and current status.
>
> **Demo requests:** `POST /demo-request` backs every "Request a demo" /
> "Contact sales" / "Talk to an expert" button in the frontend, but the
> `demo_requests` Supabase table doesn't exist yet either — submissions
> currently return a clean `503` with a friendly message rather than a raw
> error. Run `scripts/sql/003_demo_requests.sql` to activate it; no code
> changes needed once that table exists.

---

## ✨ Features

### 🤖 Intelligent Chat Interface
- **Typewriter-Style Response Reveal**: The frontend reveals each answer character-by-character for a live-typing feel (the backend returns the full answer in a single response; this effect is applied client-side)
- **Markdown Formatting**: Automatically converts markdown bold (`**text**`) to properly styled text
- **Source Attribution**: Each answer includes clickable links to the knowledge base sources
- **Context-Aware Responses**: Uses RAG to ground all answers in your company's knowledge base

### 📚 Knowledge Management
- **Vector Embeddings**: Questions converted to embeddings via Google Gemini API
- **Semantic Search**: Supabase vector database finds the most relevant content chunks
- **Grounded Answers**: Groq API generates responses based only on provided context
- **Multi-Source Support**: Aggregates information from multiple knowledge base sources

### 💼 Professional UX
- **Responsive Design**: Beautiful, modern interface built with React, TypeScript, and Tailwind CSS
- **Smooth Animations**: Framer Motion brings the interface to life
- **Mobile-Friendly**: Fully responsive chat interface for all device sizes
- **Suggested Actions**: Quick-access buttons for common queries

### 🔐 Security & Performance
- **CORS Support**: Secure cross-origin communication
- **API Rate Limiting**: Efficient request handling
- **Error Handling**: Graceful fallbacks for unavailable services

### 👤 Customer Accounts (Phase 20)

Fully additive on top of the existing anonymous experience — nothing below
changes how an anonymous visitor uses HavisIQ; it only unlocks extra features
once a visitor signs in.

- **Supabase Authentication**: Sign up, sign in, sign out, password reset, and
  email verification via Supabase Auth (`src/services/auth/auth_service.py`).
  Google/Microsoft OAuth can be added later purely as new `AuthService`
  methods — no architectural change required.
- **Customer Profile**: A lightweight profile (company, industry, phone —
  *not* AI memory) that authenticated users can view/edit from the dashboard.
- **Session-Aware Conversations**: Every `/chat` request can carry a
  client-generated `session_id`; the backend resolves bare pronouns ("How much
  does *it* cost?") against the last-discussed product before retrieval, with
  zero extra retrieval calls, and remembers discussed/recommended/compared
  products for the life of the session.
- **Conversation Persistence & History**: Authenticated users can save, list,
  resume, rename, and delete conversations from the Customer Dashboard — a
  ChatGPT/Claude-like experience, but business-focused. Persistence happens
  behind the existing `/chat` contract; the endpoint's request/response shape
  only gained optional fields (`session_id`, `conversation_id`).
- **Personalized Recommendations**: Authenticated users with a company/industry
  on file get business-intent classification biased toward relevant products
  (e.g. a Financial Services company asking about "customer onboarding" is
  steered toward SPIDIFY without extra clarifying questions) — implemented by
  lightly annotating the question text handed to the (unmodified) advisory
  engines, not by changing their logic.
- **Customer Dashboard**: `/dashboard` (React Router, auth-protected) with
  Recent Conversations, Continue/New Conversation, Profile, Saved
  Recommendations, Saved Comparisons, and a Notifications placeholder.

### ⭐ Saved Comparisons & Recommendations

- **Save Comparison**: A "Save Comparison" button inside `CompareSolutionsModal`
  (visible once 2+ solutions are selected and the visitor is signed in) persists
  the selected product ids to `saved_comparisons`. "Open" from the dashboard's
  Saved Comparisons list reopens the *same* modal component with that selection
  preloaded — no separate comparison view exists.
- **Save Recommendation**: Whenever HavisIQ's chat widget names a recommended
  product (via the existing product-header detection or a `next_actions`
  target), a "Save Recommendation" button appears under that message for
  signed-in visitors, persisting the question + recommendation text to
  `saved_recommendations` — a personal recommendation library, viewable/
  removable from the dashboard.

### 📅 Appointment Scheduling

Real booking logic behind the Support Center's "Book a strategy session"
widget — `GET /appointments/availability` derives open slots for the next few
calendar days directly from today's date plus whatever's already booked, so a
day rolling out of that forward-looking window is what makes "availability
resets the next day" true, with no cron job or explicit reset step anywhere.
`POST /appointments` books a slot (public — no sign-in required, same as demo
requests); a `unique (appointment_date, time_slot)` database constraint is the
real guard against two people booking the same slot at once, not just the
pre-check the API also does.

### 🎯 Retrieval Quality & Performance

All of the following are optional pipeline refinements — each degrades gracefully
to prior behaviour on its own failure (see [Project Structure Overview](#-project-structure-overview)
for exactly where each one sits in the pipeline):

- **Query Rewriting**: Deterministic (no LLM) rewriting of natural-language questions
  into concise search-engine queries — strips filler words, canonicalises the
  company name, adds a freshness date token and a `site:` hint when relevant
- **Domain-Quality Filtering**: Drops low-quality domains (generic dictionaries,
  Quora, etc.) and prioritises official/documentation/news sources before any page
  is fetched
- **Semantic Reranking**: Embedding-based (Gemini) cosine-similarity reranking of
  live-page chunks, falling back to lexical word-overlap ranking if embeddings are
  unavailable
- **Intelligent Source Ranking**: Multi-signal ranking of merged evidence —
  relevance, source authority, freshness, near-duplicate penalty
- **Citation Validation**: Removes duplicate and placeholder-URL (`"Unknown URL"`)
  citations before they reach the API response
- **Concurrent Page Fetching**: Live pages download in parallel (bounded by a
  configurable concurrency limit) instead of one at a time
- **Response & Embedding Caching**: In-memory TTL caches for rewritten queries,
  search results, fetched pages, and embeddings, so repeated questions within the
  cache window skip redundant network/API calls

---

## 🏗️ Architecture

```
Ha-Shem AI Support Platform
├── Backend (FastAPI)
│   ├── Vector Embedding (Google Gemini)
│   ├── Vector Database (Supabase PostgreSQL + pgvector)
│   ├── LLM Generation (Groq API)
│   └── Context Retrieval Engine
└── Frontend (React + TypeScript + Vite)
		├── Real-time Chat UI
		├── Message Streaming
		├── Source Attribution
		└── Responsive Design
```

**Data Flow**:
1. User asks a question → Frontend sends to backend
2. Backend converts question to embedding (Google Gemini)
3. Supabase vector search finds relevant knowledge chunks
4. Groq generates a grounded response using context
5. Response streams back with source links

### Authentication Architecture (Phase 20)

```
Frontend (React)
  └── AuthProvider (src/lib/authContext.tsx)
        stores access_token in localStorage, attaches "Authorization: Bearer <token>"
        to every request via apiFetch()

Backend (FastAPI)
  ├── POST /auth/sign-up, /auth/sign-in, /auth/sign-out, /auth/password-reset, GET /auth/me
  │     └── AuthService (src/services/auth/auth_service.py) — thin wrapper over
  │         supabase-py's client.auth.* — no session state kept server-side.
  ├── get_current_user_optional / get_current_user_required (src/api/deps.py)
  │     └── FastAPI dependencies that decode the bearer token via AuthService.get_user().
  │         Optional everywhere anonymous access must keep working (e.g. /chat);
  │         required only on genuinely protected routes (/profile, /conversations).
  └── ProfileService (src/services/profile/profile_service.py)
        └── customer_profiles table, auto-created on first sign-in (or via a
            DB trigger on auth.users insert — see the migration).
```

Supabase's built-in `auth.users` table is the source of truth for
credentials; everything else (`customer_profiles`, `conversations`,
`conversation_messages`) references it by `auth_user_id` / `user_id` and is
protected by Row Level Security policies keyed on `auth.uid()`.

### SessionContext Flow (Phase 20)

```
Frontend generates a session_id (crypto.randomUUID, sessionStorage) once per
tab and sends it with every /chat call.

ChatOrchestrator.chat(message, session_id=...)
  1. SessionService.resolve_reference(session_id, message)
       rewrites a bare pronoun ("it"/"this"/"that") to the last product
       discussed in that session — BEFORE the single retrieval call, so no
       extra retrieval round-trip is needed.
  2. ... normal retrieval + advisory pipeline, unchanged ...
  3. SessionService records this turn's discussed/recommended/compared
     products and business problem back into the session (30-minute TTL,
     in-memory only — no DB row).
```

`SessionContext` itself (`src/services/advisory/session_context.py`) is
unchanged from Phase 19; Phase 20 only wires it into the live request path via
the new `SessionService` adapter (`src/services/session/session_service.py`).

### Conversation Lifecycle (Phase 20)

```
POST /conversations                 -> create a conversation (optionally titled
                                        from the first message)
POST /chat {conversation_id: "..."} -> persists the user+assistant turn into
                                        conversation_messages behind the
                                        existing /chat contract (best-effort;
                                        a persistence failure never breaks the
                                        chat response itself)
GET  /conversations                 -> list, newest first
GET  /conversations/{id}            -> full message history to resume in the UI
PATCH /conversations/{id}           -> rename
DELETE /conversations/{id}          -> delete (cascades to its messages)
```

### Dashboard Architecture (Phase 20)

`frontend/src/pages/DashboardPage.tsx`, mounted at `/dashboard` behind
`ProtectedRoute` (redirects anonymous visitors to `/`). Sections: Recent
Conversations (with inline resume/rename/delete), Continue/New Conversation,
Profile (reads/writes `GET`/`PATCH /profile`), and placeholders for Saved
Recommendations, Saved Comparisons, and Notifications — reserved for a future
phase once those concepts have a backend home.

### Database Schema (Phase 20 additions)

See `scripts/sql/004_customer_identity.sql` for the full migration (additive
only — no existing table is modified):

- **`customer_profiles`**: `id`, `auth_user_id` (unique, → `auth.users`),
  `email`, `full_name`, `company_name`, `industry`, `phone`, `created_at`,
  `updated_at`, `last_login`. RLS: a user can only read/insert/update their
  own row.
- **`conversations`**: `id`, `user_id` (→ `auth.users`), `title`,
  `created_at`, `updated_at`. RLS: a user can only see/modify their own rows.
- **`conversation_messages`**: `id`, `conversation_id` (→ `conversations`),
  `role` (`user`/`assistant`), `content`, `citations` (jsonb), `metadata`
  (jsonb), `created_at`. RLS: ownership checked via the parent conversation's
  `user_id` (a message has no `user_id` column of its own).

### Database Schema (Saved Comparisons / Recommendations / Appointments)

See `scripts/sql/005_saved_items.sql` for the full migration (additive only):

- **`saved_comparisons`**: `id`, `user_id` (→ `auth.users`), `product_ids`
  (jsonb array), `created_at`. RLS: own rows only — same `auth.uid()` pattern
  as `conversations`.
- **`saved_recommendations`**: `id`, `user_id` (→ `auth.users`), `products`
  (jsonb array), `question`, `recommendation`, `created_at`. RLS: own rows only.
- **`appointments`**: `id`, `user_id` (nullable → `auth.users`), `name`,
  `email`, `appointment_date`, `time_slot`, `status`, `created_at`,
  `unique (appointment_date, time_slot)`. **No RLS** — booking is a public
  action, same precedent as `demo_requests`; the unique constraint (not a
  policy) is what prevents a double-booking race.

---

## 📋 Prerequisites

### Required
- **Python 3.9+** (for backend)
- **Node.js 16+** (for frontend)
- **Git**

### API Keys Needed (Free or Paid)
- **Groq API Key** - for LLM generation ([https://console.groq.com](https://console.groq.com))
- **Google Gemini API Key** - for embeddings ([https://ai.google.dev](https://ai.google.dev))
- **Supabase Account** - for vector database ([https://supabase.com](https://supabase.com))

---

## 🚀 Installation & Setup

### Linux Setup

#### Step 1: Clone the Repository

```bash
# Navigate to your desired directory
cd ~/Desktop  # or any preferred location

# Clone the repository
git clone https://github.com/Muideen-ha-shem/get-kc.git
cd get-kc
```

#### Step 2: Set Up Python Backend

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
pip install -r requirements.txt
```

#### Step 3: Configure Environment Variables

```bash
# Create a .env file in the root directory
cat > .env << 'EOF'
# Groq API Configuration
GROQ_API_KEY=your_groq_api_key_here

# Google Gemini API Configuration
GOOGLE_API_KEY=your_google_gemini_api_key_here

# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
EOF

# Edit the file and add your actual API keys
nano .env  # or use your preferred editor
```

#### Step 4: Set Up Node.js Frontend

```bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Set up frontend environment (optional, auto-detects backend)
# Default backend: http://127.0.0.1:8000
```

#### Step 5: Run the Application

**Terminal 1 - Start Backend:**
```bash
# From project root with venv activated
python -m src.api.app  # if using module execution

# OR directly run uvicorn
uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 - Start Frontend:**
```bash
cd frontend
npm run dev
```

**Access the Application:**
- Frontend: `http://localhost:5173`
- API Health Check: `http://localhost:8000/health`

---

### Windows Setup

#### Step 1: Clone the Repository

```cmd
# Open Command Prompt or PowerShell
# Navigate to your desired directory
cd Desktop  # or any preferred location

# Clone the repository
git clone https://github.com/Muideen-ha-shem/get-kc.git
cd get-kc
```

#### Step 2: Set Up Python Backend

```cmd
# Create a virtual environment
python -m venv venv

# Activate the virtual environment (Command Prompt)
venv\Scripts\activate

# OR if using PowerShell
# venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install Python dependencies
pip install -r requirements.txt
```

#### Step 3: Configure Environment Variables

**Option A: Using Command Prompt**
```cmd
# Create a .env file
echo. > .env

# Edit with Notepad (add the variables below)
notepad .env
```

**Option B: Using PowerShell**
```powershell
# Create a .env file with content
@"
GROQ_API_KEY=your_groq_api_key_here
GOOGLE_API_KEY=your_google_gemini_api_key_here
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
"@ | Out-File -FilePath .env -Encoding UTF8
```

**Add to .env file:**
```
GROQ_API_KEY=your_groq_api_key_here
GOOGLE_API_KEY=your_google_gemini_api_key_here
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
```

#### Step 4: Set Up Node.js Frontend

```cmd
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install
```

#### Step 5: Run the Application

**Terminal 1 - Start Backend:**
```cmd
# Make sure venv is activated
venv\Scripts\activate

# Start the FastAPI server
uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 - Start Frontend:**
```cmd
cd frontend
npm run dev
```

**Access the Application:**
- Frontend: `http://localhost:5173`
- API Health Check: `http://localhost:8000/health`

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GROQ_API_KEY` | API key for Groq LLM service | `gsk_xxxxx` |
| `GOOGLE_API_KEY` | API key for Google Gemini embeddings | `AIzaxxxxx` |
| `SUPABASE_URL` | Supabase project URL | `https://xxxxx.supabase.co` |
| `SUPABASE_KEY` | Supabase anonymous key | `eyJhbGc...` |
| `TAVILY_API_KEY` *(optional)* | Live web search provider used by the `/chat` flow's multi-source retrieval (`SourceRouter` → `SearchManager`) and the MCP server's `live_web_search` tool. Without it (and without `BRAVE_SEARCH_API_KEY`), the chat flow falls back to knowledge-base-only answers. | `tvly-xxxxx` |
| `BRAVE_SEARCH_API_KEY` *(optional)* | Fallback live web search provider, used if `TAVILY_API_KEY` is unset. Same scope as above. | `BSA-xxxxx` |
| `OFFICIAL_DOMAINS` *(optional)* | Comma-separated domains `SourceRanker` and `DomainQualityFilter` treat as this deployment's own "official website" authority tier (ranked above generic web results); also used by `QueryRewriter` as its default `site:` hint domain. | `ha-shem.com,ha-shemacademy.com` |
| `COMPANY_NAME` *(optional)* | Short company name `QueryRewriter` detects in questions (case-insensitive) to trigger name canonicalisation and the `site:` hint. | `ha-shem` |
| `COMPANY_FULL_NAME` *(optional)* | Canonical company name `QueryRewriter` substitutes in when `COMPANY_NAME` is detected. | `Ha-Shem Limited` |

> Backend host/port are **not** read from environment variables — set them via the
> `--host`/`--port` flags on the `uvicorn` command shown below.

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Server health check |
| `/chat` | POST | Send a message and get AI response |
| `/demo-request` | POST | Submit a "Request a demo" / "Contact sales" / "Talk to an expert" lead |

**Chat Request Format:**
```json
{
	"message": "What are Ha-Shem's core services?"
}
```

**Chat Response Format:**
```json
{
	"answer": "Ha-Shem provides enterprise AI solutions including **support automation**, **cloud services**, and **business process automation**.",
	"sources": [
		"https://ha-shem.com/about-us",
		"https://ha-shem.com/services"
	]
}
```

**Demo Request Format:**
```json
{
	"name": "Ada Lovelace",
	"email": "ada@example.com",
	"company": "Acme Ltd",
	"use_case": "Identity verification for customer onboarding",
	"product": "SPIDIFY"
}
```
`company`, `use_case`, and `product` are optional. Returns `503` with a
friendly message until `scripts/sql/003_demo_requests.sql` has been run
(see the note above) — this is expected until that migration is applied,
not a bug.

---

## 🎯 Running the Application

### Quick Start (After Initial Setup)

**Linux:**
```bash
# Terminal 1
source venv/bin/activate
uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2
cd frontend && npm run dev
```

**Windows:**
```cmd
REM Terminal 1
venv\Scripts\activate
uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --reload

REM Terminal 2
cd frontend && npm run dev
```

### Production Build

```bash
# Frontend build
cd frontend
npm run build
# Output in frontend/dist/

# Backend deployment (use production ASGI server)
pip install gunicorn
gunicorn src.api.app:app
```

---

## 💬 Usage

### Chat Interface Features

1. **Ask Questions**: Type any question about Ha-Shem's services, products, or company info
2. **View Streaming Responses**: Watch the AI assistant respond in real-time
3. **Access Sources**: Click on source links below each answer to verify information
4. **Use Quick Actions**: Click suggested prompts for common queries
5. **Format Support**: Answers automatically bold important terms using `**text**`

### Example Queries

- "Tell me about Ha-Shem Limited"
- "What products do you offer?"
- "How can I schedule a demo?"
- "What are your support options?"
- "Explore cloud services"

---

## 📁 Project Structure

```
get-kc/
├── README.md                          # Documentation
├── PROJECT_STRUCTURE.md               # Detailed file/directory reference
├── requirements.txt                   # Python dependencies
├── .env                               # Environment variables (create this)
│
├── src/                                # Backend source code
│   ├── api/
│   │   ├── app.py                     # FastAPI application setup
│   │   ├── schemas.py                 # Request/response schemas
│   │   ├── routes/
│   │   │   └── chat.py                # Chat endpoint
│   │   └── services/
│   │       ├── embeddings.py          # Gemini embedding calls
│   │       ├── retrieval.py           # Vector search & retrieval
│   │       └── generator.py           # LLM response generation
│   ├── orchestrator/
│   │   └── chat_orchestrator.py       # Coordinates the chat request flow
│   ├── services/                      # Knowledge, support, and multi-source
│   │   │                              #   retrieval building blocks (see note above)
│   │   ├── knowledge/, support/, documents/
│   │   └── routing/, manager/, merger/, search/, retrievers/, generator/
│   ├── infrastructure/database/       # Supabase client integration
│   ├── mcp/                           # MCP server + tools (separate process)
│   ├── shared/                        # Logging and shared utilities
│   ├── sb.py                          # Supabase client accessor
│   ├── chunk.py                       # Semantic chunking helper
│   ├── intensive_cleaner.py           # Markdown cleaning helper
│   └── chat.py / chat_cli.py          # CLI entry points
│
├── scripts/                           # Standalone crawl/chunk/upload utilities
│   ├── crawl.py
│   ├── chunk_runner.py
│   ├── upload_vectors.py
│   └── test_clean.py
│
├── frontend/                          # React TypeScript frontend
│   ├── src/
│   │   ├── App.tsx                    # Main chat application
│   │   └── index.css                  # Tailwind styles
│   ├── public/
│   │   └── logo/                      # Ha-Shem branding
│   ├── package.json                   # Node.js dependencies
│   ├── vite.config.ts                 # Vite configuration
│   ├── tailwind.config.js             # Tailwind CSS config
│   └── tsconfig.json                  # TypeScript configuration
│
└── tests/                             # pytest suite for orchestrator & services
```

---

## 🛠️ Troubleshooting

### Common Issues

**"ModuleNotFoundError: No module named 'src'"**
```bash
# Ensure you're in the project root when running
cd /path/to/get-kc
python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

**"Connection refused" when accessing frontend**
- Ensure backend is running on port 8000
- Check VITE_API_BASE_URL is correctly set (defaults to localhost:8000)

**"GROQ_API_KEY not found"**
- Verify .env file exists in project root
- Ensure you've added the actual API key (not just placeholder text)

**Port already in use**
```bash
# Change port (Linux/Mac)
uvicorn src.api.app:app --host 127.0.0.1 --port 8001

# Windows - find and kill process on port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

---

## 🧪 Running Tests

```bash
# From project root, with backend dependencies installed
pytest
```

---

## 📦 Key Dependencies

**Backend (runtime):**
- `fastapi` - Web framework
- `groq` - LLM API client
- `google-genai` - Google Gemini embeddings
- `supabase` - Vector database client

**Backend (scripts / tooling, not required for the API itself):**
- `mcp` - MCP server (`src/mcp/`) for agent/IDE tool integration
- `crawl4ai` - web crawling for `scripts/crawl.py`
- `pytest` - test suite

**Frontend:**
- `react` - UI framework
- `typescript` - Type safety
- `tailwindcss` - Styling
- `framer-motion` - Animations
- `vite` - Build tool

---

## 📝 License

This project is part of Ha-Shem Limited's AI support platform initiative.

---

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify all environment variables are set correctly
3. Ensure all dependencies are installed
4. Check that both services (backend + frontend) are running

---

## 🎉 Happy Testing!

You're all set to test the Ha-Shem AI Support Platform locally. Start with the quick start commands and enjoy exploring the intelligent chat experience!
