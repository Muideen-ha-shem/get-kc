"""Customer Timeline — one-screen read-only aggregation for agents (Phase 25).

Pure fan-out over services that already exist; no new persistence. Joins
are kept to what the fluent Supabase client does natively (`.in_()` on a
column) — conversation_ids are fetched first, then escalations are
filtered by them, avoiding any embedded/joined query.
"""

from __future__ import annotations

from typing import Any

from ...api.services.demo_requests import list_by_email
from ..appointments.appointment_service import AppointmentService
from ..conversation.conversation_service import ConversationService
from ..profile.profile_service import ProfileService
from ..saved_items.saved_comparison_service import SavedComparisonService
from ..saved_items.saved_recommendation_service import SavedRecommendationService
from .escalation_repository import EscalationRepository


def build_customer_timeline(
    auth_user_id: str,
    *,
    profile_service: ProfileService | None = None,
    conversation_service: ConversationService | None = None,
    saved_recommendation_service: SavedRecommendationService | None = None,
    saved_comparison_service: SavedComparisonService | None = None,
    appointment_service: AppointmentService | None = None,
    escalation_repository: EscalationRepository | None = None,
) -> dict[str, Any]:
    profile_service = profile_service or ProfileService()
    conversation_service = conversation_service or ConversationService()
    saved_recommendation_service = saved_recommendation_service or SavedRecommendationService()
    saved_comparison_service = saved_comparison_service or SavedComparisonService()
    appointment_service = appointment_service or AppointmentService()
    escalation_repository = escalation_repository or EscalationRepository()

    profile = profile_service.get_by_auth_user_id(auth_user_id)
    conversations = conversation_service.list_conversations(auth_user_id)
    conversation_ids = [c.id for c in conversations]

    demo_requests: list[dict[str, Any]] = []
    if profile is not None and profile.email:
        demo_requests = list_by_email(profile.email)

    return {
        "profile": profile,
        "conversations": conversations,
        "saved_recommendations": saved_recommendation_service.list_for_user(auth_user_id),
        "saved_comparisons": saved_comparison_service.list_for_user(auth_user_id),
        "appointments": appointment_service.list_for_user(auth_user_id),
        "past_escalations": escalation_repository.list_by_conversation_ids(conversation_ids),
        "demo_requests": demo_requests,
        "demo_requests_note": "Matched by email only — demo_requests has no direct customer link.",
    }
