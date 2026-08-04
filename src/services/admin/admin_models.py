"""Admin domain models (Phase 26)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AdminWorkspace:
    """Full admin-facing view of a `workspaces` row, including the Phase 26
    lifecycle columns (archived_at/deleted_at) that the Phase 22 `Workspace`
    dataclass doesn't carry. Read/written only by AdminWorkspaceRepository —
    Phase 22's WorkspaceRepository/resolve_workspace() are untouched."""

    id: str
    slug: str
    name: str
    api_key: str | None = None
    host: str | None = None
    is_active: bool = True
    logo: str | None = None
    primary_color: str | None = None
    welcome_message: str | None = None
    quick_actions: list[dict] | None = None
    archived_at: str | None = None
    deleted_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "AdminWorkspace":
        return cls(**{field: row.get(field) for field in cls.__dataclass_fields__})


@dataclass(frozen=True)
class PlatformAdmin:
    id: str
    auth_user_id: str
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "PlatformAdmin":
        return cls(**{field: row.get(field) for field in cls.__dataclass_fields__})


@dataclass(frozen=True)
class WorkspaceProductFlag:
    id: str
    workspace_id: str
    product_id: str
    enabled: bool
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "WorkspaceProductFlag":
        return cls(**{field: row.get(field) for field in cls.__dataclass_fields__})


@dataclass(frozen=True)
class WorkspaceSettings:
    id: str
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
    working_hours: dict[str, Any] | None = None
    escalation_timeout_minutes: int | None = None
    auto_assignment_enabled: bool = True
    secondary_color: str | None = None
    chat_avatar: str | None = None
    company_name: str | None = None
    footer_text: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "WorkspaceSettings":
        return cls(**{field: row.get(field) for field in cls.__dataclass_fields__})


@dataclass(frozen=True)
class FeatureFlag:
    id: str
    workspace_id: str
    flag_key: str
    enabled: bool
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "FeatureFlag":
        return cls(**{field: row.get(field) for field in cls.__dataclass_fields__})


@dataclass(frozen=True)
class AuditLogEntry:
    id: str
    workspace_id: str | None
    actor_auth_user_id: str
    action: str
    metadata: dict[str, Any] | None
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "AuditLogEntry":
        return cls(**{field: row.get(field) for field in cls.__dataclass_fields__})
