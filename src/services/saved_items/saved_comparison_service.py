"""SavedComparisonService — CRUD over ``saved_comparisons``.

Same RLS-authenticated-client pattern as ``ProfileService``/
``ConversationRepository`` (Phase 20): ``saved_comparisons`` has Row Level
Security keyed on ``auth.uid()``, so every call needs the caller's access
token — see ``get_authenticated_client``'s docstring for why the module's
own anon-key client can't perform these reads/writes on its own.

Deliberately does not duplicate any comparison *logic* — this only persists
the product-id selection a comparison was built from; reopening it replays
those ids through the existing ``CompareSolutionsModal``/``PRODUCT_REGISTRY``
on the frontend.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from supabase import Client

from ...sb import get_authenticated_client, get_client
from ...shared.logging import get_logger

logger: logging.Logger = get_logger(__name__)

_TABLE = "saved_comparisons"


@dataclass(frozen=True)
class SavedComparison:
    id: str
    user_id: str
    product_ids: list[str]
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "SavedComparison":
        return cls(**{field: row.get(field) for field in cls.__dataclass_fields__})


class SavedComparisonService:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def _client_for(self, access_token: str | None) -> Client:
        return get_authenticated_client(access_token) if access_token else self._client

    def save(self, user_id: str, product_ids: list[str], access_token: str | None = None) -> SavedComparison:
        payload = {"user_id": user_id, "product_ids": product_ids}
        response = self._client_for(access_token).table(_TABLE).insert(payload).execute()
        return SavedComparison.from_row(response.data[0])

    def list_for_user(self, user_id: str, access_token: str | None = None) -> list[SavedComparison]:
        response = (
            self._client_for(access_token)
            .table(_TABLE)
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return [SavedComparison.from_row(row) for row in response.data]

    def delete(self, comparison_id: str, user_id: str, access_token: str | None = None) -> bool:
        response = (
            self._client_for(access_token)
            .table(_TABLE)
            .delete()
            .eq("id", comparison_id)
            .eq("user_id", user_id)
            .execute()
        )
        return bool(response.data)
