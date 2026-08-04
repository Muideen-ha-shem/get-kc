"""QualityReportRepository — raw persistence for `knowledge_quality_reports`
(Phase 27)."""

from __future__ import annotations

from typing import Any

from supabase import Client

from ...sb import get_client
from .km_models import QualityReport

_TABLE = "knowledge_quality_reports"


class QualityReportRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def create(self, workspace_id: str, **counts: Any) -> QualityReport:
        payload = {"workspace_id": workspace_id, **counts}
        response = self._client.table(_TABLE).insert(payload).execute()
        return QualityReport.from_row(response.data[0])

    def latest_for_workspace(self, workspace_id: str) -> QualityReport | None:
        response = (
            self._client.table(_TABLE)
            .select("*")
            .eq("workspace_id", workspace_id)
            .order("generated_at", desc=True)
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        return QualityReport.from_row(response.data[0])
