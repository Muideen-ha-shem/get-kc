-- =============================================================================
-- Migration 005: Saved Comparisons, Saved Recommendations, Appointments
-- =============================================================================
--
-- NOT executed automatically — run this yourself in the Supabase SQL editor.
-- Claude has no DDL access with the credentials configured in .env (only
-- SUPABASE_URL/SUPABASE_KEY via PostgREST, which can't run CREATE TABLE).
--
-- Additive only — does not touch any existing table.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- saved_comparisons — a customer's saved "Compare Solutions" selections.
-- Personal, authenticated data: RLS keyed on auth.uid(), same pattern as
-- customer_profiles/conversations (004_customer_identity.sql).
-- ---------------------------------------------------------------------------
create table if not exists saved_comparisons (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    product_ids jsonb not null,
    created_at timestamptz not null default now()
);

create index if not exists idx_saved_comparisons_user_id on saved_comparisons(user_id, created_at desc);

alter table saved_comparisons enable row level security;

create policy "saved_comparisons_select_own" on saved_comparisons for select using (auth.uid() = user_id);
create policy "saved_comparisons_insert_own" on saved_comparisons for insert with check (auth.uid() = user_id);
create policy "saved_comparisons_delete_own" on saved_comparisons for delete using (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- saved_recommendations — a customer's personal library of AI recommendations.
-- ---------------------------------------------------------------------------
create table if not exists saved_recommendations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    products jsonb not null,
    question text not null,
    recommendation text not null,
    created_at timestamptz not null default now()
);

create index if not exists idx_saved_recommendations_user_id on saved_recommendations(user_id, created_at desc);

alter table saved_recommendations enable row level security;

create policy "saved_recommendations_select_own" on saved_recommendations for select using (auth.uid() = user_id);
create policy "saved_recommendations_insert_own" on saved_recommendations for insert with check (auth.uid() = user_id);
create policy "saved_recommendations_delete_own" on saved_recommendations for delete using (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- appointments — Support Center booking. Public write (anonymous visitors
-- can book, same as demo_requests in 003_demo_requests.sql), so — matching
-- that table's precedent — RLS is intentionally left OFF here rather than
-- introducing an auth requirement the current public booking UI doesn't
-- have. user_id is nullable and only populated when the booker happens to
-- be signed in; it's never required for booking to succeed.
--
-- The unique constraint on (appointment_date, time_slot) is what actually
-- prevents a double-booking race between two concurrent requests — the
-- application layer also checks first, but the constraint is the real
-- guarantee.
-- ---------------------------------------------------------------------------
create table if not exists appointments (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id) on delete set null,
    name text not null,
    email text not null,
    appointment_date date not null,
    time_slot text not null,
    status text not null default 'confirmed' check (status in ('confirmed', 'cancelled')),
    created_at timestamptz not null default now(),
    unique (appointment_date, time_slot)
);

create index if not exists idx_appointments_date on appointments(appointment_date);

comment on table appointments is
    'Support Center "Book a strategy session" bookings. Public — no RLS, same as demo_requests.';
