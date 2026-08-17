"""TenantAnalyticsService — per-workspace + platform-wide metrics (Phase 26).

Named to avoid confusion with the unrelated, in-memory-only
`src/services/advisory/analytics_service.py` (a different bounded context).
Every metric here is a fresh counting query against already-persisted
tables — no caching, no second pipeline, mirroring the exact query style
`EscalationRepository.count_active_for_agent`/`list_resolved_today_for_agent`
(Phase 25) already established.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from supabase import Client

from ...api.services.demo_requests import list_by_email
from ...sb import get_client
from ..agents.agent_repository import AgentRepository
from ..agents.attendance_repository import AttendanceRepository
from ..escalation.escalation_repository import EscalationRepository
from ..profile.profile_service import ProfileService

# Built-in defaults, used only when a workspace hasn't configured its own
# workspace_settings.aux_categories override. AUX time is never
# automatically "unproductive" — Training/Meetings/Admin Work count as
# productive operational time, not penalized.
_DEFAULT_AUX_CATEGORIES: dict[str, str] = {
    "meeting": "productive_operational",
    "training": "productive_operational",
    "admin_work": "productive_operational",
    "customer_follow_up": "customer_service",
    "technical_issue": "non_customer_work",
    "break": "non_working",
    "lunch": "non_working",
}

# Honest limitation, not a silent gap: kb_confidence and evidence-
# sufficiency are computed per-request in SearchManager and never written
# to storage — nothing here can compute these without new, separate
# tracking infrastructure. workspace_operational_report() returns these as
# None with this note attached, and the Workspace Analyst (workspace_
# analyst.py) is instructed to say so plainly rather than guess.
_KNOWLEDGE_TRACKING_NOTE = (
    "Not tracked yet — no persistent logging exists for search queries, "
    "evidence-sufficiency outcomes, or KB confidence scores."
)


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
        attendance_repository: AttendanceRepository | None = None,
    ) -> None:
        self._client = client or get_client()
        self._escalations = escalation_repository or EscalationRepository()
        self._agents = agent_repository or AgentRepository()
        self._attendance = attendance_repository or AttendanceRepository()

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

    def workspace_operational_report(self, workspace_id: str) -> dict[str, Any]:
        """Extends workspace_stats() with resolution rate/timing, per-agent
        breakdown, and honest-effort customer/AI trend signals — everything
        here is a real query against real data; anything that would need
        new tracking infrastructure (knowledge gaps, search topics,
        insufficient-evidence questions, source failures) is returned as
        None with _KNOWLEDGE_TRACKING_NOTE rather than guessed."""
        stats = self.workspace_stats(workspace_id)
        breakdown = stats["escalation_status_breakdown"]
        resolved_count = breakdown["resolved"] + breakdown["closed"]
        resolution_rate = (resolved_count / stats["escalation_count"]) if stats["escalation_count"] else None

        resolved_rows = (
            self._client.table("escalations")
            .select("assigned_agent_id,department,created_at,resolved_at,summary")
            .eq("workspace_id", workspace_id)
            .in_("status", ["resolved", "closed"])
            .execute()
        ).data or []

        durations: list[float] = []
        department_activity: dict[str, int] = {}
        frustrated_count = 0
        for row in resolved_rows:
            created_at, resolved_at = row.get("created_at"), row.get("resolved_at")
            if created_at and resolved_at:
                created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                resolved = datetime.fromisoformat(resolved_at.replace("Z", "+00:00"))
                durations.append((resolved - created).total_seconds() / 60)
            department = row.get("department")
            if department:
                department_activity[department] = department_activity.get(department, 0) + 1
            summary = row.get("summary") or {}
            if summary.get("sentiment") == "frustrated":
                frustrated_count += 1
        average_resolution_minutes = (sum(durations) / len(durations)) if durations else None

        agents = self._agents.list_by_workspace(workspace_id)

        # First-response time — fully computable from existing data, no new
        # tracking: first agent message timestamp minus the escalation's
        # assigned_at (falling back to created_at if never separately
        # assigned), grouped per agent in one pass.
        assigned_rows = (
            self._client.table("escalations")
            .select("id,assigned_agent_id,assigned_at,created_at")
            .eq("workspace_id", workspace_id)
            .not_.is_("assigned_agent_id", "null")
            .execute()
        ).data or []
        response_minutes_by_agent: dict[str, list[float]] = {}
        if assigned_rows:
            escalation_ids = [row["id"] for row in assigned_rows]
            assigned_at_by_id = {row["id"]: row.get("assigned_at") or row.get("created_at") for row in assigned_rows}
            agent_by_escalation = {row["id"]: row["assigned_agent_id"] for row in assigned_rows}
            message_rows = (
                self._client.table("escalation_messages")
                .select("escalation_id,sender_type,created_at")
                .in_("escalation_id", escalation_ids)
                .eq("sender_type", "agent")
                .order("created_at")
                .execute()
            ).data or []
            first_agent_message: dict[str, str] = {}
            for row in message_rows:
                eid = row["escalation_id"]
                if eid not in first_agent_message:
                    first_agent_message[eid] = row["created_at"]
            for eid, first_at in first_agent_message.items():
                assigned_at = assigned_at_by_id.get(eid)
                if not assigned_at:
                    continue
                minutes = (
                    datetime.fromisoformat(first_at.replace("Z", "+00:00"))
                    - datetime.fromisoformat(assigned_at.replace("Z", "+00:00"))
                ).total_seconds() / 60
                agent_id = agent_by_escalation.get(eid)
                if agent_id:
                    response_minutes_by_agent.setdefault(agent_id, []).append(max(0.0, minutes))

        all_response_minutes = [m for values in response_minutes_by_agent.values() for m in values]
        avg_first_response_minutes = (
            sum(all_response_minutes) / len(all_response_minutes) if all_response_minutes else None
        )

        # Live AUX/session state per agent — current, not historical.
        clocked_in_count = 0
        available_count = 0
        aux_breakdown: dict[str, int] = {}
        agent_breakdown = []
        for agent in agents:
            session = self._attendance.get_active_session(agent.id)
            aux = self._attendance.get_active_aux(agent.id) if session else None
            if session is not None:
                clocked_in_count += 1
                if aux is None:
                    available_count += 1
                else:
                    aux_breakdown[aux.aux_type] = aux_breakdown.get(aux.aux_type, 0) + 1
            agent_minutes = response_minutes_by_agent.get(agent.id, [])
            agent_breakdown.append({
                "id": agent.id,
                "name": agent.name,
                "department": agent.department,
                "status": agent.status,
                "current_workload": self._escalations.count_active_for_agent(agent.id),
                "clock_in_at": session.clock_in_at if session else None,
                "current_aux": aux.aux_type if aux else None,
                "current_aux_started_at": aux.started_at if aux else None,
                "avg_first_response_minutes": (sum(agent_minutes) / len(agent_minutes)) if agent_minutes else None,
            })

        # Requested products — from saved_recommendations only (workspace-
        # scoped, unlike demo_requests which has no workspace_id column and
        # so can't be safely attributed to this workspace — see
        # demo_requests_for_workspace_customer's own caveat below).
        recommendation_rows = (
            self._client.table("saved_recommendations")
            .select("products")
            .eq("workspace_id", workspace_id)
            .execute()
        ).data or []
        requested_products: dict[str, int] = {}
        for row in recommendation_rows:
            for product in row.get("products") or []:
                requested_products[product] = requested_products.get(product, 0) + 1

        # AI-resolved-conversation rate — an honest proxy, not a precise
        # "AI fully resolved this" signal (a conversation can have an
        # escalation and still continue with AI afterward).
        escalated_conversation_ids = {
            row["conversation_id"]
            for row in (
                self._client.table("escalations")
                .select("conversation_id")
                .eq("workspace_id", workspace_id)
                .execute()
            ).data or []
            if row.get("conversation_id")
        }
        ai_resolved_rate_estimate = (
            (stats["conversation_count"] - len(escalated_conversation_ids)) / stats["conversation_count"]
            if stats["conversation_count"]
            else None
        )

        # Performance targets + AUX categorization — read straight from
        # workspace_settings, all nullable. A workspace with none configured
        # gets None targets (no fabricated benchmark) and the built-in AUX
        # category defaults.
        settings_rows = (
            self._client.table("workspace_settings")
            .select("target_resolution_rate,target_response_minutes,target_resolution_minutes,"
                     "target_csat,aux_categories,working_hours")
            .eq("workspace_id", workspace_id)
            .limit(1)
            .execute()
        ).data or []
        settings_row = settings_rows[0] if settings_rows else {}
        aux_categories = {**_DEFAULT_AUX_CATEGORIES, **(settings_row.get("aux_categories") or {})}
        aux_time_by_category: dict[str, int] = {}
        for aux_type, count in aux_breakdown.items():
            category = aux_categories.get(aux_type, "productive_operational")
            aux_time_by_category[category] = aux_time_by_category.get(category, 0) + count

        # Adherence — only when a schedule exists (workspace_settings.
        # working_hours = {"start": "HH:MM", ...}). Never inferring "late"
        # without one configured.
        working_hours = settings_row.get("working_hours") or {}
        adherence = None
        scheduled_start = working_hours.get("start")
        if scheduled_start:
            today = date.today()
            adherence = []
            for agent in agents:
                session = self._attendance.get_active_session(agent.id)
                if session is None:
                    continue
                actual = datetime.fromisoformat(session.clock_in_at.replace("Z", "+00:00"))
                scheduled = datetime.combine(
                    today, datetime.strptime(scheduled_start, "%H:%M").time(), tzinfo=timezone.utc
                )
                adherence.append({
                    "agent_id": agent.id,
                    "scheduled_start": scheduled_start,
                    "actual_clock_in_at": session.clock_in_at,
                    "difference_minutes": (actual - scheduled).total_seconds() / 60,
                })

        return {
            **stats,
            "resolution_rate": resolution_rate,
            "average_resolution_minutes": average_resolution_minutes,
            "avg_first_response_minutes": avg_first_response_minutes,
            "department_activity": department_activity,
            "frustrated_conversation_count": frustrated_count,
            "agents": agent_breakdown,
            "requested_products": requested_products,
            "ai_resolved_rate_estimate": ai_resolved_rate_estimate,
            "ai_resolved_rate_caveat": (
                "Approximate — a conversation with an escalation may still have "
                "continued with AI afterward, so this understates true AI resolution."
            ),
            "clocked_in_count": clocked_in_count,
            "available_count": available_count,
            "aux_breakdown": aux_breakdown,
            "aux_time_by_category": aux_time_by_category,
            "performance_targets": {
                "resolution_rate": settings_row.get("target_resolution_rate"),
                "response_minutes": settings_row.get("target_response_minutes"),
                "resolution_minutes": settings_row.get("target_resolution_minutes"),
                "csat": settings_row.get("target_csat"),
            },
            "adherence": adherence,
            "adherence_note": None if adherence is not None else (
                "No schedule configured for this workspace (working_hours) — adherence not computed."
            ),
            "csat_note": "No per-agent CSAT data source exists yet — not tracked.",
            "knowledge_gaps": None,
            "frequently_searched_topics": None,
            "insufficient_evidence_questions": None,
            "source_failures": None,
            "knowledge_tracking_note": _KNOWLEDGE_TRACKING_NOTE,
        }

    def demo_requests_for_workspace_customer(self, workspace_id: str, auth_user_id: str) -> list[dict]:
        """Best-effort — demo_requests has no workspace_id/user_id column,
        matched by email only, same caveat as Phase 25's Customer Timeline."""
        profile = ProfileService().get_by_auth_user_id(auth_user_id)
        if profile is None or not profile.email:
            return []
        return list_by_email(profile.email)
