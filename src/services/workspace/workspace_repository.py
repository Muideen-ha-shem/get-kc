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
        resolution never breaks a request."""
        try:
            found = self.get_by_slug(Workspace.default().slug)
        except Exception:
            logger.exception("get_default: failed to look up default workspace, using hardcoded fallback")
            return Workspace.default()
        return found if found is not None else Workspace.default()

    @staticmethod
    def _first(query) -> Workspace | None:
        response = query.limit(1).execute()
        if not response.data:
            return None
        return Workspace.from_row(response.data[0])
