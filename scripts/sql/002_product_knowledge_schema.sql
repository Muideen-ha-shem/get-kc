-- =============================================================================
-- Migration 002: Multi-product knowledge base (SPIDIFY, ZivaAIRA) + demo requests
-- =============================================================================
--
-- NOT executed automatically by any script or by Claude. Review and run this
-- yourself (e.g. via the Supabase SQL editor) before running the new
-- crawl_spidify.py / crawl_zivaaira.py / upload_vectors.py product-aware
-- ingestion, or wiring ProductRouter into the live chat_orchestrator.
--
-- IMPORTANT — the match_documents(...) RPC function below is a best-effort
-- reconstruction of the standard pgvector "cosine similarity search" pattern
-- (the original CREATE FUNCTION statement is not checked into this repo, so
-- it could not be introspected). It is NOT modified or replaced by this
-- migration — a new, separate match_documents_by_product(...) function is
-- added instead, so your existing match_documents(...) function and every
-- caller of it (the current /chat endpoint) are completely unaffected
-- whether or not you've reviewed this file. Only code that explicitly calls
-- the new function (gated behind an explicit product_filter argument, see
-- src/api/services/retrieval.py) is affected.
--
-- Safe to run multiple times (IF NOT EXISTS / OR REPLACE throughout).
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. Add product metadata columns to the existing knowledge base table.
--    Nullable, no default beyond source_type — existing rows (ha-shem.com
--    general company content) simply get NULL product/category, which is
--    exactly "not scoped to any specific product" and requires no backfill.
-- -----------------------------------------------------------------------------

ALTER TABLE documentation_chunks
    ADD COLUMN IF NOT EXISTS product text,
    ADD COLUMN IF NOT EXISTS category text,
    ADD COLUMN IF NOT EXISTS source_type text;

COMMENT ON COLUMN documentation_chunks.product IS
    'Product this chunk belongs to, e.g. ''SPIDIFY'' or ''ZivaAIRA''. NULL for general/company content.';
COMMENT ON COLUMN documentation_chunks.category IS
    'Product category, e.g. ''Identity Verification'' or ''HR Recruitment''.';
COMMENT ON COLUMN documentation_chunks.source_type IS
    'Content provenance, e.g. ''official_product''.';

-- Speeds up product-filtered searches once there's real volume per product.
CREATE INDEX IF NOT EXISTS documentation_chunks_product_idx
    ON documentation_chunks (product);


-- -----------------------------------------------------------------------------
-- 2. New RPC: match_documents_by_product — adds an optional product filter
--    on top of the same cosine-similarity search match_documents already
--    does. Reconstructed to match the existing function's known contract
--    (query_embedding, match_threshold, match_count -> id, parent_url,
--    chunk_content, similarity), extended with product/category/source_type
--    in the result and an optional product_filter parameter.
--
--    *** Verify the SELECT/WHERE/ORDER BY below matches your actual
--    match_documents(...) function's logic before relying on this in
--    production — adjust the similarity expression if your original
--    function computes it differently. ***
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION match_documents_by_product(
    query_embedding vector(768),
    match_threshold float,
    match_count int,
    product_filter text[] DEFAULT NULL
)
RETURNS TABLE (
    id bigint,
    parent_url text,
    chunk_content text,
    product text,
    category text,
    source_type text,
    similarity float
)
LANGUAGE sql STABLE
AS $$
    SELECT
        documentation_chunks.id,
        documentation_chunks.parent_url,
        documentation_chunks.chunk_content,
        documentation_chunks.product,
        documentation_chunks.category,
        documentation_chunks.source_type,
        1 - (documentation_chunks.embedding <=> query_embedding) AS similarity
    FROM documentation_chunks
    WHERE 1 - (documentation_chunks.embedding <=> query_embedding) > match_threshold
      AND (product_filter IS NULL OR documentation_chunks.product = ANY(product_filter))
    ORDER BY documentation_chunks.embedding <=> query_embedding
    LIMIT match_count;
$$;


-- -----------------------------------------------------------------------------
-- 3. Demo request capture (Phase 5 groundwork). Not wired to any API
--    endpoint or frontend form yet — table only, ready for when that's built.
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS demo_requests (
    id bigserial PRIMARY KEY,
    name text NOT NULL,
    email text NOT NULL,
    company text,
    use_case text,
    product text,              -- which product they were interested in, if known
    created_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE demo_requests IS
    'Leads captured from "Request a demo" / "Contact sales" flows. Not yet wired to an API endpoint.';
