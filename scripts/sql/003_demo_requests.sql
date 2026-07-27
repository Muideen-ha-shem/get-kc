-- =============================================================================
-- Migration 003: Demo request capture
-- =============================================================================
--
-- NOT executed automatically — run this yourself in the Supabase SQL editor.
-- Claude has no DDL access with the credentials configured in .env (only
-- SUPABASE_URL/SUPABASE_KEY via PostgREST, which can't run CREATE TABLE),
-- so this step can't be automated from the app side.
--
-- Standalone extract of the demo_requests table from
-- scripts/sql/002_product_knowledge_schema.sql, for when you want demo
-- requests working without also applying the product-schema changes in that
-- file. Safe to run before, after, or independently of 002 — no dependency
-- either way. Safe to run multiple times (CREATE TABLE IF NOT EXISTS).
--
-- Once this exists, POST /demo-request (src/api/routes/demo_request.py)
-- starts working immediately — no code changes needed.
-- =============================================================================

CREATE TABLE IF NOT EXISTS demo_requests (
    id bigserial PRIMARY KEY,
    name text NOT NULL,
    email text NOT NULL,
    company text,
    use_case text,
    product text,              -- which solution they were interested in, if known
    created_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE demo_requests IS
    'Leads captured from "Request a demo" / "Contact sales" / "Talk to an expert" flows.';
