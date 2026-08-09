"""AdminWorkspaceRepository — admin-only reads/writes on `workspaces`
(Phase 26).

A *separate* repository from Phase 22's `WorkspaceRepository` (which stays
untouched, still owns tenant resolution only) — this one writes the same
table but exists purely for admin CRUD (create/suspend/archive/soft-delete/
regenerate-api-key), so resolution and administration never share a
write path.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from postgrest.exceptions import APIError
from supabase import Client

from ...sb import get_client
from .admin_models import AdminWorkspace

_TABLE = "workspaces"
_UNIQUE_VIOLATION = "23505"


class AdminWorkspaceRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def list_all(self) -> list[AdminWorkspace]:
        response = self._client.table(_TABLE).select("*").order("created_at").execute()
        return [AdminWorkspace.from_row(row) for row in response.data]

    def get_by_id(self, workspace_id: str) -> AdminWorkspace | None:
        response = self._client.table(_TABLE).select("*").eq("id", workspace_id).limit(1).execute()
        if not response.data:
            return None
        return AdminWorkspace.from_row(response.data[0])

    def create(self, slug: str, name: str, host: str | None = None) -> AdminWorkspace:
        payload = {
            "slug": slug,
            "name": name,
            "host": host,
            "api_key": secrets.token_urlsafe(32),
            "is_active": True,
        }
        try:
            response = self._client.table(_TABLE).insert(payload).execute()
        except APIError as exc:
            if exc.code == _UNIQUE_VIOLATION:
                raise ValueError(f"Workspace slug '{slug}' already exists") from exc
            raise
        return AdminWorkspace.from_row(response.data[0])

    def update_branding(self, workspace_id: str, **fields) -> AdminWorkspace:
        allowed = {"logo", "primary_color", "welcome_message", "quick_actions"}
        payload = {key: value for key, value in fields.items() if key in allowed}
        response = (
            self._client.table(_TABLE)
            .update({**payload, "updated_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", workspace_id)
            .execute()
        )
        return AdminWorkspace.from_row(response.data[0])

    def set_active(self, workspace_id: str, is_active: bool) -> AdminWorkspace:
        payload: dict = {"is_active": is_active, "updated_at": datetime.now(timezone.utc).isoformat()}
        if is_active:
            # Reactivating must also lift a prior archive — otherwise the
            # workspace flips is_active back to True but list/dashboard
            # views (which key off archived_at) keep showing it as archived
            # forever, since nothing else ever clears this column.
            payload["archived_at"] = None
        response = (
            self._client.table(_TABLE)
            .update(payload)
            .eq("id", workspace_id)
            .execute()
        )
        return AdminWorkspace.from_row(response.data[0])

    def archive(self, workspace_id: str) -> AdminWorkspace:
        response = (
            self._client.table(_TABLE)
            .update({"archived_at": datetime.now(timezone.utc).isoformat(), "is_active": False})
            .eq("id", workspace_id)
            .execute()
        )
        return AdminWorkspace.from_row(response.data[0])

    def soft_delete(self, workspace_id: str) -> AdminWorkspace:
        response = (
            self._client.table(_TABLE)
            .update({"deleted_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", workspace_id)
            .execute()
        )
        return AdminWorkspace.from_row(response.data[0])

    def regenerate_api_key(self, workspace_id: str) -> str:
        """Returns the new raw key. The old key is overwritten in place and
        never persisted/returned anywhere again after this call."""
        new_key = secrets.token_urlsafe(32)
        self._client.table(_TABLE).update(
            {"api_key": new_key, "updated_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", workspace_id).execute()
        return new_key
