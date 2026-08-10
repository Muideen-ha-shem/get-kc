-- =============================================================================
-- Migration 012: Self-Service Knowledge Management Portal (Phase 27)
-- =============================================================================
--
-- NOT executed automatically — run this yourself in the Supabase SQL editor.
-- Claude has no DDL access with the credentials configured in .env.
--
-- Additive only. documentation_chunks gains one nullable FK column
-- (knowledge_document_id) — every pre-Phase-27 row stays null, fully
-- backward compatible; the retrieval RPCs (match_documents,
-- match_documents_by_product, match_documents_by_workspace) never
-- reference it, so nothing about existing search behaviour changes.
--
-- No RLS on any new table — same team/shared-visibility, app-layer
-- workspace_id-filtering precedent as every admin-portal table since
-- Phase 24 (support_agents/escalations/.../platform_admins).
--
-- knowledge_sources.source_type is deliberately free text with NO check
-- constraint — future connectors (Notion/SharePoint/Google Drive/...) are
-- meant to require adding a string to a Python set, not a migration.
-- Lifecycle `status` columns, by contrast, are structural and DO get a
-- real check constraint.
--
-- Safe to run multiple times (IF NOT EXISTS guards throughout).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. workspace_admins — a workspace administrator is a normal Supabase Auth
--    user who additionally has a row here, scoped to one workspace. Mirrors
--    support_agents' exact precedent. Super Admins (platform_admins) can
--    still act on any workspace regardless of this table.
-- -----------------------------------------------------------------------------
create table if not exists workspace_admins (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references workspaces(id) on delete cascade,
    auth_user_id uuid not null references auth.users(id) on delete cascade,
    created_at timestamptz not null default now(),
    unique (workspace_id, auth_user_id)
);

create index if not exists idx_workspace_admins_workspace_id on workspace_admins(workspace_id);
create index if not exists idx_workspace_admins_auth_user_id on workspace_admins(auth_user_id);

comment on table workspace_admins is
    'Phase 27: per-workspace administrator membership. Distinct from platform_admins (global) and support_agents (department-scoped support role). No RLS — app-layer check via require_workspace_admin.';

-- -----------------------------------------------------------------------------
-- 2. knowledge_collections — workspace-defined logical groupings (Support,
--    Sales, Finance, HR, Training, Legal, ...). Independent of Products.
-- -----------------------------------------------------------------------------
create table if not exists knowledge_collections (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references workspaces(id) on delete cascade,
    name text not null,
    description text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    archived_at timestamptz
);

create index if not exists idx_knowledge_collections_workspace_id on knowledge_collections(workspace_id);

comment on table knowledge_collections is
    'Phase 27: workspace-scoped knowledge groupings, independent of and orthogonal to Products (workspace_products, Phase 26). No RLS.';

-- -----------------------------------------------------------------------------
-- 3. knowledge_sources — a configured ingestion source (website, upload,
--    faq, or a future connector). source_type is free text, app-validated
--    — see header note. config is type-specific (crawl depth/include-
--    exclude paths for website; original filename for upload; unused for
--    faq).
-- -----------------------------------------------------------------------------
create table if not exists knowledge_sources (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references workspaces(id) on delete cascade,
    collection_id uuid references knowledge_collections(id) on delete set null,
    source_type text not null,
    name text not null,
    status text not null default 'pending' check (
        status in ('pending', 'processing', 'embedding', 'ready', 'failed', 'archived', 'paused')
    ),
    config jsonb,
    product text,
    schedule text not null default 'manual' check (schedule in ('manual', 'daily', 'weekly', 'monthly')),
    last_crawled_at timestamptz,
    last_indexed_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    archived_at timestamptz
);

create index if not exists idx_knowledge_sources_workspace_id on knowledge_sources(workspace_id);
create index if not exists idx_knowledge_sources_workspace_status on knowledge_sources(workspace_id, status);

comment on table knowledge_sources is
    'Phase 27: a configured knowledge ingestion source. source_type has no check constraint by design — see migration header. product is validated at the application layer against shared.product_registry.PRODUCT_REGISTRY.keys(), same pattern as workspace_products (Phase 26). No RLS.';

-- -----------------------------------------------------------------------------
-- 4. knowledge_documents — one row per discovered/uploaded/authored
--    document under a source (one crawled page, one uploaded file, one FAQ
--    entry). chunk_count/char_count are denormalized for the dashboard.
-- -----------------------------------------------------------------------------
create table if not exists knowledge_documents (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references workspaces(id) on delete cascade,
    source_id uuid not null references knowledge_sources(id) on delete cascade,
    parent_url text,
    title text,
    status text not null default 'pending' check (
        status in ('pending', 'processing', 'embedding', 'ready', 'failed', 'archived')
    ),
    chunk_count integer not null default 0,
    char_count integer not null default 0,
    error_message text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    archived_at timestamptz
);

