"""FeatureFlagRepository — raw persistence for `feature_flags` (Phase 26)."""

from __future__ import annotations

from datetime import datetime, timezone

from supabase import Client

from ...sb import get_client
from .admin_models import FeatureFlag

_TABLE = "feature_flags"


class FeatureFlagRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def list_for_workspace(self, workspace_id: str) -> list[FeatureFlag]:
        response = (
            self._client.table(_TABLE).select("*").eq("workspace_id", workspace_id).order("flag_key").execute()
        )
        return [FeatureFlag.from_row(row) for row in response.data]

    def get(self, workspace_id: str, flag_key: str) -> FeatureFlag | None:
        response = (
            self._client.table(_TABLE)
            .select("*")
            .eq("workspace_id", workspace_id)
            .eq("flag_key", flag_key)
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        return FeatureFlag.from_row(response.data[0])

    def set_flag(self, workspace_id: str, flag_key: str, enabled: bool) -> FeatureFlag:
        existing = self.get(workspace_id, flag_key)
        now = datetime.now(timezone.utc).isoformat()
        if existing is None:
            response = (
                self._client.table(_TABLE)
                .insert({"workspace_id": workspace_id, "flag_key": flag_key, "enabled": enabled})
                .execute()
            )
        else:
            response = (
                self._client.table(_TABLE)
                .update({"enabled": enabled, "updated_at": now})
                .eq("workspace_id", workspace_id)
                .eq("flag_key", flag_key)
                .execute()
            )
        return FeatureFlag.from_row(response.data[0])
