"""SessionService — thin orchestration adapter over Phase 19's SessionContext.

SessionContext itself (in ``src/services/advisory``) already has the full
mechanism (TTL cache, pronoun resolution, discussed/recommended/compared
tracking) — it was simply never called from the live request path. This
service is the one new collaborator ChatOrchestrator depends on so it
doesn't need to know about session-id generation or SessionContext's
constructor directly; it does not duplicate any of SessionContext's logic.
"""

from __future__ import annotations

import logging
import uuid

from ...shared.logging import get_logger
from ..advisory.session_context import PendingAction, SessionContext, SessionState

logger: logging.Logger = get_logger(__name__)


class SessionService:
    def __init__(self, session_context: SessionContext | None = None) -> None:
        self._context = session_context or SessionContext()

    @staticmethod
    def new_session_id() -> str:
        return str(uuid.uuid4())

    def resolve_reference(self, session_id: str | None, question: str) -> str:
        if not session_id:
            return question
        return self._context.resolve_reference(session_id, question)

    def get_state(self, session_id: str | None) -> SessionState | None:
        if not session_id:
            return None
        return self._context.get(session_id)

    def record_products(self, session_id: str | None, products: list[str]) -> None:
        if session_id:
            self._context.record_products(session_id, products)

    def record_recommendation(self, session_id: str | None, product: str) -> None:
        if session_id:
            self._context.record_recommendation(session_id, product)

    def record_comparison(self, session_id: str | None, products: list[str]) -> None:
        if session_id:
            self._context.record_comparison(session_id, products)

    def record_business_problem(self, session_id: str | None, problem: str) -> None:
        if session_id:
            self._context.record_business_problem(session_id, problem)

    def get_pending_action(self, session_id: str | None) -> PendingAction | None:
        if not session_id:
            return None
        return self._context.get_pending_action(session_id)

    def set_pending_action(self, session_id: str | None, action: PendingAction | None) -> None:
        if session_id:
            self._context.set_pending_action(session_id, action)
