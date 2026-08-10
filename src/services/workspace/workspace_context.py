"""WorkspaceContext — the per-request tenant scope.

Built fresh by `workspace_resolver.resolve_workspace()` for every request
and passed down the call chain as a plain argument (mirroring how
`access_token`/`session_id`/`product_filter` already flow) — never stored
as global or process-lifetime state.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkspaceContext:
    workspace_id: str
    slug: str
    name: str
    is_default: bool = False
    logo: str | None = None
    primary_color: str | None = None
    welcome_message: str | None = None
    quick_actions: list[dict] | None = None
