"""MCP tool: live_web_search

Exposes the SearchService to the MCP tool layer so that the LangGraph agent
can call it as a standard tool.  Provider selection and credentials are read
from the environment at first call (lazy initialisation) to avoid startup
failures when the search keys are absent.
"""

from __future__ import annotations

import json
import os

from dotenv import load_dotenv

load_dotenv()

from src.shared.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Lazy singleton — built once, reused across tool calls within the process.
# ---------------------------------------------------------------------------

_search_service = None


def _get_search_service():
    """Return (and lazily create) the process-level SearchService instance."""
    global _search_service  # noqa: PLW0603
    if _search_service is None:
        from src.config.settings import Settings
        settings = Settings.from_environment()
        _search_service = settings.build_search_service()
        logger.info("live_web_search: SearchService initialised via %s.", _search_service.provider_name)
    return _search_service


# ---------------------------------------------------------------------------
# Tool function — registered on the MCP server in server.py
# ---------------------------------------------------------------------------

def live_web_search(query: str, max_results: int = 10) -> str:
    """Execute a live web search and return structured results as Markdown.

    Args:
        query:       A natural-language search query.
        max_results: Maximum number of results to return (1–20).

    Returns:
        A Markdown-formatted string listing each result with its title,
        URL, snippet, source domain, and relevance score (when available).
        Returns an error message string if the provider is unavailable.
    """
    if not query or not query.strip():
        return "Error: `query` must be a non-empty string."

    max_results = max(1, min(int(max_results), 20))

    try:
        service = _get_search_service()
    except RuntimeError as exc:
        logger.warning("live_web_search: no search provider configured — %s", exc)
        return (
            "⚠️ Live web search is not available: no search provider API key is configured.\n"
            "Set `TAVILY_API_KEY` or `BRAVE_SEARCH_API_KEY` in the environment."
        )

    logger.info("live_web_search: query=%r, max_results=%d, provider=%s", query, max_results, service.provider_name)

    try:
        results = service.search(query.strip(), max_results=max_results)
    except Exception as exc:
        logger.error("live_web_search: search failed — %s", exc, exc_info=True)
        return f"❌ Search failed: {exc}"

    if not results:
        return f"No web results found for: **{query}**"

    lines = [f"### Web Search Results\n**Query:** {query}  \n**Provider:** {service.provider_name}\n"]
    for idx, result in enumerate(results, start=1):
        score_label = f" _(score: {result.score:.2f})_" if result.score is not None else ""
        lines.append(
            f"#### {idx}. {result.title}{score_label}\n"
            f"**URL:** [{result.url}]({result.url})  \n"
            f"**Source:** {result.source}  \n"
            f"{result.snippet}\n"
        )

    return "\n".join(lines)
