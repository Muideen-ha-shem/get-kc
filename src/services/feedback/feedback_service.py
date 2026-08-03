"""FeedbackService — 👍/👎 + optional comment on a chat answer.

Public feature (no RLS, no auth required to submit) — same precedent as
``demo_requests``/``appointments``: anonymous visitors can rate a response
too. ``user_id`` is recorded when the rater happens to be signed in, but
submitting feedback never requires it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from supabase import Client

from ...sb import get_client
from ...services.workspace.workspace_models import DEFAULT_WORKSPACE_ID
from ...shared.logging import get_logger

logger: logging.Logger = get_logger(__name__)

_TABLE = "message_feedback"

Rating = str  # "helpful" | "not_helpful"


@dataclass(frozen=True)
class Feedback:
    id: str
    question: str
    answer: str
    rating: str
    comment: str | None = None
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Feedback":
        return cls(**{field: row.get(field) for field in cls.__dataclass_fields__})


class FeedbackService:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def submit(
        self,
        question: str,
        answer: str,
        rating: Rating,
        comment: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        conversation_id: str | None = None,
        workspace_id: str = DEFAULT_WORKSPACE_ID,
    ) -> Feedback:
        payload = {
            "question": question,
            "answer": answer,
            "rating": rating,
            "comment": comment,
            "user_id": user_id,
            "session_id": session_id,
            "conversation_id": conversation_id,
            "workspace_id": workspace_id,
        }
        response = self._client.table(_TABLE).insert(payload).execute()
        return Feedback.from_row(response.data[0])
