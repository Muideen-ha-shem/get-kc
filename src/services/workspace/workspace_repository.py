"""WorkspaceRepository — raw persistence for the `workspaces` tenant table.

`workspaces` is app metadata, not per-user data — no Row Level Security,
so every method uses the plain anon-key client (`get_client()`), unlike
the RLS-scoped repositories elsewhere in this package (conversation,
profile, etc.) that need `get_authenticated_client(access_token)`.
"""

from __future__ import annotations

import logging

from supabase import Client

from ...sb import get_client
from ...shared.logging import get_logger
from .workspace_models import Workspace

logger: logging.Logger = get_logger(__name__)

_WORKSPACES = "workspaces"


class WorkspaceRepository:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def get_by_id(self, workspace_id: str) -> Workspace | None:
        return self._first(self._client.table(_WORKSPACES).select("*").eq("id", workspace_id))

    def get_by_slug(self, slug: str) -> Workspace | None:
        return self._first(self._client.table(_WORKSPACES).select("*").eq("slug", slug))

    def get_by_api_key(self, api_key: str) -> Workspace | None:
        return self._first(self._client.table(_WORKSPACES).select("*").eq("api_key", api_key))

    def get_by_host(self, host: str) -> Workspace | None:
        return self._first(self._client.table(_WORKSPACES).select("*").eq("host", host))

    def get_default(self) -> Workspace:
        """Never raises — falls back to the hardcoded default workspace if
        the DB is unreachable or the seed row is somehow missing, so
        resolution never breaks a request.

        That hardcoded fallback carries a fixed id (DEFAULT_WORKSPACE_ID)
        that only stays valid as long as a `workspaces` row with slug
        "ha-shem" actually exists — if it's ever hard-deleted, any *write*
        that lands on this fallback (e.g. inserting a new conversation for
        an ambient/unauthenticated request) will fail its workspace_id FK
        at the database, not here. This method can't safely refuse to
        return a value (every caller in the resolve_workspace chain
        assumes a Workspace is always available), so the failure is
        surfaced as a clear log line instead — an operator seeing this
        warning knows the platform has no live default workspace and
        needs to either restore one at slug "ha-shem" or ensure every
        write path always supplies an explicit workspace signal."""
        try:
            found = self.get_by_slug(Workspace.default().slug)
        except Exception:
            logger.exception("get_default: failed to look up default workspace, using hardcoded fallback")
            return Workspace.default()
        if found is None:
            logger.warning(
                "get_default: no workspace row for slug '%s' — falling back to hardcoded id %s, "
                "which will fail any write that reaches it",
                Workspace.default().slug, Workspace.default().id,
            )
            return Workspace.default()
        return found

    @staticmethod
    def _first(query) -> Workspace | None:
        response = query.limit(1).execute()
        if not response.data:
            return None
        return Workspace.from_row(response.data[0])
