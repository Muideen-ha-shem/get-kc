-- =============================================================================
-- Migration 009: Human Support / AI Escalation Foundation (Phase 24)
-- =============================================================================
--
-- NOT executed automatically — run this yourself in the Supabase SQL editor.
-- Claude has no DDL access with the credentials configured in .env (only
-- SUPABASE_URL/SUPABASE_KEY via PostgREST, which can't run CREATE TABLE).
--
-- Additive only — no existing table, column, RPC, or RLS policy is dropped
-- or altered in place.
--
-- No RLS on any table below. Precedent: workspaces (007_workspace_foundation.sql)
-- has no RLS because it's a workspace-shared-visibility table, not a
-- single-owner row — Postgres RLS keyed on auth.uid() alone cannot express
-- "any member of workspace X may read/write this row" without custom JWT
-- claims/session vars, which is out of scope. support_agents/escalations/
-- escalation_messages are the same shape of table (team-visible within a
-- workspace, not owned by one user), so they follow the same app-layer
-- workspace_id-filtering precedent rather than the auth.uid()-owner RLS
-- pattern used by customer_profiles/conversations/saved_*.
--
-- Scope trim: no separate agent_assignments table — escalations.
-- assigned_agent_id + assigned_at already carry 100% of "who is assigned,
-- since when." A join table would only add redundant state to keep in
-- sync. Deliberate, not an oversight.
--
-- Safe to run multiple times (IF NOT EXISTS guards throughout).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. support_agents — a registered agent within a workspace. An "agent" is
--    just a normal Supabase Auth user who additionally has a row here.
-- -----------------------------------------------------------------------------
create table if not exists support_agents (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references workspaces(id) on delete cascade,
    auth_user_id uuid not null references auth.users(id) on delete cascade,
    name text not null,
    email text not null,
    department text not null default 'General' check (
        department in ('Support', 'Sales', 'Solution Architect', 'Customer Success', 'General')
    ),
    status text not null default 'offline' check (status in ('available', 'away', 'offline')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (workspace_id, auth_user_id)
);

create index if not exists idx_support_agents_workspace_id on support_agents(workspace_id);
create index if not exists idx_support_agents_workspace_status on support_agents(workspace_id, status);
create index if not exists idx_support_agents_auth_user_id on support_agents(auth_user_id);

comment on table support_agents is
    'Registered support agents per workspace (Phase 24). Department is stored now for future routing but is NOT used for assignment in Phase 24 — assignment is "first available agent in the workspace" regardless of department. No RLS — app-layer workspace_id filtering, same precedent as workspaces.';

-- -----------------------------------------------------------------------------
-- 2. escalations — a single AI-to-human handoff.
--    Lifecycle: waiting -> assigned -> active -> resolved -> closed,
--    mirroring the plain-status-column-with-check-constraint pattern
--    already used by appointments.status (005_saved_items.sql).
-- -----------------------------------------------------------------------------
create table if not exists escalations (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references workspaces(id) on delete cascade,
    conversation_id uuid references conversations(id) on delete set null,
    status text not null default 'waiting' check (
        status in ('waiting', 'assigned', 'active', 'resolved', 'closed')
    ),
    assigned_agent_id uuid references support_agents(id) on delete set null,
    trigger_reason text not null check (
        trigger_reason in ('explicit_request', 'critical_intent', 'low_confidence', 'unresolved')
    ),
    department text,
    summary jsonb,
    created_at timestamptz not null default now(),
    assigned_at timestamptz,
    resolved_at timestamptz,
    closed_at timestamptz
);

create index if not exists idx_escalations_workspace_status on escalations(workspace_id, status);
create index if not exists idx_escalations_assigned_agent_id on escalations(assigned_agent_id);
create index if not exists idx_escalations_conversation_id on escalations(conversation_id);

comment on table escalations is
    'A single AI-to-human handoff (Phase 24). department is stored (informational) but is never a routing input in Phase 24 — see support_agents. No RLS — app-layer workspace_id filtering.';

-- -----------------------------------------------------------------------------
-- 3. escalation_messages — live agent<->customer chat during an escalation.
--    Deliberately NOT stored in conversation_messages (whose role check
--    constraint is user/assistant only) — keeps the AI-turn history table
--    100% untouched.
-- -----------------------------------------------------------------------------
create table if not exists escalation_messages (
    id uuid primary key default gen_random_uuid(),
    escalation_id uuid not null references escalations(id) on delete cascade,
    sender_type text not null check (sender_type in ('agent', 'customer')),
    sender_auth_user_id uuid,
    content text not null,
    created_at timestamptz not null default now()
);

create index if not exists idx_escalation_messages_escalation_id_created_at
    on escalation_messages(escalation_id, created_at);

comment on table escalation_messages is
    'Live agent<->customer chat during an escalation (Phase 24). No RLS — app-layer isolation via escalation_id -> escalations.workspace_id.';
