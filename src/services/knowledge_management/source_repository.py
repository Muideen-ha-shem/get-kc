"""SourceRepository — raw persistence for `knowledge_sources` (Phase 27)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from supabase import Client

from ...sb import get_client
from .km_models import KnowledgeSource

_TABLE = "knowledge_sources"


class SourceRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def list_for_workspace(self, workspace_id: str, include_archived: bool = False) -> list[KnowledgeSource]:
        query = self._client.table(_TABLE).select("*").eq("workspace_id", workspace_id)
        if not include_archived:
            query = query.is_("archived_at", "null")
        response = query.order("created_at", desc=True).execute()
        return [KnowledgeSource.from_row(row) for row in response.data]

    def get(self, source_id: str) -> KnowledgeSource | None:
        response = self._client.table(_TABLE).select("*").eq("id", source_id).limit(1).execute()
        if not response.data:
            return None
        return KnowledgeSource.from_row(response.data[0])

    def create(
        self,
        workspace_id: str,
        source_type: str,
        name: str,
        collection_id: str | None,
        config: dict[str, Any] | None,
        product: str | None,
        schedule: str,
    ) -> KnowledgeSource:
        payload = {
            "workspace_id": workspace_id, "source_type": source_type, "name": name,
            "collection_id": collection_id, "config": config, "product": product, "schedule": schedule,
        }
        response = self._client.table(_TABLE).insert(payload).execute()
        return KnowledgeSource.from_row(response.data[0])

    def update(self, source_id: str, **fields: Any) -> KnowledgeSource:
        payload = {**fields, "updated_at": datetime.now(timezone.utc).isoformat()}
        response = self._client.table(_TABLE).update(payload).eq("id", source_id).execute()
        return KnowledgeSource.from_row(response.data[0])

    def set_status(self, source_id: str, status: str) -> KnowledgeSource:
        return self.update(source_id, status=status)

    def archive(self, source_id: str) -> KnowledgeSource:
        response = (
            self._client.table(_TABLE)
            .update({"status": "archived", "archived_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", source_id)
            .execute()
        )
        return KnowledgeSource.from_row(response.data[0])

    def mark_crawled(self, source_id: str) -> None:
        self._client.table(_TABLE).update(
            {"last_crawled_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", source_id).execute()

    def mark_indexed(self, source_id: str) -> None:
        self._client.table(_TABLE).update(
            {"last_indexed_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", source_id).execute()
