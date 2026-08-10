-- =============================================================================
-- Migration 010: Live Human Support & Intelligent Routing (Phase 25)
-- =============================================================================
--
-- NOT executed automatically — run this yourself in the Supabase SQL editor.
-- Claude has no DDL access with the credentials configured in .env (only
-- SUPABASE_URL/SUPABASE_KEY via PostgREST, which can't run CREATE TABLE).
--
-- Additive only. Builds on 009_human_support_foundation.sql:
--   - Widens support_agents.department's check constraint (union of Phase
--     24's and Phase 25's department lists — no existing row becomes
--     invalid).
--   - Widens escalations.status's check constraint to add
--     'waiting_for_customer' (Phase 24's five values are untouched).
--   - Adds escalations.ai_engaged (new column, additive).
--   - Adds escalation_notes (new table, additive) — same no-RLS,
--     app-layer workspace_id-filtering precedent as support_agents/
--     escalations/escalation_messages (team-visible, not single-owner).
--
-- Safe to run multiple times (IF NOT EXISTS / DO $$ ... $$ guards throughout).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. support_agents.department — widen to the union of both phases' lists.
-- -----------------------------------------------------------------------------
alter table support_agents drop constraint if exists support_agents_department_check;
alter table support_agents add constraint support_agents_department_check check (
    department in (
        'Support', 'Sales', 'Solution Architect', 'Customer Success', 'General',
        'Implementation', 'Training', 'Finance'
    )
);

-- -----------------------------------------------------------------------------
-- 2. escalations — new waiting_for_customer status value, new ai_engaged flag.
-- -----------------------------------------------------------------------------
alter table escalations drop constraint if exists escalations_status_check;
alter table escalations add constraint escalations_status_check check (
    status in ('waiting', 'assigned', 'active', 'waiting_for_customer', 'resolved', 'closed')
);

alter table escalations add column if not exists ai_engaged boolean not null default true;

comment on column escalations.ai_engaged is
    'Phase 25: true while the AI is the only one engaged (before assignment, or after an explicit AI-rejoin). Flipped to false on assignment to a human agent. Informational for the frontend/copilot — /chat itself never reads this column, so AI answering is never blocked by escalation state.';

-- -----------------------------------------------------------------------------
-- 3. escalation_notes — internal, staff-only annotations (Phase 25).
--    Never returned to any customer-facing endpoint.
-- -----------------------------------------------------------------------------
create table if not exists escalation_notes (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references workspaces(id) on delete cascade,
    escalation_id uuid not null references escalations(id) on delete cascade,
    author_agent_id uuid references support_agents(id) on delete set null,
    content text not null,
    created_at timestamptz not null default now()
);

create index if not exists idx_escalation_notes_escalation_id_created_at
    on escalation_notes(escalation_id, created_at);

comment on table escalation_notes is
    'Internal, staff-only notes on an escalation (Phase 25) — never exposed to customers. No RLS — app-layer isolation via escalation_id -> escalations.workspace_id, same precedent as escalation_messages.';
