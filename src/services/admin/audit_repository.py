"""AuditRepository — append-only persistence for `audit_logs` (Phase 26).

No update()/delete() method is defined anywhere in this class — append-only
by omission, not a runtime guard.
"""

from __future__ import annotations

from supabase import Client

from ...sb import get_client
from .admin_models import AuditLogEntry

_TABLE = "audit_logs"


class AuditRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def insert(
        self, workspace_id: str | None, actor_auth_user_id: str, action: str, metadata: dict | None
    ) -> AuditLogEntry:
        payload = {
            "workspace_id": workspace_id,
            "actor_auth_user_id": actor_auth_user_id,
            "action": action,
            "metadata": metadata,
        }
        response = self._client.table(_TABLE).insert(payload).execute()
        return AuditLogEntry.from_row(response.data[0])

    def list_recent(
        self,
        workspace_id: str | None,
        limit: int,
        action: str | None = None,
        actor_auth_user_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[AuditLogEntry]:
        query = self._client.table(_TABLE).select("*")
        if workspace_id is not None:
            query = query.eq("workspace_id", workspace_id)
        if action is not None:
            query = query.eq("action", action)
        if actor_auth_user_id is not None:
            query = query.eq("actor_auth_user_id", actor_auth_user_id)
        if start_date is not None:
            query = query.gte("created_at", start_date)
        if end_date is not None:
            query = query.lte("created_at", end_date)
        response = query.order("created_at", desc=True).limit(limit).execute()
        return [AuditLogEntry.from_row(row) for row in response.data]
