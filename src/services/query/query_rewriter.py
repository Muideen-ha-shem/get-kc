"""QueryRewriter — turns a natural-language question into a search-engine query.

Runs inside ``SearchManager`` right before a question is sent to the live
web search provider (Tavily/Brave). Chat questions are conversational
("What cybersecurity services does Ha-Shem offer?"); search engines respond
better to short, keyword-dense queries ("Ha-Shem Limited cybersecurity
services site:ha-shem.com"). This closes that gap.

Deterministic by design — filler-word removal, freshness-keyword detection,
company-name canonicalisation, and an optional ``site:`` hint are all plain
string/regex operations with no I/O and no LLM call, so rewriting is free
and instant on every request. Any failure (unexpected input, regex edge
case) falls back to the original, un-rewritten question rather than raising
— a broken rewrite must never break search.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from typing import Sequence

from ...shared.logging import get_logger

logger: logging.Logger = get_logger(__name__)

# Filler/auxiliary words stripped from anywhere in the question — these
# carry the question's grammar, not its search intent. Deliberately does
# NOT include freshness words ("latest", "recent", ...): those are a signal
# this rewriter surfaces explicitly, not noise to discard.
_FILLER_WORDS: frozenset[str] = frozenset({
    "what", "which", "who", "whom", "whose",
    "is", "are", "was", "were", "am", "be",
    "does", "do", "did",
    "can", "could", "will", "would", "should", "shall",
    "please", "kindly",
    "tell", "know", "explain", "give",
    "me", "us", "you", "i",
    "a", "an", "the",
    "of", "about", "for", "on",
})

_FRESHNESS_KEYWORDS: tuple[str, ...] = (
    "latest", "recent", "recently", "current", "currently", "today",
    "this week", "this month", "this year", "new", "newest", "newly",
    "breaking", "upcoming", "update", "updates", "updated",
)

_TOKEN_RE = re.compile(r"[^\s?!.,;:]+")


class QueryRewriter:
    """Rewrites a natural-language question into a concise search query.

    Args:
        company_name: Short form of the company name to detect in questions
            (e.g. ``"ha-shem"``, case-insensitive). Defaults to the
            ``COMPANY_NAME`` environment variable when not given; if that's
            also unset, company-name canonicalisation and the ``site:``
            hint are both disabled (they need a company signal to know
            when they apply).
        company_full_name: Canonical form to substitute in when
            ``company_name`` is detected but the full name isn't already
            present (e.g. ``"Ha-Shem Limited"``). Defaults to
            ``COMPANY_FULL_NAME``.
        site_hint_domain: Domain to append as a ``site:`` hint (e.g.
            ``"ha-shem.com"``) whenever ``company_name`` is detected in the
            question. Defaults to the first entry in ``OFFICIAL_DOMAINS``
            (the same variable ``SourceRanker``/``DomainQualityFilter``
            use). ``None`` disables the hint.
        filler_words: Override the default filler-word set entirely.
        products: Known product/service names to preserve verbatim (never
            touched by filler stripping since they're not in the filler
            set, but recorded so callers can inspect what was detected via
            :meth:`detect_entities`).

    Typical usage::

        rewriter = QueryRewriter(
            company_name="ha-shem",
            company_full_name="Ha-Shem Limited",
            site_hint_domain="ha-shem.com",
        )
        rewriter.rewrite("What cybersecurity services does Ha-Shem offer?")
        # -> "cybersecurity services Ha-Shem Limited offer site:ha-shem.com"
    """

    def __init__(
        self,
        *,
        company_name: str | None = None,
        company_full_name: str | None = None,
        site_hint_domain: str | None = None,
        filler_words: Sequence[str] | None = None,
        products: Sequence[str] | None = None,
    ) -> None:
        company_name = company_name if company_name is not None else os.getenv("COMPANY_NAME")
        company_full_name = (
            company_full_name if company_full_name is not None else os.getenv("COMPANY_FULL_NAME")
        )
        if site_hint_domain is None:
            official_domains = os.getenv("OFFICIAL_DOMAINS", "")
            site_hint_domain = official_domains.split(",")[0].strip() or None

        self._company_name = company_name.lower() if company_name else None
        self._company_full_name = company_full_name
        self._site_hint_domain = site_hint_domain
        self._filler_words = (
            frozenset(w.lower() for w in filler_words)
            if filler_words is not None
            else _FILLER_WORDS
        )
        self._products = tuple(products or ())

        logger.info(
            "QueryRewriter ready (company_name=%s, site_hint_domain=%s, products=%d).",
            self._company_name or "(none)",
            self._site_hint_domain or "(none)",
            len(self._products),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def rewrite(self, question: str) -> str:
        """Rewrite *question* into a search-engine-friendly query.

        Never raises — any internal error is logged and the original
        *question* is returned unchanged.

        Args:
            question: The user's natural-language question.

        Returns:
            A rewritten query string, or the original *question* if
            rewriting isn't possible/safe (empty input, internal error).
        """
        try:
            return self._rewrite(question)
        except Exception as exc:
            logger.warning("QueryRewriter: rewrite failed (%s) — using original question.", exc)
            return question

    def detect_entities(self, question: str) -> dict[str, bool | str | None]:
        """Report what this rewriter noticed in *question*, for logging/tests.

        Returns:
            A dict with ``company`` (bool), ``freshness`` (matched keyword
            or ``None``), and ``products`` (list of matched product names).
        """
        lower = (question or "").lower()
        return {
            "company": bool(self._company_name and self._company_name in lower),
            "freshness": self._detect_freshness(lower),
            "products": [p for p in self._products if p.lower() in lower],
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _rewrite(self, question: str) -> str:
        original = question or ""
        cleaned = original.strip()
        if not cleaned:
            return original

        lower = cleaned.lower()
        freshness = self._detect_freshness(lower)
        mentions_company = bool(self._company_name and self._company_name in lower)

        tokens = _TOKEN_RE.findall(cleaned)
        kept = [t for t in tokens if t.lower() not in self._filler_words]
        if not kept:
            # Filler removal ate everything (e.g. the question WAS just
            # filler) — better to fall back than send an empty query.
            return original

        text = " ".join(kept)

        if mentions_company and self._company_full_name:
            if self._company_full_name.lower() not in text.lower():
                text = re.sub(
                    re.escape(self._company_name),
                    self._company_full_name,
                    text,
                    count=1,
                    flags=re.IGNORECASE,
                )

        parts = [text]
        if freshness:
            parts.append(datetime.now().strftime("%B %Y"))
        if mentions_company and self._site_hint_domain:
            parts.append(f"site:{self._site_hint_domain}")

        rewritten = re.sub(r"\s+", " ", " ".join(parts)).strip()

        logger.info(
            "QueryRewriter: %r -> %r (freshness=%s, company=%s).",
            original,
            rewritten,
            freshness,
            mentions_company,
        )
        return rewritten or original

    @staticmethod
    def _detect_freshness(lower_question: str) -> str | None:
        for keyword in _FRESHNESS_KEYWORDS:
            if keyword in lower_question:
                return keyword
        return None
