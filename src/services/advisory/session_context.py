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
from typing import Literal

from ...shared.cache import TTLCache
from ...shared.logging import get_logger
from ...shared.product_registry import PRODUCT_REGISTRY

logger: logging.Logger = get_logger(__name__)

# Matches "it"/"this"/"that" (whole word) used as a bare pronoun subject —
# not, say, "this" inside "this year" (still fires, deliberately broad: a
# false-positive substitution just makes the rewritten question mention a
# product name that was already the topic, which is harmless).
_PRONOUN_RE = re.compile(r"\b(it|this|that)\b", re.IGNORECASE)

# "this company"/"that platform"/etc. is a DIFFERENT reference entirely —
# it means the workspace/host itself, never the last-discussed product.
# Live-confirmed bug: with SPIDIFY as the last-discussed product, "Tell me
# the core values of this company" was rewritten to "...of this SPIDIFY
# company", so the self-identity guard downstream (which only sees the
# already-rewritten text) never recognized it as a question about the
# workspace itself. Unlike the "harmless" tradeoff noted above, this one
# actively produces a wrong answer, so it's excluded specifically.
_SELF_REFERENTIAL_NOUNS: tuple[str, ...] = (
    "company", "platform", "organization", "organisation", "business",
)

_DEFAULT_TTL_SECONDS = 1800.0  # 30 minutes of conversational inactivity


@dataclass
class PendingAction:
    """A multi-turn action workflow in progress (Phase 2 — confirmed action
    workflows). ``kind`` mirrors ``services.routing.action_intent.ActionKind``
    plus ``"demo"``. ``missing`` is the ordered queue of fields still needed;
    once empty, ``status`` flips to ``"awaiting_confirmation"`` and nothing
    is written to a real backend until the user explicitly confirms — see
    ``services.advisory.action_workflow.execute_action``, the only function
    in this feature that performs a real write."""

    kind: Literal["escalation", "appointment", "demo"]
    status: Literal["collecting_info", "awaiting_confirmation"] = "collecting_info"
    fields: dict[str, str] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    original_question: str = ""
    # Appointment only — the exact slot labels shown to the customer, so the
    # next turn's reply can be matched against real availability rather than
    # parsed with any date/time NLU.
    offered_slots: list[str] = field(default_factory=list)


@dataclass
class SessionState:
    discussed_products: list[str] = field(default_factory=list)
    recommended_products: list[str] = field(default_factory=list)
    comparisons: list[tuple[str, ...]] = field(default_factory=list)
    current_business_problem: str | None = None
    pending_action: PendingAction | None = None

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

    def get_pending_action(self, session_id: str) -> PendingAction | None:
        """The in-progress action workflow for this session, if any. Does
        NOT auto-create a session (unlike ``get()``) — a probe for a
        pending action on a session that doesn't exist yet should just
        report "none", not fabricate empty state."""
        state = self._cache.get(session_id)
        return state.pending_action if state is not None else None

    def set_pending_action(self, session_id: str, action: PendingAction | None) -> None:
        """Set or clear (``None``) the in-progress action workflow."""
        state = self.get(session_id)
        state.pending_action = action
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

        match = _PRONOUN_RE.search(question)
        if not match:
            return question

        # "this company"/"that platform"/etc. — leave untouched so the
        # self-identity guard downstream still sees the real phrase (see
        # is_self_identity_question), instead of a corrupted "this SPIDIFY
        # company"-style rewrite.
        following = question[match.end():match.end() + 20].strip().lower()
        if any(following.startswith(noun) for noun in _SELF_REFERENTIAL_NOUNS):
            return question

        last_product = state.last_product()
        if not last_product:
            return question

        resolved = _PRONOUN_RE.sub(last_product, question, count=1)
        logger.info("SessionContext: resolved %r -> %r (last product=%s).", question, resolved, last_product)
        return resolved
