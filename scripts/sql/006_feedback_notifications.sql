-- =============================================================================
-- Migration 006: Response Feedback + In-App Notifications
-- =============================================================================
--
-- NOT executed automatically — run this yourself in the Supabase SQL editor.
-- Claude has no DDL access with the credentials configured in .env (only
-- SUPABASE_URL/SUPABASE_KEY via PostgREST, which can't run CREATE TABLE).
--
-- Additive only — does not touch any existing table.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- message_feedback — 👍/👎 + optional comment on a chat answer.
-- Public write, same precedent as demo_requests/appointments: anonymous
-- visitors can rate a response too, not just signed-in customers. user_id
-- is populated when the rater happens to be signed in but is never required.
-- No RLS — analytics data, not personal data the rater needs to read back.
-- ---------------------------------------------------------------------------
create table if not exists message_feedback (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id) on delete set null,
    session_id text,
    conversation_id uuid references conversations(id) on delete set null,
    question text not null,
    answer text not null,
    rating text not null check (rating in ('helpful', 'not_helpful')),
    comment text,
    created_at timestamptz not null default now()
);

create index if not exists idx_message_feedback_created_at on message_feedback(created_at desc);

comment on table message_feedback is
    'Response quality feedback (thumbs up/down + optional comment). Public — no RLS, same as demo_requests.';

-- ---------------------------------------------------------------------------
-- notifications — in-app notifications for a signed-in customer's own
-- activity (demo requests, appointments, saved recommendations, support
-- updates). Personal data: RLS keyed on auth.uid(), same pattern as
-- saved_comparisons/saved_recommendations (005_saved_items.sql). A
-- notification is only ever created using the target user's own access
-- token (they're notified about their own action), so the insert policy
-- below is sufficient — no service-role/admin path is needed for the
-- triggers this phase wires up.
-- ---------------------------------------------------------------------------
create table if not exists notifications (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    type text not null check (type in ('demo_request', 'appointment', 'saved_recommendation', 'support_update')),
    title text not null,
    body text,
    is_read boolean not null default false,
    created_at timestamptz not null default now()
);

create index if not exists idx_notifications_user_id on notifications(user_id, created_at desc);

alter table notifications enable row level security;

create policy "notifications_select_own" on notifications for select using (auth.uid() = user_id);
create policy "notifications_insert_own" on notifications for insert with check (auth.uid() = user_id);
create policy "notifications_update_own" on notifications for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
