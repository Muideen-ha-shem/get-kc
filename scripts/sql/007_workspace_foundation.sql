-- =============================================================================
-- Migration 007: Multi-Tenant Workspace Foundation
-- =============================================================================
--
-- NOT executed automatically — run this yourself in the Supabase SQL editor.
-- Claude has no DDL access with the credentials configured in .env (only
-- SUPABASE_URL/SUPABASE_KEY via PostgREST, which can't run CREATE TABLE).
--
-- Additive only — no existing table, column, RPC, or RLS policy is dropped
-- or altered in place, following the precedent set by 002_product_knowledge_
-- schema.sql (additive ALTER TABLE + new RPC alongside the untouched
-- original) and 004_customer_identity.sql (new tables + RLS with zero
-- impact on pre-existing tables).
--
-- Purpose: introduce a `workspaces` (tenant) table and scope every
-- customer-data table in this schema to it via a nullable-then-backfilled
-- `workspace_id` column. A single, deterministic "Ha-Shem" workspace row is
-- seeded and every existing row is backfilled to point at it, so no row
-- is ever left with a NULL workspace_id post-migration and every future
-- query can use a plain `eq("workspace_id", ...)` filter — never an
-- `IS NULL OR ...` special case.
--
-- demo_requests is intentionally NOT scoped here — it is not one of the
-- six required isolation areas for this phase (Phase 22). Treat it as a
-- Phase 23 candidate, not a silent omission.
--
-- Safe to run multiple times (IF NOT EXISTS guards throughout).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. workspaces — the tenant table itself.
-- -----------------------------------------------------------------------------
create table if not exists workspaces (
    id uuid primary key default gen_random_uuid(),
    slug text not null unique,
    name text not null,
    api_key text unique,
    host text,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_workspaces_slug on workspaces(slug);
create index if not exists idx_workspaces_api_key on workspaces(api_key);
create index if not exists idx_workspaces_host on workspaces(host);

comment on table workspaces is
    'Tenant registry (Phase 22). Every customer-scoped table below carries a workspace_id referencing this table. api_key/host are prepared for a future embeddable JS SDK (Phase 23+) — unused by any resolver path today beyond header-based lookup.';
comment on column workspaces.slug is
    'URL/param-safe identifier, e.g. ''ha-shem''. Used by WorkspaceResolver''s workspace_slug priority tier.';
comment on column workspaces.api_key is
    'Opaque per-workspace key for a future embeddable widget/SDK. NULL for the seeded default workspace today — no key is issued until Phase 23 needs one.';
comment on column workspaces.host is
    'Optional Host-header value (e.g. ''chat.ha-shem.com'') for WorkspaceResolver''s Host-header priority tier — prepares for embeddable-SDK deployments without building one yet.';

-- Deterministic UUID (not gen_random_uuid()) so every environment (dev,
-- staging, prod) seeds the *same* id and this migration is idempotent.
-- Mirrored exactly by DEFAULT_WORKSPACE_ID in
-- src/services/workspace/workspace_models.py — keep both in sync.
insert into workspaces (id, slug, name, is_active)
values ('00000000-0000-0000-0000-000000000001', 'ha-shem', 'Ha-Shem', true)
on conflict (id) do nothing;

-- -----------------------------------------------------------------------------
-- 2. documentation_chunks — knowledge isolation. Nullable column added
--    first (so the ALTER is instant even on a large table), then backfilled,
--    then indexed. Not marked NOT NULL: keeping it nullable means a future
--    ingestion path that forgets to pass workspace_id fails without a DB
--    constraint violation — consistent with product/category/source_type
--    being nullable in 002.
-- -----------------------------------------------------------------------------
alter table documentation_chunks
    add column if not exists workspace_id uuid references workspaces(id);

update documentation_chunks
    set workspace_id = '00000000-0000-0000-0000-000000000001'
    where workspace_id is null;

create index if not exists idx_documentation_chunks_workspace_id
    on documentation_chunks(workspace_id);

comment on column documentation_chunks.workspace_id is
    'Tenant this chunk belongs to. Backfilled to the Ha-Shem workspace for every pre-Phase-22 row. Every retrieval RPC filters on this column before ranking — never left to the prompt.';

-- -----------------------------------------------------------------------------
-- 3. New RPC: match_documents_by_workspace — cosine-similarity search with
--    a required workspace filter, layered on top of match_documents_by_
--    product's contract (adds workspace_id alongside product_filter).
--    match_documents(...) and match_documents_by_product(...) are NOT
--    modified or replaced — every existing caller (retrieval.py's two
--    current branches) is completely unaffected. Only a caller that
--    explicitly opts in by passing workspace_id uses this new function.
-- -----------------------------------------------------------------------------
create or replace function match_documents_by_workspace(
    query_embedding vector(768),
    match_threshold float,
    match_count int,
    workspace_id uuid,
    product_filter text[] default null
)
returns table (
    id bigint,
    parent_url text,
    chunk_content text,
    product text,
    category text,
    source_type text,
    similarity float
)
language sql stable
as $$
    select
        documentation_chunks.id,
        documentation_chunks.parent_url,
        documentation_chunks.chunk_content,
        documentation_chunks.product,
        documentation_chunks.category,
        documentation_chunks.source_type,
        1 - (documentation_chunks.embedding <=> query_embedding) as similarity
    from documentation_chunks
    where documentation_chunks.workspace_id = match_documents_by_workspace.workspace_id
      and 1 - (documentation_chunks.embedding <=> query_embedding) > match_threshold
      and (product_filter is null or documentation_chunks.product = any(product_filter))
    order by documentation_chunks.embedding <=> query_embedding
    limit match_count;
$$;

comment on function match_documents_by_workspace is
    'Workspace-scoped counterpart to match_documents_by_product. Isolation happens in the WHERE clause (workspace_id = ...), not by trusting prompt content — see src/api/services/retrieval.py.';

-- -----------------------------------------------------------------------------
-- 4. Isolation for conversations / profiles / appointments / saved items /
--    feedback / notifications. Same pattern repeated per table: add
--    nullable workspace_id, backfill to Ha-Shem, index. RLS is NOT changed
--    (still auth.uid()-only) — application-layer filtering only in this
--    phase; see Phase 23 recommendation in the plan re: RLS hardening.
-- -----------------------------------------------------------------------------

alter table customer_profiles add column if not exists workspace_id uuid references workspaces(id);
update customer_profiles set workspace_id = '00000000-0000-0000-0000-000000000001' where workspace_id is null;
create index if not exists idx_customer_profiles_workspace_id on customer_profiles(workspace_id);

alter table conversations add column if not exists workspace_id uuid references workspaces(id);
update conversations set workspace_id = '00000000-0000-0000-0000-000000000001' where workspace_id is null;
create index if not exists idx_conversations_workspace_id on conversations(workspace_id);

alter table conversation_messages add column if not exists workspace_id uuid references workspaces(id);
update conversation_messages set workspace_id = '00000000-0000-0000-0000-000000000001' where workspace_id is null;
create index if not exists idx_conversation_messages_workspace_id on conversation_messages(workspace_id);

alter table appointments add column if not exists workspace_id uuid references workspaces(id);
update appointments set workspace_id = '00000000-0000-0000-0000-000000000001' where workspace_id is null;
create index if not exists idx_appointments_workspace_id on appointments(workspace_id);

alter table saved_comparisons add column if not exists workspace_id uuid references workspaces(id);
update saved_comparisons set workspace_id = '00000000-0000-0000-0000-000000000001' where workspace_id is null;
create index if not exists idx_saved_comparisons_workspace_id on saved_comparisons(workspace_id);

alter table saved_recommendations add column if not exists workspace_id uuid references workspaces(id);
update saved_recommendations set workspace_id = '00000000-0000-0000-0000-000000000001' where workspace_id is null;
create index if not exists idx_saved_recommendations_workspace_id on saved_recommendations(workspace_id);

alter table message_feedback add column if not exists workspace_id uuid references workspaces(id);
update message_feedback set workspace_id = '00000000-0000-0000-0000-000000000001' where workspace_id is null;
create index if not exists idx_message_feedback_workspace_id on message_feedback(workspace_id);

alter table notifications add column if not exists workspace_id uuid references workspaces(id);
update notifications set workspace_id = '00000000-0000-0000-0000-000000000001' where workspace_id is null;
create index if not exists idx_notifications_workspace_id on notifications(workspace_id);

comment on column customer_profiles.workspace_id is 'Tenant scope (Phase 22). Backfilled to the Ha-Shem workspace.';
comment on column conversations.workspace_id is 'Tenant scope (Phase 22). Backfilled to the Ha-Shem workspace.';
comment on column conversation_messages.workspace_id is 'Tenant scope (Phase 22). Backfilled to the Ha-Shem workspace.';
comment on column appointments.workspace_id is 'Tenant scope (Phase 22). Backfilled to the Ha-Shem workspace.';
comment on column saved_comparisons.workspace_id is 'Tenant scope (Phase 22). Backfilled to the Ha-Shem workspace.';
comment on column saved_recommendations.workspace_id is 'Tenant scope (Phase 22). Backfilled to the Ha-Shem workspace.';
comment on column message_feedback.workspace_id is 'Tenant scope (Phase 22). Backfilled to the Ha-Shem workspace.';
comment on column notifications.workspace_id is 'Tenant scope (Phase 22). Backfilled to the Ha-Shem workspace.';
