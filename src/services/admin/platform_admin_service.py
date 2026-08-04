"""PlatformAdminService — thin facade over PlatformAdminRepository (Phase 26).

`is_super_admin` backs the `require_super_admin` FastAPI dependency.
"""

from __future__ import annotations

from .admin_models import PlatformAdmin
from .platform_admin_repository import PlatformAdminRepository


class PlatformAdminService:
    def __init__(self, repository: PlatformAdminRepository | None = None) -> None:
        self._repo = repository or PlatformAdminRepository()

    def is_super_admin(self, auth_user_id: str) -> bool:
        return self._repo.get_by_auth_user_id(auth_user_id) is not None

    def list_admins(self) -> list[PlatformAdmin]:
        return self._repo.list_all()

    def add_admin(self, auth_user_id: str) -> PlatformAdmin:
        return self._repo.add(auth_user_id)

    def remove_admin(self, auth_user_id: str) -> None:
        self._repo.remove(auth_user_id)