create index if not exists idx_knowledge_documents_workspace_id on knowledge_documents(workspace_id);
create index if not exists idx_knowledge_documents_source_id on knowledge_documents(source_id);
create index if not exists idx_knowledge_documents_workspace_status on knowledge_documents(workspace_id, status);

comment on table knowledge_documents is
    'Phase 27: one row per ingested document (crawled page / uploaded file / FAQ entry). status is authoritative for the ingestion pipeline — crawl_logs/embedding_jobs are observability logs only. No RLS.';

-- -----------------------------------------------------------------------------
-- 5. documentation_chunks — one additive FK column linking searchable
--    chunks back to their source document. Nullable — every pre-Phase-27
--    row (the 13 hand-crawled products) stays null.
-- -----------------------------------------------------------------------------
alter table documentation_chunks
    add column if not exists knowledge_document_id uuid references knowledge_documents(id) on delete cascade;

create index if not exists idx_documentation_chunks_knowledge_document_id
    on documentation_chunks(knowledge_document_id);

comment on column documentation_chunks.knowledge_document_id is
    'Phase 27: links a chunk back to the knowledge_documents row that produced it, for preview/quality features. Null for all pre-Phase-27 rows and for anything ingested outside the self-service portal. Never referenced by the retrieval RPCs — retrieval behaviour is unchanged.';

-- -----------------------------------------------------------------------------
-- 6. crawl_jobs / crawl_logs — website-crawl execution tracking.
-- -----------------------------------------------------------------------------
create table if not exists crawl_jobs (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references workspaces(id) on delete cascade,
    source_id uuid not null references knowledge_sources(id) on delete cascade,
    status text not null default 'pending' check (status in ('pending', 'running', 'completed', 'failed')),
    pages_discovered integer not null default 0,
    pages_ingested integer not null default 0,
    started_at timestamptz,
    completed_at timestamptz,
    error_message text,
    created_at timestamptz not null default now()
);

create index if not exists idx_crawl_jobs_source_id on crawl_jobs(source_id);
create index if not exists idx_crawl_jobs_workspace_id on crawl_jobs(workspace_id);

comment on table crawl_jobs is 'Phase 27: one row per crawl execution (manual or, in a future phase, scheduled). No RLS.';

create table if not exists crawl_logs (
    id uuid primary key default gen_random_uuid(),
    crawl_job_id uuid not null references crawl_jobs(id) on delete cascade,
    url text not null,
    status text not null check (status in ('fetched', 'cleaned', 'chunked', 'embedded', 'failed')),
    message text,
    created_at timestamptz not null default now()
);

create index if not exists idx_crawl_logs_crawl_job_id on crawl_logs(crawl_job_id);

comment on table crawl_logs is 'Phase 27: per-page progress log for a crawl_job. Observability only, not a source of truth. No RLS.';

-- -----------------------------------------------------------------------------
-- 7. document_versions — extension point for future incremental crawling.
--    One row written per (re)ingest; no diffing logic this phase.
-- -----------------------------------------------------------------------------
create table if not exists document_versions (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references knowledge_documents(id) on delete cascade,
    version_number integer not null,
    content_hash text,
    chunk_count integer not null default 0,
    created_at timestamptz not null default now()
);

create index if not exists idx_document_versions_document_id on document_versions(document_id);

comment on table document_versions is
    'Phase 27: extension point only — a content_hash is stored per (re)ingest so a future phase can diff versions and skip unchanged pages (incremental crawling). No diff/skip logic is implemented yet. No RLS.';

-- -----------------------------------------------------------------------------
-- 8. embedding_jobs — lightweight per-document embedding attempt log.
-- -----------------------------------------------------------------------------
create table if not exists embedding_jobs (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references knowledge_documents(id) on delete cascade,
    status text not null default 'pending' check (status in ('pending', 'running', 'completed', 'failed')),
    chunks_embedded integer not null default 0,
    error_message text,
    created_at timestamptz not null default now(),
    completed_at timestamptz
);

create index if not exists idx_embedding_jobs_document_id on embedding_jobs(document_id);

comment on table embedding_jobs is 'Phase 27: observability log for the embedding step. knowledge_documents.status is authoritative, not this table. No RLS.';

-- -----------------------------------------------------------------------------
-- 9. knowledge_quality_reports — periodic/on-demand diagnostic snapshots.
-- -----------------------------------------------------------------------------
create table if not exists knowledge_quality_reports (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references workspaces(id) on delete cascade,
    generated_at timestamptz not null default now(),
    duplicate_chunk_count integer not null default 0,
    broken_url_count integer not null default 0,
    empty_document_count integer not null default 0,
    embedding_failure_count integer not null default 0,
    large_chunk_count integer not null default 0,
    missing_metadata_count integer not null default 0,
    details jsonb
);

create index if not exists idx_knowledge_quality_reports_workspace_id on knowledge_quality_reports(workspace_id);

comment on table knowledge_quality_reports is 'Phase 27: on-demand knowledge-quality diagnostic snapshots. No RLS.';
