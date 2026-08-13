"""AuditService — thin facade over AuditRepository (Phase 26). Append-only."""

from __future__ import annotations

from .admin_models import AuditLogEntry
from .audit_repository import AuditRepository


class AuditService:
    def __init__(self, repository: AuditRepository | None = None) -> None:
        self._repo = repository or AuditRepository()

    def record(
        self,
        action: str,
        actor_auth_user_id: str,
        workspace_id: str | None,
        metadata: dict | None = None,
    ) -> AuditLogEntry:
        return self._repo.insert(workspace_id, actor_auth_user_id, action, metadata)

    def list_recent(
        self,
        workspace_id: str | None = None,
        limit: int = 100,
        action: str | None = None,
        actor_auth_user_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[AuditLogEntry]:
        return self._repo.list_recent(
            workspace_id, limit, action=action, actor_auth_user_id=actor_auth_user_id,
            start_date=start_date, end_date=end_date,
        )
