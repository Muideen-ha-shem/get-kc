"""TenantAnalyticsService — per-workspace + platform-wide metrics (Phase 26).

Named to avoid confusion with the unrelated, in-memory-only
`src/services/advisory/analytics_service.py` (a different bounded context).
Every metric here is a fresh counting query against already-persisted
tables — no caching, no second pipeline, mirroring the exact query style
`EscalationRepository.count_active_for_agent`/`list_resolved_today_for_agent`
(Phase 25) already established.
"""

from __future__ import annotations

from typing import Any

from supabase import Client

from ...api.services.demo_requests import list_by_email
from ...sb import get_client
from ..agents.agent_repository import AgentRepository
from ..escalation.escalation_repository import EscalationRepository
from ..profile.profile_service import ProfileService


def _count(client: Client, table: str, workspace_id: str, **extra_filters: Any) -> int:
    query = client.table(table).select("id", count="exact").eq("workspace_id", workspace_id)
    for key, value in extra_filters.items():
        query = query.eq(key, value)
    response = query.execute()
    return response.count or 0


class TenantAnalyticsService:
    def __init__(
        self,
        client: Client | None = None,
        escalation_repository: EscalationRepository | None = None,
        agent_repository: AgentRepository | None = None,
    ) -> None:
        self._client = client or get_client()
        self._escalations = escalation_repository or EscalationRepository()
        self._agents = agent_repository or AgentRepository()

    def workspace_stats(self, workspace_id: str) -> dict[str, Any]:
        conversation_count = _count(self._client, "conversations", workspace_id)
        escalation_count = _count(self._client, "escalations", workspace_id)
        escalation_status_breakdown = {
            status: _count(self._client, "escalations", workspace_id, status=status)
            for status in ("waiting", "assigned", "active", "waiting_for_customer", "resolved", "closed")
        }
        appointment_count = _count(self._client, "appointments", workspace_id)
        saved_recommendation_count = _count(self._client, "saved_recommendations", workspace_id)
        saved_comparison_count = _count(self._client, "saved_comparisons", workspace_id)
        feedback_helpful_count = _count(self._client, "message_feedback", workspace_id, rating="helpful")
        feedback_not_helpful_count = _count(
            self._client, "message_feedback", workspace_id, rating="not_helpful"
        )

        return {
            "conversation_count": conversation_count,
            "escalation_count": escalation_count,
            "escalation_status_breakdown": escalation_status_breakdown,
            "appointment_count": appointment_count,
            "saved_recommendation_count": saved_recommendation_count,
            "saved_comparison_count": saved_comparison_count,
            "feedback_helpful_count": feedback_helpful_count,
            "feedback_not_helpful_count": feedback_not_helpful_count,
        }

    def platform_dashboard_stats(self, workspaces: list[Any]) -> dict[str, Any]:
        """*workspaces* is the already-fetched list of admin Workspace rows
        (from AdminWorkspaceRepository.list_all()) — avoids a second
        workspace-listing query here."""
        active_workspaces = [w for w in workspaces if w.is_active and w.deleted_at is None]

        total_conversations = 0
        total_escalations = 0
        for workspace in workspaces:
            if workspace.deleted_at is not None:
                continue
            total_conversations += _count(self._client, "conversations", workspace.id)
            total_escalations += _count(self._client, "escalations", workspace.id)

        return {
            "total_workspace_count": len([w for w in workspaces if w.deleted_at is None]),
            "active_workspace_count": len(active_workspaces),
            "total_conversation_count": total_conversations,
            "total_escalation_count": total_escalations,
            "total_agent_count": sum(
                len(self._agents.list_by_workspace(w.id)) for w in workspaces if w.deleted_at is None
            ),
        }

    def demo_requests_for_workspace_customer(self, workspace_id: str, auth_user_id: str) -> list[dict]:
        """Best-effort — demo_requests has no workspace_id/user_id column,
        matched by email only, same caveat as Phase 25's Customer Timeline."""
        profile = ProfileService().get_by_auth_user_id(auth_user_id)
        if profile is None or not profile.email:
            return []
        return list_by_email(profile.email)
