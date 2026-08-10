-- =============================================================================
-- Migration 014: Workspace-Scoped Chunk Uniqueness (Phase 28 QA follow-up)
-- =============================================================================
--
-- NOT executed automatically — run this yourself in the Supabase SQL editor.
-- Claude has no DDL access with the credentials configured in .env.
--
-- Bug: `documentation_chunks` has a unique index `chunk_content_unique_idx`
-- on `md5(chunk_content)` ALONE — no `workspace_id` in the key. This index
-- predates Phase 22 (workspace_id was added later via a bolt-on ALTER TABLE
-- and this pre-existing index was never updated). Consequence, confirmed
-- live: any workspace that crawls/uploads content byte-identical to
-- content another workspace already has ingested (e.g. two workspaces
-- both crawling the same public page) gets a silent per-document insert
-- failure — the source/crawl job still reports success, but the affected
-- document ends up with zero chunks. This is a genuine cross-tenant data
-- issue: workspace isolation should never let one tenant's already-stored
-- content block another tenant's otherwise-identical content from being
-- stored.
--
-- Fix: replace the index with one scoped to (workspace_id, md5(chunk_
-- content)) — duplicate-prevention still works WITHIN a workspace
-- (re-crawling/re-uploading the same page twice in the same workspace
-- still correctly fails/skips), but two different workspaces can each
-- independently hold identical content without colliding.
--
-- Safe to run multiple times (IF EXISTS / IF NOT EXISTS guards).
-- =============================================================================

drop index if exists chunk_content_unique_idx;

create unique index if not exists chunk_content_workspace_unique_idx
    on documentation_chunks (workspace_id, md5(chunk_content));

comment on index chunk_content_workspace_unique_idx is
    'Prevents re-ingesting byte-identical chunk content within the SAME workspace, without blocking two different workspaces from independently holding identical content (e.g. both crawling the same public page). Replaces the pre-Phase-22 chunk_content_unique_idx, which had no workspace_id in its key.';
