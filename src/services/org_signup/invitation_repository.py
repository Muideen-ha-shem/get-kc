"""InvitationRepository — raw persistence for `workspace_invitations`
(Phase 28). No RLS, same team/shared-visibility precedent as every
admin-portal table since Phase 24.
"""

from __future__ import annotations

from datetime import datetime, timezone

from postgrest.exceptions import APIError
from supabase import Client

from ...sb import get_client
from .invitation_models import WorkspaceInvitation

_TABLE = "workspace_invitations"
_UNIQUE_VIOLATION = "23505"


class InvitationRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def create(
        self, workspace_id: str, email: str, role: str, department: str | None, invited_by: str
    ) -> WorkspaceInvitation:
        payload = {
            "workspace_id": workspace_id,
            "email": email,
            "role": role,
            "department": department,
            "invited_by": invited_by,
        }
        try:
            response = self._client.table(_TABLE).insert(payload).execute()
        except APIError as exc:
            if exc.code == _UNIQUE_VIOLATION:
                raise ValueError(f"An invite is already pending for {email} in this workspace") from exc
            raise
        return WorkspaceInvitation.from_row(response.data[0])

    def get(self, invitation_id: str) -> WorkspaceInvitation | None:
        response = self._client.table(_TABLE).select("*").eq("id", invitation_id).limit(1).execute()
        if not response.data:
            return None
        return WorkspaceInvitation.from_row(response.data[0])

    def list_for_workspace(self, workspace_id: str) -> list[WorkspaceInvitation]:
        response = (
            self._client.table(_TABLE)
            .select("*")
            .eq("workspace_id", workspace_id)
            .order("created_at", desc=True)
            .execute()
        )
        return [WorkspaceInvitation.from_row(row) for row in response.data]

    def find_pending_by_email(self, email: str) -> WorkspaceInvitation | None:
        response = (
            self._client.table(_TABLE)
            .select("*")
            .eq("status", "pending")
            .ilike("email", email)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        return WorkspaceInvitation.from_row(response.data[0])

    def mark_accepted(self, invitation_id: str) -> WorkspaceInvitation:
        response = (
            self._client.table(_TABLE)
            .update({"status": "accepted", "accepted_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", invitation_id)
            .execute()
        )
        return WorkspaceInvitation.from_row(response.data[0])

    def revoke(self, invitation_id: str, workspace_id: str) -> None:
        self._client.table(_TABLE).update({"status": "revoked"}).eq("id", invitation_id).eq(
            "workspace_id", workspace_id
        ).execute()
