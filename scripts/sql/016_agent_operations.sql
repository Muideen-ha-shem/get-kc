-- =============================================================================
-- 016 — Agent Operations: work sessions (clock in/out), AUX tracking, and
-- workspace-configurable performance targets / AUX categorization.
--
-- Additive-only (safe to run multiple times). No RLS — same team/shared-
-- visibility, app-layer workspace_id-filtering precedent as every other
-- table since Phase 24 (escalations/support_agents/...). Historical rows
-- are never deleted by the application — only the still-open row (no
-- clock_out_at / no ended_at) is ever updated to close it.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. agent_work_sessions — one row per clock-in. At most one row per agent
--    may have a null clock_out_at at any time (enforced at the service layer,
--    not the DB, matching this codebase's existing precedent of app-layer
--    invariants over DB constraints for multi-step business rules).
-- -----------------------------------------------------------------------------
create table if not exists agent_work_sessions (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references workspaces(id) on delete cascade,
    agent_id uuid not null references support_agents(id) on delete cascade,
    work_date date not null,
    clock_in_at timestamptz not null default now(),
    clock_out_at timestamptz,
    total_work_seconds integer,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_work_sessions_agent_active
    on agent_work_sessions(agent_id) where clock_out_at is null;
create index if not exists idx_work_sessions_workspace_date
    on agent_work_sessions(workspace_id, work_date);

comment on table agent_work_sessions is
    'Agent Operations: one row per clock-in/clock-out cycle. Never deleted — clock_out_at/total_work_seconds are set once, on close.';

-- -----------------------------------------------------------------------------
-- 2. agent_aux_events — AUX (away-reason) periods within a work session. At
--    most one row per agent may have a null ended_at at any time.
-- -----------------------------------------------------------------------------
create table if not exists agent_aux_events (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references workspaces(id) on delete cascade,
    agent_id uuid not null references support_agents(id) on delete cascade,
    work_session_id uuid not null references agent_work_sessions(id) on delete cascade,
    aux_type text not null,
    started_at timestamptz not null default now(),
    ended_at timestamptz,
    duration_seconds integer,
    reason text,
    created_at timestamptz not null default now()
);

create index if not exists idx_aux_events_agent_active
    on agent_aux_events(agent_id) where ended_at is null;
create index if not exists idx_aux_events_session
    on agent_aux_events(work_session_id);

comment on table agent_aux_events is
    'Agent Operations: AUX (away-reason) periods — meeting/training/break/etc. — inside a work session. aux_type is free text, categorized via workspace_settings.aux_categories rather than a check constraint, so new AUX types never require a migration.';

-- -----------------------------------------------------------------------------
-- 3. workspace_settings — performance targets (all nullable; a workspace with
--    none configured simply shows no target comparison) + AUX categorization
--    override (defaults are applied in the application layer when null).
-- -----------------------------------------------------------------------------
alter table workspace_settings add column if not exists target_resolution_rate double precision;
alter table workspace_settings add column if not exists target_response_minutes double precision;
alter table workspace_settings add column if not exists target_resolution_minutes double precision;
alter table workspace_settings add column if not exists target_csat double precision;
alter table workspace_settings add column if not exists aux_categories jsonb;

comment on column workspace_settings.target_resolution_rate is
    'Agent Operations: configured target (0-1 fraction) for escalation resolution rate. Null = no target configured, no comparison shown.';
comment on column workspace_settings.target_response_minutes is
    'Agent Operations: configured target for average first-response time in minutes.';
comment on column workspace_settings.target_resolution_minutes is
    'Agent Operations: configured target for average resolution time in minutes.';
comment on column workspace_settings.target_csat is
    'Agent Operations: configured target CSAT (1-5). No per-agent CSAT data source exists yet — reserved for when one does.';
comment on column workspace_settings.aux_categories is
    'Agent Operations: maps an aux_type string to one of customer_service/productive_operational/non_customer_work/non_working. Null = built-in defaults apply.';
