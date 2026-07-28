"""SavedRecommendationService — CRUD over ``saved_recommendations``.

Same RLS-authenticated-client pattern as ``SavedComparisonService``/
``ProfileService`` (Phase 20).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from supabase import Client

from ...sb import get_authenticated_client, get_client
from ...shared.logging import get_logger

logger: logging.Logger = get_logger(__name__)

_TABLE = "saved_recommendations"


@dataclass(frozen=True)
class SavedRecommendation:
    id: str
    user_id: str
    products: list[str]
    question: str
    recommendation: str
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "SavedRecommendation":
        return cls(**{field: row.get(field) for field in cls.__dataclass_fields__})


class SavedRecommendationService:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def _client_for(self, access_token: str | None) -> Client:
        return get_authenticated_client(access_token) if access_token else self._client

    def save(
        self,
        user_id: str,
        products: list[str],
        question: str,
        recommendation: str,
        access_token: str | None = None,
    ) -> SavedRecommendation:
        payload = {
            "user_id": user_id,
            "products": products,
            "question": question,
            "recommendation": recommendation,
        }
        response = self._client_for(access_token).table(_TABLE).insert(payload).execute()
        return SavedRecommendation.from_row(response.data[0])

    def list_for_user(self, user_id: str, access_token: str | None = None) -> list[SavedRecommendation]:
        response = (
            self._client_for(access_token)
            .table(_TABLE)
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return [SavedRecommendation.from_row(row) for row in response.data]

    def delete(self, recommendation_id: str, user_id: str, access_token: str | None = None) -> bool:
        response = (
            self._client_for(access_token)
            .table(_TABLE)
            .delete()
            .eq("id", recommendation_id)
            .eq("user_id", user_id)
            .execute()
        )
        return bool(response.data)
