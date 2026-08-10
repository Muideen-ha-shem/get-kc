"""CollectionRepository — raw persistence for `knowledge_collections` (Phase 27)."""

from __future__ import annotations

from datetime import datetime, timezone

from supabase import Client

from ...sb import get_client
from .km_models import KnowledgeCollection

_TABLE = "knowledge_collections"


class CollectionRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def list_for_workspace(self, workspace_id: str) -> list[KnowledgeCollection]:
        response = (
            self._client.table(_TABLE)
            .select("*")
            .eq("workspace_id", workspace_id)
            .is_("archived_at", "null")
            .order("name")
            .execute()
        )
        return [KnowledgeCollection.from_row(row) for row in response.data]

    def get(self, collection_id: str) -> KnowledgeCollection | None:
        response = self._client.table(_TABLE).select("*").eq("id", collection_id).limit(1).execute()
        if not response.data:
            return None
        return KnowledgeCollection.from_row(response.data[0])

    def create(self, workspace_id: str, name: str, description: str | None) -> KnowledgeCollection:
        payload = {"workspace_id": workspace_id, "name": name, "description": description}
        response = self._client.table(_TABLE).insert(payload).execute()
        return KnowledgeCollection.from_row(response.data[0])

    def archive(self, collection_id: str) -> KnowledgeCollection:
        response = (
            self._client.table(_TABLE)
            .update({"archived_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", collection_id)
            .execute()
        )
        return KnowledgeCollection.from_row(response.data[0])
