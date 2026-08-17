"""WorkSession/AuxEvent domain models — Agent Operations (clock in/out, AUX)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WorkSession:
    id: str
    workspace_id: str
    agent_id: str
    work_date: str
    clock_in_at: str
    clock_out_at: str | None
    total_work_seconds: int | None
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "WorkSession":
        return cls(**{field: row.get(field) for field in cls.__dataclass_fields__})


@dataclass(frozen=True)
class AuxEvent:
    id: str
    workspace_id: str
    agent_id: str
    work_session_id: str
    aux_type: str
    started_at: str
    ended_at: str | None
    duration_seconds: int | None
    reason: str | None
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "AuxEvent":
        return cls(**{field: row.get(field) for field in cls.__dataclass_fields__})
