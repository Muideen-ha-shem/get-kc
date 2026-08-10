-- =============================================================================
-- Migration 015: Fix Remaining Unscoped Chunk-Content Index
-- =============================================================================
--
-- NOT executed automatically — run this yourself in the Supabase SQL editor.
-- Claude has no DDL access with the credentials configured in .env.
--
-- Follow-up to 014_workspace_scoped_chunk_uniqueness.sql: that migration
-- dropped `chunk_content_unique_idx`, but a live recrawl attempt after
-- applying it still failed with the identical symptom under a DIFFERENT
-- index name — `chunk_content_md5_idx` — also a unique index on
-- `md5(chunk_content)` alone, with no `workspace_id` in its key. There
-- were apparently two separately-named legacy unique indexes on the same
-- expression from different points in this table's history; 014 only
-- knew about (and could only infer the name of) the one that first
-- surfaced. This migration catches the other one.
--
-- Safe to run multiple times and safe to run even if 014 already ran
-- (IF EXISTS / IF NOT EXISTS guards throughout; recreating the same
-- target index is a no-op).
-- =============================================================================

drop index if exists chunk_content_unique_idx;
drop index if exists chunk_content_md5_idx;

create unique index if not exists chunk_content_workspace_unique_idx
    on documentation_chunks (workspace_id, md5(chunk_content));

comment on index chunk_content_workspace_unique_idx is
    'Prevents re-ingesting byte-identical chunk content within the SAME workspace, without blocking two different workspaces from independently holding identical content (e.g. both crawling the same public page). Replaces both legacy unscoped indexes found on this table (chunk_content_unique_idx, chunk_content_md5_idx).';

-- Sanity check after running: this should return exactly one row
-- (chunk_content_workspace_unique_idx) and nothing named
-- chunk_content_unique_idx or chunk_content_md5_idx.
--
--   select indexname, indexdef from pg_indexes
--   where tablename = 'documentation_chunks' and indexdef ilike '%md5%';
