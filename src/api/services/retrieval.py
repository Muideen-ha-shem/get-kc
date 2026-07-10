from typing import Any

from dotenv import load_dotenv

try:
    from sb import get_client
except ImportError:  # pragma: no cover - supports package execution
    from src.sb import get_client

from .embeddings import embed_query

load_dotenv()


def retrieve_context(question: str) -> tuple[list[dict[str, Any]], list[float], list[str]]:
    sb_client = get_client()
    question_embedding = embed_query(question)

    rpc_response = sb_client.rpc(
        "match_documents",
        {
            "query_embedding": question_embedding,
            "match_threshold": 0.2,
            "match_count": 3,
        },
    ).execute()

    if rpc_response.data is None:
        return [], [], []

    matches = rpc_response.data
    similarities = [match.get("similarity", 0.0) for match in matches]
    parent_urls = [match.get("parent_url", "") for match in matches if match.get("parent_url")]

    return matches, similarities, parent_urls
