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

    def list_for_auth_user_id(self, auth_user_id: str) -> list[dict]:
        """Every workspace this user administers — identity-first lookup
        (Phase 28), same rationale as AgentRepository's
        get_by_auth_user_id_any_workspace: a signed-in workspace_admin's
        own dashboard has no ambient workspace context to check against,
        so discovering "which workspace(s) am I an admin of" has to be
        resolved from the user's own membership rows, not request context.
        """
        response = self._client.table(_TABLE).select("*").eq("auth_user_id", auth_user_id).execute()
        return response.data

    def add(self, workspace_id: str, auth_user_id: str) -> dict:
        existing = self.get_by_auth_user_id(auth_user_id, workspace_id)
        if existing is not None:
            return existing
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
