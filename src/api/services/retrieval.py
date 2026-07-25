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
    """
    sb_client = get_client()
    question_embedding = embed_query(question)

    if product_filter:
        rpc_name = "match_documents_by_product"
        rpc_params: dict[str, Any] = {
            "query_embedding": question_embedding,
            "match_threshold": 0.2,
            "match_count": 3,
            "product_filter": list(product_filter),
        }
    else:
        rpc_name = "match_documents"
        rpc_params = {
            "query_embedding": question_embedding,
            "match_threshold": 0.2,
            "match_count": 3,
        }

    rpc_response = sb_client.rpc(rpc_name, rpc_params).execute()

    if rpc_response.data is None:
        return [], [], []

    matches = rpc_response.data
    similarities = [match.get("similarity", 0.0) for match in matches]
    parent_urls = [match.get("parent_url", "") for match in matches if match.get("parent_url")]

    return matches, similarities, parent_urls
