# Enterprise AI Implementation Prompt – Live Search & Dynamic Knowledge Retrieval

You are a Senior AI Engineer and Enterprise Software Architect.

Your task is to evolve my existing RAG application into an **Enterprise Knowledge Intelligence Platform (EKIP)** capable of retrieving **live information from the internet** while preserving the existing architecture and codebase integrity.

## Existing Platform

The current system already contains:

* FastAPI backend
* React frontend
* FastMCP server
* Groq LLM
* Google Gemini Embeddings
* Supabase pgvector knowledge base
* Crawl4AI document ingestion pipeline
* Service Layer architecture
* AI Orchestrator
* Knowledge Service

The existing RAG pipeline must continue working exactly as it currently does.

Do **NOT** rewrite or replace existing working functionality.

---

# Objective

Implement **dynamic live information retrieval**.

The AI should no longer rely solely on the vector database.

Instead, it must determine whether external information is required and retrieve it dynamically.

Examples include:

* recent awards
* recent company news
* partner announcements
* certifications
* industry news
* technology updates
* press releases

The solution must be generic and work for any company or topic.

There must be **no hardcoded company names**, URLs, responses, keywords, or fixed workflows tied specifically to Ha-Shem.

---

# Critical Requirements

The implementation must follow Enterprise AI standards.

Do NOT hardcode:

* responses
* URLs
* domains
* company names
* search queries
* reply templates
* source priorities

Everything must be dynamically determined.

---

# Required Workflow

Implement the following runtime workflow.

## Step 1

Receive the user question.

Example:

> Has the company won any recent awards?

---

## Step 2

Determine whether the question requires:

* internal knowledge
* live information
* or both

Implement an intelligent routing mechanism.

This decision must NOT be based only on fixed keyword matching.

If appropriate, use the LLM as a lightweight intent classifier.

---

## Step 3

If live information is required:

Search the web using a real search provider.

Do NOT scrape random websites directly.

Implement a pluggable search provider abstraction so different providers can be swapped later.

The implementation should allow providers such as:

* Tavily
* Brave Search
* SerpAPI
* Bing Search
* Google Custom Search

without changing business logic.

---

## Step 4

From the search results:

Retrieve the most relevant URLs.

For each URL:

* download the page
* extract readable content
* remove boilerplate HTML
* clean navigation
* remove ads
* remove headers
* remove footers

Reuse the existing Crawl4AI / cleaning pipeline wherever possible.

Do not duplicate logic.

---

## Step 5

Process retrieved pages through the existing RAG pipeline.

Reuse existing functions wherever possible.

Pipeline:

* clean
* chunk
* embed
* semantic search

Do NOT create another embedding pipeline.

The live retrieval system must reuse the existing embedding implementation.

---

## Step 6

Perform semantic ranking.

Compare:

User Question Embedding

against

Downloaded Page Embeddings

Return only the highest-ranking chunks.

Do not send entire webpages to the LLM.

---

## Step 7

If internal knowledge also exists:

Retrieve it.

Merge:

* internal context
* external context

Remove duplicate information.

Rank by relevance.

Return one unified context.

---

## Step 8

Generate the final answer.

The LLM must answer ONLY using retrieved evidence.

Never fabricate information.

If confidence is low, clearly state uncertainty.

Include source attribution where possible.

---

## Step 9

Background Learning

If externally retrieved information is considered valuable:

Do NOT block the user.

Instead:

queue a background ingestion task.

The task should:

* crawl
* clean
* chunk
* embed
* insert into Supabase

Future searches should automatically benefit from newly discovered knowledge.

---

# Architecture Rules

Do NOT place business logic inside:

* FastAPI routes
* MCP tools
* Controllers

Business logic belongs inside Services.

Create reusable services.

Avoid duplication.

Maintain separation of concerns.

---

# Required Components

Introduce reusable services similar to:

* LiveSearchService
* SearchProvider
* PageFetcher
* PageExtractor
* ContextMerger
* SourceRouter

These should integrate with the existing Service Layer rather than replace it.

---

# Code Quality Requirements

The implementation must:

* be modular
* follow SOLID principles
* support dependency injection
* include type hints
* include docstrings
* include logging
* include error handling
* avoid duplicated code
* reuse existing services wherever possible

---

# Enterprise Requirements

The system must support future expansion including:

* additional search providers
* news providers
* partner portals
* RSS feeds
* APIs
* MCP tools
* asynchronous workers
* RabbitMQ
* scheduled indexing

without requiring architectural redesign.

---

# Deliverables

Implement production-ready code.

Refactor only where necessary.

Preserve all existing functionality.

Do not introduce breaking changes.

Do not hardcode any company-specific behavior.

The final result should be an Enterprise AI platform capable of combining:

* internal vector knowledge
* dynamically retrieved web knowledge
* semantic ranking
* evidence-based response generation

into a single intelligent workflow suitable for enterprise production use.
