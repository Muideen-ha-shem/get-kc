"""Tests for require_workspace_admin (Phase 27) — super admin passes
anywhere, workspace_admin passes only their own workspace, 403 otherwise."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from fastapi import HTTPException

from src.api.deps import require_workspace_admin
from src.services.auth.auth_service import AuthUser

_USER = AuthUser(id="u1", email="ada@example.com", full_name="Ada")


class TestRequireWorkspaceAdmin:
    def test_super_admin_passes_any_workspace(self):
        with patch("src.api.deps._platform_admin_service.is_super_admin", return_value=True), \
             patch("src.api.deps._workspace_admin_service.is_workspace_admin") as mock_is_ws_admin:
            result = require_workspace_admin("w1", user=_USER)

        assert result == _USER
        mock_is_ws_admin.assert_not_called()

    def test_workspace_admin_passes_their_own_workspace(self):
        with patch("src.api.deps._platform_admin_service.is_super_admin", return_value=False), \
             patch("src.api.deps._workspace_admin_service.is_workspace_admin", return_value=True):
            result = require_workspace_admin("w1", user=_USER)

        assert result == _USER

    def test_workspace_admin_403s_for_a_different_workspace(self):
        with patch("src.api.deps._platform_admin_service.is_super_admin", return_value=False), \
             patch("src.api.deps._workspace_admin_service.is_workspace_admin", return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                require_workspace_admin("w2", user=_USER)

        assert exc_info.value.status_code == 403

    def test_non_admin_non_agent_403s(self):
        with patch("src.api.deps._platform_admin_service.is_super_admin", return_value=False), \
             patch("src.api.deps._workspace_admin_service.is_workspace_admin", return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                require_workspace_admin("w1", user=_USER)

        assert exc_info.value.status_code == 403
