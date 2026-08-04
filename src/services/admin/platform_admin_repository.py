"""PlatformAdminRepository — raw persistence for `platform_admins` (Phase 26).

Global, not workspace-scoped. No RLS — app-layer check, same precedent as
`AgentRepository`/`WorkspaceRepository`.
"""

from __future__ import annotations

from supabase import Client

from ...sb import get_client
from .admin_models import PlatformAdmin

_TABLE = "platform_admins"


class PlatformAdminRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def get_by_auth_user_id(self, auth_user_id: str) -> PlatformAdmin | None:
        response = (
            self._client.table(_TABLE).select("*").eq("auth_user_id", auth_user_id).limit(1).execute()
        )
        if not response.data:
            return None
        return PlatformAdmin.from_row(response.data[0])

    def list_all(self) -> list[PlatformAdmin]:
        response = self._client.table(_TABLE).select("*").order("created_at").execute()
        return [PlatformAdmin.from_row(row) for row in response.data]

    def add(self, auth_user_id: str) -> PlatformAdmin:
        response = self._client.table(_TABLE).insert({"auth_user_id": auth_user_id}).execute()
        return PlatformAdmin.from_row(response.data[0])

    def remove(self, auth_user_id: str) -> None:
        self._client.table(_TABLE).delete().eq("auth_user_id", auth_user_id).execute()
