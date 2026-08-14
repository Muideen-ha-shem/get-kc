"""WorkspaceSettingsRepository — raw persistence for `workspace_settings`
(Phase 26). One row per workspace."""

from __future__ import annotations

from datetime import datetime, timezone

from supabase import Client

from ...sb import get_client
from .admin_models import WorkspaceSettings

_TABLE = "workspace_settings"

_UPDATABLE_FIELDS = {
    "ai_enabled", "confidence_threshold", "live_search_enabled", "human_escalation_enabled",
    "ai_personality", "welcome_prompt", "chat_enabled", "offline_mode", "greeting_message",
    "working_hours", "escalation_timeout_minutes", "auto_assignment_enabled", "secondary_color",
    "chat_avatar", "company_name", "footer_text",
    # Agent Operations (Phase 29) — all nullable; a workspace with none of
    # these configured simply shows no target comparison / uses the
    # built-in AUX category defaults (see tenant_analytics_service.py).
    "target_resolution_rate", "target_response_minutes", "target_resolution_minutes",
    "target_csat", "aux_categories",
}


class WorkspaceSettingsRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def get_by_workspace_id(self, workspace_id: str) -> WorkspaceSettings | None:
        response = (
            self._client.table(_TABLE).select("*").eq("workspace_id", workspace_id).limit(1).execute()
        )
        if not response.data:
            return None
        return WorkspaceSettings.from_row(response.data[0])

    def create_default(self, workspace_id: str) -> WorkspaceSettings:
        response = self._client.table(_TABLE).insert({"workspace_id": workspace_id}).execute()
        return WorkspaceSettings.from_row(response.data[0])

    def upsert(self, workspace_id: str, **fields) -> WorkspaceSettings:
        payload = {key: value for key, value in fields.items() if key in _UPDATABLE_FIELDS}
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        existing = self.get_by_workspace_id(workspace_id)
        if existing is None:
            response = self._client.table(_TABLE).insert({**payload, "workspace_id": workspace_id}).execute()
        else:
            response = (
                self._client.table(_TABLE).update(payload).eq("workspace_id", workspace_id).execute()
            )
        return WorkspaceSettings.from_row(response.data[0])
