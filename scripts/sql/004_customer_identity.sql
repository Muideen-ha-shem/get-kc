-- Phase 20 — Customer Identity Foundation
--
-- Additive only: creates three new tables plus a convenience trigger.
-- Does NOT modify documentation_chunks, crawled_pages, demo_requests, or
-- any other existing table. Anonymous /chat usage is entirely unaffected
-- by this migration — these tables are only ever touched for
-- authenticated requests.
--
-- Not executed by any script or by Claude (no DDL access with the
-- credentials in .env — only PostgREST via SUPABASE_URL/SUPABASE_KEY,
-- which can't run CREATE TABLE). Run this yourself via the Supabase SQL
-- editor. Requires Supabase Auth's built-in `auth.users` table, which
-- exists by default in every Supabase project.

-- ---------------------------------------------------------------------
-- customer_profiles — lightweight customer info, NOT AI memory.
-- One row per authenticated user (1:1 with auth.users).
-- ---------------------------------------------------------------------
create table if not exists customer_profiles (
    id uuid primary key default gen_random_uuid(),
    auth_user_id uuid not null unique references auth.users(id) on delete cascade,
    email text not null,
    full_name text,
    company_name text,
    industry text,
    phone text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    last_login timestamptz
);

create index if not exists idx_customer_profiles_auth_user_id on customer_profiles(auth_user_id);

alter table customer_profiles enable row level security;

create policy "customer_profiles_select_own"
    on customer_profiles for select
    using (auth.uid() = auth_user_id);

create policy "customer_profiles_insert_own"
    on customer_profiles for insert
    with check (auth.uid() = auth_user_id);

create policy "customer_profiles_update_own"
    on customer_profiles for update
    using (auth.uid() = auth_user_id)
    with check (auth.uid() = auth_user_id);

-- Auto-create a blank profile whenever a new auth user signs up, so the
-- dashboard/profile page always has a row to read/update rather than
-- needing a "does a profile exist yet" branch everywhere. ProfileService
-- also has its own create-if-missing fallback for robustness (e.g. a user
-- who signed up before this trigger existed).
create or replace function handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    insert into customer_profiles (auth_user_id, email, full_name)
    values (new.id, new.email, new.raw_user_meta_data->>'full_name')
    on conflict (auth_user_id) do nothing;
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function handle_new_auth_user();

-- ---------------------------------------------------------------------
-- conversations — one row per saved chat thread for an authenticated user.
-- ---------------------------------------------------------------------
create table if not exists conversations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    title text not null default 'New conversation',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_conversations_user_id on conversations(user_id);
create index if not exists idx_conversations_user_id_updated_at on conversations(user_id, updated_at desc);

alter table conversations enable row level security;

create policy "conversations_select_own"
    on conversations for select
    using (auth.uid() = user_id);

create policy "conversations_insert_own"
    on conversations for insert
    with check (auth.uid() = user_id);

create policy "conversations_update_own"
    on conversations for update
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

create policy "conversations_delete_own"
    on conversations for delete
    using (auth.uid() = user_id);

-- ---------------------------------------------------------------------
-- conversation_messages — one row per turn (user or assistant) within a
-- conversation. citations/metadata mirror the existing ChatResponse shape
-- (sources list, next_actions, etc.) so a resumed conversation can render
-- exactly like a live one.
-- ---------------------------------------------------------------------
create table if not exists conversation_messages (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references conversations(id) on delete cascade,
    role text not null check (role in ('user', 'assistant')),
    content text not null,
    citations jsonb not null default '[]'::jsonb,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_conversation_messages_conversation_id on conversation_messages(conversation_id, created_at);

alter table conversation_messages enable row level security;

-- Ownership is via the parent conversation's user_id — a message has no
-- user_id column of its own (avoids duplicating ownership data that could
-- drift from its parent conversation).
create policy "conversation_messages_select_own"
    on conversation_messages for select
    using (
        exists (
            select 1 from conversations
            where conversations.id = conversation_messages.conversation_id
            and conversations.user_id = auth.uid()
        )
    );

create policy "conversation_messages_insert_own"
    on conversation_messages for insert
    with check (
        exists (
            select 1 from conversations
            where conversations.id = conversation_messages.conversation_id
            and conversations.user_id = auth.uid()
        )
    );

create policy "conversation_messages_delete_own"
    on conversation_messages for delete
    using (
        exists (
            select 1 from conversations
            where conversations.id = conversation_messages.conversation_id
            and conversations.user_id = auth.uid()
        )
    );
