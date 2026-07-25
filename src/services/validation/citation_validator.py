"""CitationValidator — cleans up the citation list ResponseGenerator returns.

Two concrete, deterministic problems this fixes, both observed in
production: (1) some knowledge-base rows have ``parent_url`` literally
stored as the string ``"Unknown URL"`` (a pre-existing data-quality issue in
the crawled data — see ``PROJECT_STRUCTURE.md``), which is a non-empty
string and so slips past the existing "drop citations with no url" check
and ends up in the response's ``sources`` list looking like a real URL;
(2) the same URL can appear more than once across citations (e.g. a
knowledge-base chunk and a live-search result pointing at the same page)
without being deduplicated at this stage.

This validates the *citation list* only — it runs after generation, on the
metadata ResponseGenerator already produced, and never touches the LLM's
answer text. It does not (and, deterministically, cannot) verify that every
sentence in the answer is individually entailed by a specific citation;
that would require an LLM-as-judge or NLP entailment model, which is
intentionally out of scope here (cost/latency, and the risk of a fragile
heuristic silently mangling a correct answer). What it does guarantee: every
citation that survives has a real, unique URL.
"""

from __future__ import annotations

import logging
from typing import Any, Sequence

from ...shared.logging import get_logger

logger: logging.Logger = get_logger(__name__)

# Values PageFetcher/knowledge-base rows are known to use as a URL
# placeholder when the real source URL wasn't captured. Compared
# case-insensitively.
_PLACEHOLDER_URLS: frozenset[str] = frozenset({
    "unknown url", "unknown", "n/a", "none", "null", "",
})


class CitationValidator:
    """Removes duplicate and placeholder-URL citations from a citation list.

    Args:
        min_score: If given, citations with a ``score`` below this are also
            dropped. ``None`` (default) disables score filtering.

    Typical usage::

        validator = CitationValidator()
        clean_citations = validator.validate(raw_citations)
    """

    def __init__(self, *, min_score: float | None = None) -> None:
        self._min_score = min_score
        logger.info("CitationValidator ready (min_score=%s).", self._min_score)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self, citations: Sequence[dict[str, Any]] | None) -> list[dict[str, Any]]:
        """Return *citations* with placeholder-URL and duplicate entries removed.

        Args:
            citations: Citation dicts as produced by
                ``ResponseGenerator._format_evidence`` (``url``, ``title``,
                ``source_type``, ``score`` keys).

        Returns:
            A new list, preserving the original order of surviving entries.
            Never raises — malformed entries (missing keys, wrong types) are
            dropped rather than crashing the response.
        """
        if not citations:
            return []

        seen_urls: set[str] = set()
        validated: list[dict[str, Any]] = []

        for citation in citations:
            try:
                if not self._is_valid(citation, seen_urls):
                    continue
                url = str(citation.get("url", "")).strip()
                seen_urls.add(url.lower())
                validated.append(citation)
            except Exception as exc:
                logger.warning("CitationValidator: skipping malformed citation %r — %s.", citation, exc)

        logger.info(
            "CitationValidator.validate: %d citations -> %d kept.",
            len(citations),
            len(validated),
        )
        return validated

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _is_valid(self, citation: dict[str, Any], seen_urls: set[str]) -> bool:
        if not isinstance(citation, dict):
            return False

        url = str(citation.get("url") or "").strip()
        if url.lower() in _PLACEHOLDER_URLS:
            return False
        if url.lower() in seen_urls:
            return False

        if self._min_score is not None:
            score = citation.get("score")
            if score is not None and score < self._min_score:
                return False

        return True
