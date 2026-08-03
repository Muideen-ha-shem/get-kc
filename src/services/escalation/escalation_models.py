"""Escalation domain models (Phase 24 + Phase 25)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Escalation:
    id: str
    workspace_id: str
    conversation_id: str | None
    status: str
    assigned_agent_id: str | None
    trigger_reason: str
    department: str | None
    summary: dict[str, Any] | None
    created_at: str | None = None
    assigned_at: str | None = None
    resolved_at: str | None = None
    closed_at: str | None = None
    ai_engaged: bool = True

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Escalation":
        return cls(**{field: row.get(field) for field in cls.__dataclass_fields__})


@dataclass(frozen=True)
class EscalationMessage:
    id: str
    escalation_id: str
    sender_type: str
    sender_auth_user_id: str | None
    content: str
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "EscalationMessage":
        return cls(**{field: row.get(field) for field in cls.__dataclass_fields__})
