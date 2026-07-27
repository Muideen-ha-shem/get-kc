"""SessionContext — in-memory, session-scoped conversation awareness.

No database, no persistence beyond the process's own memory, and no entry
outlives its TTL — reuses the same ``TTLCache`` every other in-memory cache
in this codebase (SearchManager's response cache, SemanticReranker's
embedding cache) is built on, rather than hand-rolling a second eviction
mechanism.

Not wired into the live ``/chat`` endpoint yet: doing so requires the
frontend to generate, persist, and send a session identifier with every
request (a small but real API-contract + frontend change), which is out of
scope for this pass. This is a complete, independently testable service
ready for that integration — see ``resolve_reference`` for the mechanism
that would make "How much does it cost?" resolve to the last-discussed
product once wired in.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from ...shared.cache import TTLCache
from ...shared.logging import get_logger
from ...shared.product_registry import PRODUCT_REGISTRY

logger: logging.Logger = get_logger(__name__)

# Matches "it"/"this"/"that" (whole word) used as a bare pronoun subject —
# not, say, "this" inside "this year" (still fires, deliberately broad: a
# false-positive substitution just makes the rewritten question mention a
# product name that was already the topic, which is harmless).
_PRONOUN_RE = re.compile(r"\b(it|this|that)\b", re.IGNORECASE)

_DEFAULT_TTL_SECONDS = 1800.0  # 30 minutes of conversational inactivity


@dataclass
class SessionState:
    discussed_products: list[str] = field(default_factory=list)
    recommended_products: list[str] = field(default_factory=list)
    comparisons: list[tuple[str, ...]] = field(default_factory=list)
    current_business_problem: str | None = None

    def last_product(self) -> str | None:
        return self.discussed_products[-1] if self.discussed_products else None


class SessionContext:
    """Tracks per-session conversational state — discussed products,
    recommendations, comparisons, and the current business problem.

    Args:
        ttl_seconds: How long a session stays alive after its last update.
        max_sessions: Cap on concurrently tracked sessions (oldest evicted
            first) — bounds memory use under sustained traffic.
    """

    def __init__(self, *, ttl_seconds: float = _DEFAULT_TTL_SECONDS, max_sessions: int = 2000) -> None:
        self._cache: TTLCache[str, SessionState] = TTLCache(ttl_seconds=ttl_seconds, maxsize=max_sessions)
        logger.info("SessionContext ready (ttl_seconds=%.0f, max_sessions=%d).", ttl_seconds, max_sessions)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, session_id: str) -> SessionState:
        """Return the session's state, creating a fresh one if it doesn't
        exist yet or has expired."""
        state = self._cache.get(session_id)
        if state is None:
            state = SessionState()
            self._cache.set(session_id, state)
        return state

    def record_products(self, session_id: str, products: list[str]) -> None:
        if not products:
            return
        state = self.get(session_id)
        for product in products:
            if product not in state.discussed_products:
                state.discussed_products.append(product)
        self._cache.set(session_id, state)

    def record_recommendation(self, session_id: str, product: str) -> None:
        state = self.get(session_id)
        state.recommended_products.append(product)
        self._cache.set(session_id, state)

    def record_comparison(self, session_id: str, products: list[str]) -> None:
        if len(products) < 2:
            return
        state = self.get(session_id)
        state.comparisons.append(tuple(products))
        self._cache.set(session_id, state)

    def record_business_problem(self, session_id: str, problem: str) -> None:
        state = self.get(session_id)
        state.current_business_problem = problem
        self._cache.set(session_id, state)

    def resolve_reference(self, session_id: str, question: str) -> str:
        """Rewrite a pronoun-only reference in *question* to the last
        product discussed in this session, if any. Returns *question*
        unchanged when there's nothing to resolve — no session history, no
        pronoun present, or the question already names a product itself.

        Example: session last discussed "SPIDIFY" -> "How much does it
        cost?" becomes "How much does SPIDIFY cost?"
        """
        state = self._cache.get(session_id)
        if state is None or not state.discussed_products:
            return question

        lowered = question.lower()
        if any(re.search(rf"\b{re.escape(p.lower())}\b", lowered) for p in PRODUCT_REGISTRY):
            return question  # already names a product explicitly

        if not _PRONOUN_RE.search(question):
            return question

        last_product = state.last_product()
        if not last_product:
            return question

        resolved = _PRONOUN_RE.sub(last_product, question, count=1)
        logger.info("SessionContext: resolved %r -> %r (last product=%s).", question, resolved, last_product)
        return resolved
