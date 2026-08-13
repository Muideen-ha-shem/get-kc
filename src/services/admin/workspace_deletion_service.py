"""WorkspaceHardDeleteService — true, irreversible workspace deletion.

Deliberately separate from TenantService (which owns the reversible
lifecycle: suspend/reactivate/archive/soft-delete, all untouched by this
file) — hard delete is a fundamentally different, cross-cutting, one-way
operation and keeping it isolated avoids ballooning TenantService with
table-level deletes it otherwise has no reason to know about.

Deletion plan verified directly against scripts/sql/007/009/010/011/012/
013_*.sql (not assumed): most workspace-scoped tables declare
`workspace_id ... references workspaces(id) on delete cascade` and clean up
automatically the instant the `workspaces` row is deleted — those need zero
app code. Only the 9 tables bolted onto `workspaces` via a plain
`alter table ... add column workspace_id ... references workspaces(id)`
(007_workspace_foundation.sql, no `on delete` clause at all) don't cascade
and must be deleted explicitly before the workspace row itself. No FK blocks
any ordering among those 9 — the fixed order below exists purely for
deterministic tests, not correctness.
"""

from __future__ import annotations

from supabase import Client

from ...sb import get_admin_client
from .audit_service import AuditService
from .tenant_repository import AdminWorkspaceRepository

# Bolt-on tables from 007_workspace_foundation.sql with no ON DELETE
# cascade — must be deleted explicitly. documentation_chunks is included as
# a safety net even though most of its rows are already covered
# transitively via knowledge_document_id ON DELETE CASCADE, because its own
# workspace_id column has no cascade of its own.
_EXPLICIT_DELETE_TABLES: tuple[str, ...] = (
    "conversation_messages",
    "message_feedback",
    "conversations",
    "saved_recommendations",
    "saved_comparisons",
    "notifications",
    "appointments",
    "customer_profiles",
    "documentation_chunks",
)

_WORKSPACES_TABLE = "workspaces"


class WorkspaceDeletionConfirmationError(ValueError):
    """Raised when the caller-supplied confirmation text doesn't match the
    workspace's actual name — must be raised before any data is touched."""


class WorkspaceHardDeleteService:
    def __init__(
        self,
        client: Client | None = None,
        repo: AdminWorkspaceRepository | None = None,
        audit: AuditService | None = None,
    ) -> None:
        # Admin client, not the tenant-scoped get_client() — this operation
        # must bypass any RLS/tenant-scoping policy that would otherwise
        # block a cross-cutting bulk delete.
        self._client = client or get_admin_client()
        self._repo = repo or AdminWorkspaceRepository()
        self._audit = audit or AuditService()

    def hard_delete(self, workspace_id: str, confirm_name: str, actor_auth_user_id: str) -> None:
        workspace = self._repo.get_by_id(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace '{workspace_id}' not found")

        if confirm_name != workspace.name:
            raise WorkspaceDeletionConfirmationError("Workspace name confirmation did not match.")

        captured_id, captured_slug, captured_name = workspace.id, workspace.slug, workspace.name

        for table in _EXPLICIT_DELETE_TABLES:
            self._client.table(table).delete().eq("workspace_id", workspace_id).execute()

        self._client.table(_WORKSPACES_TABLE).delete().eq("id", workspace_id).execute()

        # workspace_id=None on the audit row itself — the workspace no
        # longer exists to reference; identifying info moves into metadata
        # so the trail still shows what was deleted.
        self._audit.record(
            "workspace.hard_deleted",
            actor_auth_user_id,
            None,
            {"deleted_workspace_id": captured_id, "slug": captured_slug, "name": captured_name},
        )
