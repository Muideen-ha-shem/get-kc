"""SourceRouter — decides which knowledge sources to consult for a question.

This module contains two main exports:

* :class:`RoutingDecision` — a simple data object with one boolean per source.
* :class:`SourceRouter` — the router itself, which examines a user question
  and returns a :class:`RoutingDecision`.

How it works
------------
The router uses **intent-aware keyword heuristics** to make three kinds of
decisions:

1. **Web-only** — queries asking about current events, news, recent releases,
   or external topics that the internal KB cannot answer.
2. **Knowledge-base-only** — queries about company products, services,
   documentation, support policies.
3. **Both** — queries that mix internal and external concerns (e.g. "latest
   product pricing").

The :meth:`route` method is intentionally **pure** — it has no I/O and no
side-effects — making it trivially testable and safe to call in any context.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence

from ...shared.logging import get_logger

logger: logging.Logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Domain model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RoutingDecision:
    """Describes which knowledge sources should be queried for a question.

    Each boolean field corresponds to one source.  ``True`` means the
    router believes that source may contain relevant information.

    Attributes:
        knowledge: Whether to search the internal knowledge base (vector DB).
        web:       Whether to perform a live web search.
    """

    knowledge: bool = False
    web: bool = False

    def to_dict(self) -> dict[str, bool]:
        """Serialise to a plain dictionary."""
        return {
            "knowledge": self.knowledge,
            "web": self.web,
        }

    def any_active(self) -> bool:
        """Return ``True`` if at least one source is active."""
        return self.knowledge or self.web


# ---------------------------------------------------------------------------
# Default keyword lists
# ---------------------------------------------------------------------------

_KNOWLEDGE_KEYWORDS: tuple[str, ...] = (
    # Product / service enquiries
    "service", "services", "product", "products", "solution", "solutions",
    "pricing", "price", "cost", "offer", "offers", "offering", "offerings",
    "capability", "capabilities", "feature", "features",
    # Company information
    "company", "about", "mission", "vision", "team", "history",
    "contact", "located", "location", "address", "office", "offices",
    "founded", "founding", "founder", "founders", "ceo",
    # Support / help
    "support", "help", "guide", "tutorial", "manual", "documentation",
    "docs", "document", "documents", "faq", "faqs", "kb", "knowledge base",
    "policy", "policies", "terms", "conditions", "privacy",
    # Technical
    "integration", "integrations", "setup", "configuration", "configure",
    "troubleshoot", "troubleshooting", "error", "errors", "limitation",
    "limitations", "requirement", "requirements", "prerequisite", "prerequisites",
    "roadmap", "changelog", "release notes", "version", "versions",
    "compatibility", "compatible", "deprecated", "deprecation",
    "migration", "migrate", "migrating", "upgrade", "upgrading",
    "api", "api key", "api keys", "authentication", "authorization",
    "sdk", "sdks", "cli", "command line",
    # Reliability
    "status", "uptime", "sla", "service level", "incident", "incidents",
    # Marketing
    "case study", "case studies", "whitepaper", "whitepapers",
    "testimonial", "testimonials", "customer", "customers",
)

# Keywords that strongly suggest current-event / external knowledge.
# These are separated from general web keywords so the router can
# decide "web only" when none of the KB keywords match.
_CURRENT_EVENT_KEYWORDS: tuple[str, ...] = (
    # Temporal signals
    "today", "yesterday", "this week", "this month", "this year",
    "breaking", "just in", "newly", "upcoming", "trending",
    # News
    "news", "headline", "headlines", "press release", "press releases",
    "announce", "announced", "announcement", "announcements",
    # Live events
    "won", "winner", "win", "match", "game", "score", "scores",
    "election", "elections", "tournament", "championship",
    "weather", "forecast", "forecasts",
    # External platforms
    "reddit", "twitter", "linkedin", "github", "stackoverflow",
    "forum", "forums", "discussion", "discussions",
)

# General web keywords for "mixed" queries.
_WEB_KEYWORDS: tuple[str, ...] = (
    # Temporal (non-breaking)
    "latest", "recent", "current",
    # Events
    "event", "events", "conference", "conferences", "webinar", "webinars",
    "live", "stream", "streaming", "broadcast", "broadcasts",
    # Recency-sensitive
    "price", "prices", "pricing", "cost", "costs",
    "stock", "stocks", "market", "markets",
    "schedule", "schedules", "scheduled",
    "release", "releases", "released",
    "update", "updates", "updated",
    "launch", "launches", "launched",
    # Comparison
    "vs ", " versus ", "compare", "comparison", "alternative", "alternatives",
    "competitor", "competitors", "competition",
    "review", "reviews", "rating", "ratings",
    "best", "top", "list", "lists", "ranking", "rankings",
    "difference between", "what is the difference",
    # External content
    "how to", "tutorial", "tutorials", "guide", "guides",
    "example", "examples", "sample", "samples",
    "blog", "blogs", "article", "articles", "post", "posts",
    "podcast", "podcasts", "video", "videos",
    "youtube", "vimeo",
)


# ---------------------------------------------------------------------------
# SourceRouter
# ---------------------------------------------------------------------------


class SourceRouter:
    """Routes a user question to the appropriate knowledge source(s).

    The router uses intent-aware keyword heuristics.  Three outcomes:

    * **Web-only**:   Current-event keywords match, no KB keywords → web
    * **KB-only**:    KB keywords match, no current-event/web keywords → KB
    * **Both**:       Both categories match, or mixed intent is detected

    Args:
        knowledge_keywords:    Keywords for company/internal knowledge.
        web_keywords:          General web-search keywords.
        current_event_keywords: Keywords for current events / breaking news.
    """

    def __init__(
        self,
        knowledge_keywords: Sequence[str] | None = None,
        web_keywords: Sequence[str] | None = None,
        current_event_keywords: Sequence[str] | None = None,
    ) -> None:
        self._knowledge_keywords = (
            tuple(k.lower() for k in knowledge_keywords)
            if knowledge_keywords is not None
            else _KNOWLEDGE_KEYWORDS
        )
        self._web_keywords = (
            tuple(k.lower() for k in web_keywords)
            if web_keywords is not None
            else _WEB_KEYWORDS
        )
        self._current_event_keywords = (
            tuple(k.lower() for k in current_event_keywords)
            if current_event_keywords is not None
            else _CURRENT_EVENT_KEYWORDS
        )

        logger.info(
            "SourceRouter initialised "
            "(knowledge_keywords=%d, web_keywords=%d, current_event_keywords=%d).",
            len(self._knowledge_keywords),
            len(self._web_keywords),
            len(self._current_event_keywords),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def route(self, question: str) -> RoutingDecision:
        """Decide which sources to query for *question*.

        The decision is based purely on keyword matching — no I/O or
        side-effects occur.

        Args:
            question: The user's natural-language question.

        Returns:
            A :class:`RoutingDecision` with one boolean per source.

        Raises:
            ValueError: If ``question`` is empty or blank after stripping.
        """
        cleaned = (question or "").strip()
        if not cleaned:
            raise ValueError("route() requires a non-empty question string.")

        cleaned_lower = cleaned.lower()

        wants_knowledge = self._matches_any(cleaned_lower, self._knowledge_keywords)
        wants_web_general = self._matches_any(cleaned_lower, self._web_keywords)
        wants_current_event = self._matches_any(cleaned_lower, self._current_event_keywords)

        wants_web = wants_web_general or wants_current_event

        # --- Intent-aware routing ---
        if wants_current_event and not wants_knowledge:
            # Pure current-event question → web only
            decision = RoutingDecision(knowledge=False, web=True)
            logger.info(
                "SourceRouter: current-event detected for %r → web only.",
                cleaned,
            )
        elif wants_knowledge and not wants_web:
            # Pure internal question → KB only
            decision = RoutingDecision(knowledge=True, web=False)
            logger.info(
                "SourceRouter: internal query detected for %r → knowledge only.",
                cleaned,
            )
        elif wants_knowledge and wants_web:
            # Mixed → both
            decision = RoutingDecision(knowledge=True, web=True)
            logger.info(
                "SourceRouter: mixed query detected for %r → both.",
                cleaned,
            )
        elif wants_web and not wants_knowledge:
            # General web query, no KB keywords → web only
            decision = RoutingDecision(knowledge=False, web=True)
            logger.info(
                "SourceRouter: web query detected for %r → web only.",
                cleaned,
            )
        else:
            # No keywords matched at all → default to KB only
            decision = RoutingDecision(knowledge=True, web=False)
            logger.info(
                "SourceRouter: no keywords matched for %r — defaulting to knowledge=True.",
                cleaned,
            )

        return decision

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _matches_any(text: str, keywords: tuple[str, ...]) -> bool:
        """Return ``True`` if *text* contains at least one *keyword*."""
        for kw in keywords:
            if kw in text:
                return True
        return False