-- =============================================================================
-- Migration 011: Multi-Tenant Administration Portal (Phase 26)
-- =============================================================================
--
-- NOT executed automatically — run this yourself in the Supabase SQL editor.
-- Claude has no DDL access with the credentials configured in .env.
--
-- Additive only — no existing table, column, RPC, or RLS policy is dropped
-- or altered in place, except two new nullable timestamp columns added to
-- `workspaces` (archived_at, deleted_at) via `alter table ... add column if
-- not exists`, which is itself additive/backward compatible.
--
-- No RLS on any table below — same team/shared-visibility, app-layer
-- workspace_id-filtering precedent as support_agents/escalations
-- (009_human_support_foundation.sql). Admin-portal tables are inherently
-- cross-tenant (a super admin, by definition, is not scoped to one
-- workspace), making per-row RLS even less applicable here than to
-- support_agents/escalations.
--
-- Safe to run multiple times (IF NOT EXISTS guards throughout).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 0. workspaces — two new nullable soft-delete/archive markers (additive).
--    is_active (existing, Phase 22) continues to mean suspend/reactivate;
--    archived_at/deleted_at are separate, coarser lifecycle markers, mirroring
--    the resolved_at/closed_at timestamp-marker style used by escalations
--    rather than inventing a new status enum column.
-- -----------------------------------------------------------------------------
alter table workspaces add column if not exists archived_at timestamptz;
alter table workspaces add column if not exists deleted_at timestamptz;

comment on column workspaces.archived_at is
    'Phase 26: set when a super admin archives a workspace (read-only, hidden from active lists, distinct from is_active=false suspension). Null = not archived.';
comment on column workspaces.deleted_at is
    'Phase 26: set when a super admin soft-deletes a workspace. Null = not deleted. No hard-delete path is exposed anywhere in Phase 26.';

-- -----------------------------------------------------------------------------
-- 1. platform_admins — a super admin is just a normal Supabase Auth user who
--    additionally has a row here. Mirrors support_agents' exact precedent.
--    Global, not workspace-scoped — no workspace_id column by design.
-- -----------------------------------------------------------------------------
create table if not exists platform_admins (
    id uuid primary key default gen_random_uuid(),
    auth_user_id uuid not null unique references auth.users(id) on delete cascade,
    created_at timestamptz not null default now()
);

create index if not exists idx_platform_admins_auth_user_id on platform_admins(auth_user_id);

comment on table platform_admins is
    'Global super-admin membership (Phase 26). An auth_user_id is a super admin iff a row exists here. Not workspace-scoped. No RLS — app-layer check via PlatformAdminService.is_super_admin(), same precedent as support_agents.';

-- -----------------------------------------------------------------------------
-- 2. workspace_products — per-workspace product enable/disable, ADMIN
--    METADATA ONLY. Does not affect live RAG/retrieval routing in Phase 26.
--    product_id is free text matching PRODUCT_REGISTRY's Python dict keys —
--    deliberately NOT a foreign key, since PRODUCT_REGISTRY is a dict, not a
--    DB table.
-- -----------------------------------------------------------------------------
create table if not exists workspace_products (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references workspaces(id) on delete cascade,
    product_id text not null,
    enabled boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (workspace_id, product_id)
);

create index if not exists idx_workspace_products_workspace_id on workspace_products(workspace_id);

comment on table workspace_products is
    'Phase 26: per-workspace product catalog toggle. Admin-facing metadata only — this table does NOT gate what the live RAG/retrieval pipeline (ProductRouter/SearchManager) actually returns; those are unchanged in Phase 26. product_id is validated at the application layer against shared.product_registry.PRODUCT_REGISTRY.keys(), not a DB foreign key. No RLS.';

-- -----------------------------------------------------------------------------
-- 3. workspace_settings — one row per workspace: AI/chat/human-support
--    settings plus the secondary branding fields not already on `workspaces`.
--    Single-row-per-entity, mirroring escalations' shape, not an EAV table.
-- -----------------------------------------------------------------------------
create table if not exists workspace_settings (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null unique references workspaces(id) on delete cascade,
    ai_enabled boolean not null default true,
    confidence_threshold double precision,
    live_search_enabled boolean not null default true,
    human_escalation_enabled boolean not null default true,
    ai_personality text,
    welcome_prompt text,
    chat_enabled boolean not null default true,
    offline_mode boolean not null default false,
    greeting_message text,
    working_hours jsonb,
    escalation_timeout_minutes integer,
    auto_assignment_enabled boolean not null default true,
    secondary_color text,
    chat_avatar text,
    company_name text,
    footer_text text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_workspace_settings_workspace_id on workspace_settings(workspace_id);

comment on table workspace_settings is
    'Phase 26: one settings row per workspace (AI/chat/human-support toggles + secondary branding fields). Primary branding (logo, primary_color, welcome_message, quick_actions) stays on workspaces (Phase 23) — this table only adds what Phase 23 did not cover. No RLS.';

-- -----------------------------------------------------------------------------
-- 4. feature_flags — freeform per-workspace flags, no migration needed to
--    add a new flag key later.
-- -----------------------------------------------------------------------------
create table if not exists feature_flags (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references workspaces(id) on delete cascade,
    flag_key text not null,
    enabled boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (workspace_id, flag_key)
);

create index if not exists idx_feature_flags_workspace_id on feature_flags(workspace_id);

comment on table feature_flags is
    'Phase 26: freeform per-workspace feature flags. flag_key is not an enum/check-constrained column so new flags never require a migration. No RLS.';

-- -----------------------------------------------------------------------------
-- 5. audit_logs — append-only. workspace_id is nullable for platform-level
--    events (e.g. workspace creation itself, admin-role assignment) that
--    aren't scoped to one existing workspace row.
-- -----------------------------------------------------------------------------
create table if not exists audit_logs (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid references workspaces(id) on delete set null,
    actor_auth_user_id uuid not null,
    action text not null,
    metadata jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_audit_logs_workspace_id_created_at on audit_logs(workspace_id, created_at);
create index if not exists idx_audit_logs_actor_auth_user_id on audit_logs(actor_auth_user_id);

comment on table audit_logs is
    'Phase 26: append-only admin action log. workspace_id is nullable for platform-level events with no single-workspace scope. No update/delete method is ever exposed against this table — AuditService only exposes record()/list_recent(). No RLS.';
