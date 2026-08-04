"""FeatureFlagService — thin facade over FeatureFlagRepository (Phase 26)."""

from __future__ import annotations

from .admin_models import FeatureFlag
from .feature_flag_repository import FeatureFlagRepository


class FeatureFlagService:
    def __init__(self, repository: FeatureFlagRepository | None = None) -> None:
        self._repo = repository or FeatureFlagRepository()

    def list_for_workspace(self, workspace_id: str) -> list[FeatureFlag]:
        return self._repo.list_for_workspace(workspace_id)

    def set_flag(self, workspace_id: str, flag_key: str, enabled: bool) -> FeatureFlag:
        return self._repo.set_flag(workspace_id, flag_key, enabled)

    def is_enabled(self, workspace_id: str, flag_key: str, default: bool = True) -> bool:
        flag = self._repo.get(workspace_id, flag_key)
        return flag.enabled if flag is not None else default
