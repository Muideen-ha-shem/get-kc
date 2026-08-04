"""WorkspaceAdminRepository — raw persistence for `workspace_admins`
(Phase 27). Mirrors PlatformAdminRepository/AgentRepository's exact shape."""

from __future__ import annotations

from supabase import Client

from ...sb import get_client

_TABLE = "workspace_admins"


class WorkspaceAdminRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def get_by_auth_user_id(self, auth_user_id: str, workspace_id: str):
        response = (
            self._client.table(_TABLE)
            .select("*")
            .eq("auth_user_id", auth_user_id)
            .eq("workspace_id", workspace_id)
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        return response.data[0]

    def list_for_workspace(self, workspace_id: str) -> list[dict]:
        response = self._client.table(_TABLE).select("*").eq("workspace_id", workspace_id).execute()
        return response.data

    def add(self, workspace_id: str, auth_user_id: str) -> dict:
        response = (
            self._client.table(_TABLE)
            .insert({"workspace_id": workspace_id, "auth_user_id": auth_user_id})
            .execute()
        )
        return response.data[0]

    def remove(self, workspace_id: str, auth_user_id: str) -> None:
        self._client.table(_TABLE).delete().eq("workspace_id", workspace_id).eq(
            "auth_user_id", auth_user_id
        ).execute()
