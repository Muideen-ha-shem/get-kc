"""AgentRepository — raw persistence for `support_agents` (Phase 24).

No RLS on `support_agents` (team/shared-visibility table, same precedent as
`workspaces` — see scripts/sql/009_human_support_foundation.sql), so every
method uses the plain anon-key client, like `WorkspaceRepository`.
"""

from __future__ import annotations

import logging

from supabase import Client

from ...sb import get_client
from ...shared.logging import get_logger
from .agent_models import SupportAgent

logger: logging.Logger = get_logger(__name__)

_TABLE = "support_agents"


class AgentRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def get_by_auth_user_id(self, auth_user_id: str, workspace_id: str) -> SupportAgent | None:
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
        return SupportAgent.from_row(response.data[0])

    def get_by_id(self, agent_id: str) -> SupportAgent | None:
        response = self._client.table(_TABLE).select("*").eq("id", agent_id).limit(1).execute()
        if not response.data:
            return None
        return SupportAgent.from_row(response.data[0])

    def get_or_create(
        self,
        auth_user_id: str,
        email: str,
        name: str,
        workspace_id: str,
        department: str = "General",
    ) -> SupportAgent:
        existing = self.get_by_auth_user_id(auth_user_id, workspace_id)
        if existing is not None:
            return existing
        payload = {
            "auth_user_id": auth_user_id,
            "email": email,
            "name": name,
            "workspace_id": workspace_id,
            "department": department,
        }
        response = self._client.table(_TABLE).insert(payload).execute()
        return SupportAgent.from_row(response.data[0])

    def update_status(self, agent_id: str, status: str) -> SupportAgent:
        from datetime import datetime, timezone

        response = (
            self._client.table(_TABLE)
            .update({"status": status, "updated_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", agent_id)
            .execute()
        )
        return SupportAgent.from_row(response.data[0])

    def update_department(self, agent_id: str, department: str) -> SupportAgent:
        from datetime import datetime, timezone

        response = (
            self._client.table(_TABLE)
            .update({"department": department, "updated_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", agent_id)
            .execute()
        )
        return SupportAgent.from_row(response.data[0])

    def delete(self, agent_id: str) -> None:
        """Phase 26 — admin-only removal of an agent."""
        self._client.table(_TABLE).delete().eq("id", agent_id).execute()

    def list_available(self, workspace_id: str) -> list[SupportAgent]:
        response = (
            self._client.table(_TABLE)
            .select("*")
            .eq("workspace_id", workspace_id)
            .eq("status", "available")
            .order("created_at")
            .execute()
        )
        return [SupportAgent.from_row(row) for row in response.data]

    def list_by_workspace(self, workspace_id: str) -> list[SupportAgent]:
        response = (
            self._client.table(_TABLE)
            .select("*")
            .eq("workspace_id", workspace_id)
            .order("created_at")
            .execute()
        )
        return [SupportAgent.from_row(row) for row in response.data]
