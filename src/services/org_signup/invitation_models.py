"""WorkspaceInvitation domain model (Phase 28)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WorkspaceInvitation:
    id: str
    workspace_id: str
    email: str
    role: str
    department: str | None
    invited_by: str
    status: str = "pending"
    created_at: str | None = None
    accepted_at: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "WorkspaceInvitation":
        return cls(**{field: row.get(field) for field in cls.__dataclass_fields__})
