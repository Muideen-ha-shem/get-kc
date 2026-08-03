"""SupportAgent domain model (Phase 24)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SupportAgent:
    id: str
    workspace_id: str
    auth_user_id: str
    name: str
    email: str
    department: str
    status: str  # "available" | "away" | "offline"
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "SupportAgent":
        return cls(**{field: row.get(field) for field in cls.__dataclass_fields__})
