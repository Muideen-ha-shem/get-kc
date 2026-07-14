# Ha-Shem AI Support Platform Architecture

## Objective
Design a scalable AI platform that provides intelligent support across all Ha-Shem solutions and products while remaining modular, secure, and easy to extend.

## High-Level Architecture

```text
                                    ┌─────────────────────────┐
                                    │        End Users        │
                                    │ Staff • Clients • Admin │
                                    └─────────────┬───────────┘
                                                  │
                                                  ▼
                                    ┌─────────────────────────┐
                                    │ React / Next.js Frontend│
                                    │  AI Chat Interface      │
                                    └─────────────┬───────────┘
                                                  │
                                                  ▼
                                    ┌─────────────────────────┐
                                    │    AI Agent (LLM)       │
                                    │ GPT / Claude / Llama    │
                                    └─────────────┬───────────┘
                                                  │
                                        Intelligent Planning
                                                  │
                                                  ▼
                                    ┌─────────────────────────┐
                                    │     LangGraph Agent     │
                                    │ Workflow Orchestration  │
                                    └─────────────┬───────────┘
                                                  │
                                                  ▼
                     ┌───────────────────────────────────────────────────────┐
                     │                 MCP SERVER                            │
                     │      (Model Context Protocol Layer)                   │
                     └──────┬────────────┬─────────────┬─────────────────────┘
                            │            │             │
             ┌──────────────┘            │             └──────────────┐
             ▼                           ▼                            ▼
      Knowledge Tools            Product Tools                Support Tools
             │                           │                            │
             ▼                           ▼                            ▼
 search_knowledge_base()        list_products()          create_support_ticket()
 search_document()              get_training_materials() check_service_status()
 crawl_new_page()
 embed_document()
 reindex_database()
                            │
                            ▼
                  Business Service Layer
                            │
        ┌───────────────────┼────────────────────┐
        ▼                   ▼                    ▼
  Knowledge Service    Product Service     Support Service
        │                   │                    │
        ▼                   ▼                    ▼
  Supabase pgVector    Product Database    Ticket Database
        │
        ▼
   Document Storage
```

## Background Processing

```text
Upload -> FastAPI -> RabbitMQ/Kafka/celery python -> Workers

Workers:
- Crawl Worker
- Embedding Worker
- OCR Worker

Embedding Flow:
Extract -> Chunk -> Embed -> pgVector
```

## Runtime Request Flow

```text
User
 ↓
AI Agent
 ↓
LangGraph
 ↓
MCP Tool
 ↓
Knowledge Service
 ↓
Supabase pgVector / 
 ↓
Relevant Chunks
 ↓
LLM Response
```

## MCP Functional Modules

### Knowledge
- search_knowledge_base()
- search_document()
- crawl_new_page()
- embed_document()
- reindex_database()

### Products
- list_products()
- get_training_materials()

### Support
- create_support_ticket()
- check_service_status()

## Message Queue Responsibilities

- Decouple long-running AI jobs from API requests
- Retry failed jobs
- Parallel processing
- Fast user responses
- Scalable workers

## Worker Responsibilities

### Crawl Worker
- Crawl websites
- Detect updates
- Clean documents

### Embedding Worker
- Chunk documents
- Generate embeddings
- Store vectors
- Update status

### OCR Worker
- Extract text from PDFs
- Forward extracted text to embedding pipeline

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React / Next.js |
| Backend | FastAPI |
| Agent | LangGraph |
| Tool Layer | MCP |
| Queue | RabbitMQ / Kafka |
| Workers | Celery / Dramatiq / ARQ |
| Vector DB | Supabase pgVector |
| Database | PostgreSQL |
| Storage | Supabase Storage / S3 |
| Crawler | Crawl4AI |
| Embeddings | OpenAI / BGE / E5 |

## Benefits

- Modular architecture
- Independent service scaling
- Secure tool access
- Asynchronous AI processing
- Easier maintenance
- Future-proof integrations

## Future Expansion

- CRM
- HR
- Analytics
- Inventory
- Microsoft 365
- Jira
- SAP
- Internal APIs

## Executive Summary

The architecture separates AI reasoning, enterprise tools, business services, and background processing. MCP standardizes tool access, LangGraph orchestrates workflows, RabbitMQ/Kafka manages asynchronous tasks, and workers perform crawling, embedding, and OCR independently, enabling a scalable enterprise AI support platform.
