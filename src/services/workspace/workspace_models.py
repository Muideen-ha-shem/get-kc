"""Workspace domain model.

`DEFAULT_WORKSPACE_ID` mirrors the seeded row literal in
``scripts/sql/007_workspace_foundation.sql`` exactly — keep both in sync if
either ever changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DEFAULT_WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_WORKSPACE_SLUG = "ha-shem"


@dataclass(frozen=True)
class Workspace:
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

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Workspace":
        return cls(
            id=row["id"],
            slug=row["slug"],
            name=row["name"],
            api_key=row.get("api_key"),
            host=row.get("host"),
            is_active=row.get("is_active", True),
            logo=row.get("logo"),
            primary_color=row.get("primary_color"),
            welcome_message=row.get("welcome_message"),
            quick_actions=row.get("quick_actions"),
        )

    @classmethod
    def default(cls) -> "Workspace":
        """Hardcoded fallback used when the DB row is unreachable — workspace
        resolution must never hard-fail a request."""
        return cls(id=DEFAULT_WORKSPACE_ID, slug=DEFAULT_WORKSPACE_SLUG, name="Ha-Shem")
