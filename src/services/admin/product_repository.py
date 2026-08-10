"""ProductRepository — raw persistence for `workspace_products` (Phase 26).

Admin metadata only — does not gate live RAG/retrieval routing.
"""

from __future__ import annotations

from datetime import datetime, timezone

from supabase import Client

from ...sb import get_client
from .admin_models import WorkspaceProductFlag

_TABLE = "workspace_products"


class ProductRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def list_for_workspace(self, workspace_id: str) -> list[WorkspaceProductFlag]:
        response = (
            self._client.table(_TABLE).select("*").eq("workspace_id", workspace_id).order("product_id").execute()
        )
        return [WorkspaceProductFlag.from_row(row) for row in response.data]

    def get(self, workspace_id: str, product_id: str) -> WorkspaceProductFlag | None:
        response = (
            self._client.table(_TABLE)
            .select("*")
            .eq("workspace_id", workspace_id)
            .eq("product_id", product_id)
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        return WorkspaceProductFlag.from_row(response.data[0])

    def set_enabled(self, workspace_id: str, product_id: str, enabled: bool) -> WorkspaceProductFlag:
        existing = self.get(workspace_id, product_id)
        now = datetime.now(timezone.utc).isoformat()
        if existing is None:
            response = (
                self._client.table(_TABLE)
                .insert({"workspace_id": workspace_id, "product_id": product_id, "enabled": enabled})
                .execute()
            )
        else:
            response = (
                self._client.table(_TABLE)
                .update({"enabled": enabled, "updated_at": now})
                .eq("workspace_id", workspace_id)
                .eq("product_id", product_id)
                .execute()
            )
        return WorkspaceProductFlag.from_row(response.data[0])
