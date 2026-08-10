from typing import Any, Sequence

from dotenv import load_dotenv

try:
    from ...infrastructure.database.supabase import get_client
except ImportError:  # pragma: no cover - supports package execution
    from src.infrastructure.database.supabase import get_client

from .embeddings import embed_query

load_dotenv()


def retrieve_context(
    question: str,
    product_filter: Sequence[str] | None = None,
    match_count: int = 3,
    workspace_id: str | None = None,
) -> tuple[list[dict[str, Any]], list[float], list[str]]:
    """Retrieve knowledge-base matches for *question*.

    Args:
        question: The user's natural-language question.
        product_filter: Optional product names (e.g. ``["SPIDIFY"]``) to
            scope the search to. When ``None`` or empty (the default), this
            calls the original ``match_documents`` RPC exactly as before —
            behaviour is unchanged unless a caller explicitly opts in. When
            given, it calls ``match_documents_by_product`` instead, which
            requires ``scripts/sql/002_product_knowledge_schema.sql`` to
            have been applied first.
        match_count: Max rows to return. Defaults to ``3`` — the original,
            unconfigurable value — so every existing caller is unaffected.
            A higher value matters for narrow, per-product queries (see
            ``SearchManager._retrieve_knowledge_per_product``): candidate
            pages sometimes chunk into short, boilerplate-heavy fragments
            (nav text, security badges) that can look like a near-duplicate
            of an unrelated short fragment from a *different* product to
            ContextMerger's bigram dedup pass; requesting a few more
            candidates makes it far more likely at least one substantive,
            genuinely distinct chunk per product survives that pass.
        workspace_id: Optional tenant scope (Phase 22). ``None`` (the
            default) preserves the exact pre-Phase-22 branching below,
            byte-for-byte, so every existing caller is unaffected. When
            given, calls ``match_documents_by_workspace`` instead — scoping
            happens in the SQL ``WHERE`` clause, never by trusting the
            prompt — requiring ``scripts/sql/007_workspace_foundation.sql``
            to have been applied first.
    """
    sb_client = get_client()
    question_embedding = embed_query(question)

    if workspace_id:
        rpc_name = "match_documents_by_workspace"
        rpc_params: dict[str, Any] = {
            "query_embedding": question_embedding,
            "match_threshold": 0.2,
            "match_count": match_count,
            "workspace_id": workspace_id,
            "product_filter": list(product_filter) if product_filter else None,
        }
    elif product_filter:
        rpc_name = "match_documents_by_product"
        rpc_params = {
            "query_embedding": question_embedding,
            "match_threshold": 0.2,
            "match_count": match_count,
            "product_filter": list(product_filter),
        }
    else:
        rpc_name = "match_documents"
        rpc_params = {
            "query_embedding": question_embedding,
            "match_threshold": 0.2,
            "match_count": match_count,
        }

    rpc_response = sb_client.rpc(rpc_name, rpc_params).execute()

    if rpc_response.data is None:
        return [], [], []

    matches = rpc_response.data
    similarities = [match.get("similarity", 0.0) for match in matches]
    parent_urls = [match.get("parent_url", "") for match in matches if match.get("parent_url")]

    return matches, similarities, parent_urls
