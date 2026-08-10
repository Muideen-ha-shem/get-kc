-- =============================================================================
-- Migration 013: Self-Service Organization Signup & Team Invitations (Phase 28)
-- =============================================================================
--
-- NOT executed automatically — run this yourself in the Supabase SQL editor.
-- Claude has no DDL access with the credentials configured in .env.
--
-- Additive only. `workspaces` gains two nullable/defaulted columns
-- (owner_auth_user_id, plan) — every pre-Phase-28 row (including every
-- workspace created via the super-admin onboarding wizard) stays
-- owner_auth_user_id = null, plan = 'free', fully backward compatible.
--
-- No RLS on the new table — same team/shared-visibility, app-layer
-- workspace_id-filtering precedent as every admin-portal table since
-- Phase 24 (support_agents/escalations/.../workspace_admins).
--
-- Safe to run multiple times (IF NOT EXISTS guards throughout).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. workspaces — owner + plan. `plan` is a structural, finite set (unlike
--    knowledge_sources.source_type's deliberate free-text precedent), so it
--    gets a real check constraint. No billing/payment enforcement anywhere
--    this phase — this column is captured at signup only.
-- -----------------------------------------------------------------------------
alter table workspaces add column if not exists owner_auth_user_id uuid references auth.users(id);
alter table workspaces add column if not exists plan text not null default 'free';

alter table workspaces drop constraint if exists workspaces_plan_check;
alter table workspaces add constraint workspaces_plan_check
    check (plan in ('free', 'starter', 'pro'));

create index if not exists idx_workspaces_owner_auth_user_id on workspaces(owner_auth_user_id);

comment on column workspaces.owner_auth_user_id is
    'The auth.users row that self-service-signed-up this workspace (Phase 28). Null for every workspace created via the super-admin onboarding wizard.';
comment on column workspaces.plan is
    'Plan tier captured at signup (free/starter/pro). No billing/payment enforcement exists anywhere yet — this is metadata only until a future billing phase.';

-- -----------------------------------------------------------------------------
-- 2. workspace_invitations — a pending/accepted/revoked invite for a
--    teammate to join a workspace as an agent or workspace_admin. Sent via
--    Supabase Auth's own hosted invite email (auth.admin.invite_user_by_email)
--    — no new email provider. This table is the single source of truth for
--    "what role/department was this invite for" — Supabase's own invite
--    metadata is not relied on for anything beyond delivering the email.
-- -----------------------------------------------------------------------------
create table if not exists workspace_invitations (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references workspaces(id) on delete cascade,
    email text not null,
    role text not null check (role in ('workspace_admin', 'agent')),
    department text,
    invited_by uuid not null references auth.users(id),
    status text not null default 'pending' check (status in ('pending', 'accepted', 'revoked')),
    created_at timestamptz not null default now(),
    accepted_at timestamptz
);

create index if not exists idx_workspace_invitations_workspace_id on workspace_invitations(workspace_id);

-- Partial unique index (not a table-level UNIQUE) so a revoked/accepted
-- invite doesn't block re-inviting the same email later — only one PENDING
-- invite per (workspace, email) at a time.
create unique index if not exists idx_workspace_invitations_pending_unique
    on workspace_invitations(workspace_id, lower(email))
    where status = 'pending';

comment on table workspace_invitations is
    'Pending/accepted/revoked team invites (Phase 28). department must match support_agents'' own check constraint values (Support/Sales/Solution Architect/Customer Success/General) — validated at the API layer, not duplicated here as a constraint since it only applies when role=agent.';
