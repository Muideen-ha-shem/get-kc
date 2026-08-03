-- =============================================================================
-- Migration 008: Workspace Branding (Embeddable SDK Foundation)
-- =============================================================================
--
-- NOT executed automatically — run this yourself in the Supabase SQL editor.
-- Claude has no DDL access with the credentials configured in .env (only
-- SUPABASE_URL/SUPABASE_KEY via PostgREST, which can't run CREATE TABLE).
--
-- Additive only — extends the `workspaces` table from
-- 007_workspace_foundation.sql with public branding fields consumed by the
-- new GET /workspace/config endpoint (Phase 23). No existing column, row,
-- RPC, or RLS policy is dropped or altered in place. `workspaces` still has
-- no RLS (app metadata, not per-user data) — these are the SAME columns
-- returned publicly to any caller holding a valid api_key/host/slug, so
-- nothing added here should ever be treated as a secret.
--
-- Safe to run multiple times (IF NOT EXISTS guards throughout).
-- =============================================================================

alter table workspaces add column if not exists logo text;
alter table workspaces add column if not exists primary_color text;
alter table workspaces add column if not exists welcome_message text;
alter table workspaces add column if not exists quick_actions jsonb;

comment on column workspaces.logo is
    'Public logo URL rendered in the embeddable SDK widget header (Phase 23). NULL falls back to the SDK''s built-in default mark — never required.';
comment on column workspaces.primary_color is
    'Hex color (e.g. ''#2563eb'') applied as the widget''s accent color by the embeddable SDK (Phase 23). NULL falls back to the SDK''s default theme color.';
comment on column workspaces.welcome_message is
    'First message the SDK widget shows in an empty conversation (Phase 23). NULL falls back to the SDK''s default greeting.';
comment on column workspaces.quick_actions is
    'jsonb array of suggested-prompt chips shown by the embeddable SDK widget, e.g. [{"label": "Compare products", "prompt": "What is the difference between SPIDIFY and ZivaAIRA?"}]. Each item is a canned question that prefills the chat input — NOT the same shape as NextActionSchema (no action_type/target). NULL/empty means no chips are shown.';
