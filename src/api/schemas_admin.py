"""Pydantic schemas for the /admin/* surface (Phase 26).

Kept in a separate file from schemas.py (already 415+ lines after Phases
20-25) — a ~20-endpoint admin surface adds a comparable number of request/
response models, and keeping them together here is easier to review/
maintain than pushing schemas.py substantially larger.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class WorkspaceAdminSchema(BaseModel):
    id: str
    slug: str
    name: str
    host: str | None = None
    is_active: bool
    logo: str | None = None
    primary_color: str | None = None
    welcome_message: str | None = None
    quick_actions: list[dict] | None = None
    archived_at: str | None = None
    deleted_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class WorkspaceCreateRequest(BaseModel):
    slug: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    host: str | None = None


class WorkspaceCreateResponse(BaseModel):
    """The one and only place a newly-created workspace's raw api_key is
    ever returned — never re-displayed after this response."""

    workspace: WorkspaceAdminSchema
    api_key: str


class WorkspaceBrandingUpdateRequest(BaseModel):
    logo: str | None = None
    primary_color: str | None = None
    welcome_message: str | None = None
    quick_actions: list[dict] | None = None


class WorkspaceSettingsSchema(BaseModel):
    workspace_id: str
    ai_enabled: bool = True
    confidence_threshold: float | None = None
    live_search_enabled: bool = True
    human_escalation_enabled: bool = True
    ai_personality: str | None = None
    welcome_prompt: str | None = None
    chat_enabled: bool = True
    offline_mode: bool = False
    greeting_message: str | None = None
    working_hours: dict | None = None
    escalation_timeout_minutes: int | None = None
    auto_assignment_enabled: bool = True
    secondary_color: str | None = None
    chat_avatar: str | None = None
    company_name: str | None = None
    footer_text: str | None = None


class WorkspaceSettingsUpdateRequest(BaseModel):
    ai_enabled: bool | None = None
    confidence_threshold: float | None = None
    live_search_enabled: bool | None = None
    human_escalation_enabled: bool | None = None
    ai_personality: str | None = None
    welcome_prompt: str | None = None
    chat_enabled: bool | None = None
    offline_mode: bool | None = None
    greeting_message: str | None = None
    working_hours: dict | None = None
    escalation_timeout_minutes: int | None = None
    auto_assignment_enabled: bool | None = None
    secondary_color: str | None = None
    chat_avatar: str | None = None
    company_name: str | None = None
    footer_text: str | None = None


class WorkspaceProductSchema(BaseModel):
    product_id: str
    enabled: bool


class WorkspaceProductsUpdateRequest(BaseModel):
    products: list[WorkspaceProductSchema]


class FeatureFlagSchema(BaseModel):
    flag_key: str
    enabled: bool


class FeatureFlagsUpdateRequest(BaseModel):
    flags: list[FeatureFlagSchema]


class ApiKeyRegenerateResponse(BaseModel):
    api_key: str


class WorkspaceAnalyticsSchema(BaseModel):
    conversation_count: int
    escalation_count: int
    escalation_status_breakdown: dict[str, int]
    appointment_count: int
    saved_recommendation_count: int
    saved_comparison_count: int
    feedback_helpful_count: int
    feedback_not_helpful_count: int


class PlatformDashboardSchema(BaseModel):
    total_workspace_count: int
    active_workspace_count: int
    total_conversation_count: int
    total_escalation_count: int
    total_agent_count: int


class AuditLogEntrySchema(BaseModel):
    id: str
    workspace_id: str | None
    actor_auth_user_id: str
    action: str
    metadata: dict | None
    created_at: str | None = None


class AdminUserSchema(BaseModel):
    id: str
    email: str | None
    full_name: str | None = None


class RoleAssignmentRequest(BaseModel):
    role: Literal["agent", "admin", "workspace_admin"]
    workspace_id: str | None = None
    department: str | None = None
    name: str | None = None
    email: str | None = None


class AgentPerformanceSchema(BaseModel):
    agent_id: str
    active_chats: int
    resolved_today: int
    satisfaction_score: float | None = Field(
        None, description="Not computed — no message_feedback<->agent linkage exists. Always null."
    )
