"""Tests for get_current_agent (BUG-011 fix) — identity-based workspace
resolution for /agent/* and /agents/* routes. Direct-call pattern mirrors
test_workspace_admin_role.py: pass user positionally, mock service calls."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from src.api.deps import get_current_agent
from src.services.agents.agent_models import SupportAgent
from src.services.auth.auth_service import AuthUser

_USER = AuthUser(id="u1", email="ada@example.com", full_name="Ada")


def _agent(**overrides) -> SupportAgent:
    base = {
        "id": "a1", "workspace_id": "w1", "auth_user_id": "u1", "name": "Ada",
        "email": "ada@example.com", "department": "General", "status": "available",
        "created_at": None, "updated_at": None,
    }
    base.update(overrides)
    return SupportAgent(**base)


class TestGetCurrentAgent:
    def test_returns_agent_regardless_of_which_workspace_they_belong_to(self):
        with patch(
            "src.api.deps._agent_service.get_by_auth_user_id_any_workspace",
            return_value=_agent(workspace_id="greenbank-id"),
        ):
            result = get_current_agent(user=_USER)

        assert result.workspace_id == "greenbank-id"

    def test_404s_when_user_has_no_agent_row_anywhere(self):
        with patch("src.api.deps._agent_service.get_by_auth_user_id_any_workspace", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                get_current_agent(user=_USER)

        assert exc_info.value.status_code == 404

    def test_never_calls_ambient_workspace_scoped_lookup(self):
        """Regression guard: this must not depend on get_current_workspace
        at all — that's the entire point of the fix (BUG-011)."""
        with patch(
            "src.api.deps._agent_service.get_by_auth_user_id_any_workspace", return_value=_agent()
        ) as mock_lookup:
            get_current_agent(user=_USER)

        mock_lookup.assert_called_once_with("u1")
