"""SourceRouter — decides which knowledge sources to consult for a question.

This module contains two main exports:

* :class:`RoutingDecision` — a simple data object with one boolean per source.
* :class:`SourceRouter` — the router itself, which examines a user question
  and returns a :class:`RoutingDecision`.

How it works
------------
The router uses a set of **keyword heuristics** to decide whether a question
should consult the internal knowledge base, live web search, or both.  The
heuristic lists are configuration-driven (passed at construction time) so they
can be tuned without modifying code.

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
    "service", "services", "product", "products", "solution", "solutions",
    "pricing", "price", "cost", "offer", "offers", "offering", "offerings",
    "capability", "capabilities", "feature", "features",
    "company", "about", "mission", "vision", "team", "history",
    "contact", "located", "location", "address", "office", "offices",
    "founded", "founding", "founder", "founders", "ceo",
    "support", "help", "guide", "tutorial", "manual", "documentation",
    "docs", "document", "documents", "faq", "faqs", "kb", "knowledge base",
    "policy", "policies", "terms", "conditions", "privacy",
    "integration", "integrations", "setup", "configuration", "configure",
    "troubleshoot", "troubleshooting", "error", "errors", "limitation",
    "limitations", "requirement", "requirements", "prerequisite", "prerequisites",
    "roadmap", "changelog", "release notes", "version", "versions",
    "compatibility", "compatible", "deprecated", "deprecation",
    "migration", "migrate", "migrating", "upgrade", "upgrading",
    "api", "api key", "api keys", "authentication", "authorization",
    "sdk", "sdks", "cli", "command line",
    "status", "uptime", "sla", "service level", "incident", "incidents",
    "case study", "case studies", "whitepaper", "whitepapers",
    "testimonial", "testimonials", "customer", "customers",
)

_WEB_KEYWORDS: tuple[str, ...] = (
    "latest", "recent", "current", "today", "yesterday",
    "this week", "this month", "this year",
    "breaking", "just in", "newly", "upcoming", "trending",
    "news", "headline", "headlines", "announce", "announced", "announcement",
    "announcements", "press release", "press releases", "event", "events",
    "conference", "conferences", "webinar", "webinars",
    "price", "prices", "pricing", "cost", "costs",
    "stock", "stocks", "market", "markets",
    "weather", "forecast", "forecasts",
    "schedule", "schedules", "scheduled",
    "release", "releases", "released",
    "update", "updates", "updated",
    "launch", "launches", "launched",
    "vs ", " versus ", "compare", "comparison", "alternative", "alternatives",
    "competitor", "competitors", "competition",
    "review", "reviews", "rating", "ratings",
    "best", "top", "list", "lists", "ranking", "rankings",
    "how to", "tutorial", "tutorials", "guide", "guides",
    "example", "examples", "sample", "samples",
    "difference between", "what is the difference",
    "reddit", "twitter", "linkedin", "github", "stackoverflow",
    "forum", "forums", "discussion", "discussions",
    "blog", "blogs", "article", "articles", "post", "posts",
    "podcast", "podcasts", "video", "videos",
    "youtube", "vimeo",
)


# ---------------------------------------------------------------------------
# SourceRouter
# ---------------------------------------------------------------------------


class SourceRouter:
    """Routes a user question to the appropriate knowledge source(s).

    The router uses keyword heuristics to decide whether a question should
    consult the internal knowledge base, live web search, or both.  The
    keyword lists can be overridden at construction time for customisation.

    Args:
        knowledge_keywords: Iterable of keywords (case-insensitive) that
            suggest the question is about the internal knowledge base.
            Defaults to ``_KNOWLEDGE_KEYWORDS``.
        web_keywords: Iterable of keywords (case-insensitive) that suggest
            the question needs a live web search.
            Defaults to ``_WEB_KEYWORDS``.
    """

    def __init__(
        self,
        knowledge_keywords: Sequence[str] | None = None,
        web_keywords: Sequence[str] | None = None,
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

        logger.debug(
            "SourceRouter initialised (knowledge_keywords=%d, web_keywords=%d).",
            len(self._knowledge_keywords),
            len(self._web_keywords),
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
        wants_web = self._matches_any(cleaned_lower, self._web_keywords)

        # If nothing matched, default to consulting the knowledge base only
        if not wants_knowledge and not wants_web:
            wants_knowledge = True
            logger.info(
                "SourceRouter: no keywords matched for %r — defaulting to knowledge=True.",
                cleaned,
            )

        decision = RoutingDecision(knowledge=wants_knowledge, web=wants_web)
        logger.info("SourceRouter: %r -> %s", cleaned, decision.to_dict())
        return decision

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _matches_any(text: str, keywords: tuple[str, ...]) -> bool:
        """Return ``True`` if *text* contains at least one *keyword*.

        Keywords ending with a space (e.g. ``"vs "``) use the trailing
        space as a natural word-boundary guard — they match ``"A vs B"``
        but not ``"vsphere"``.  All other keywords use simple substring
        matching.
        """
        for kw in keywords:
            if kw in text:
                return True
        return False
