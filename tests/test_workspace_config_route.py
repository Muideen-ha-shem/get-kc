"""Tests for GET /workspace/config (Phase 23) and get_current_workspace_strict.

Follows test_solutions_route.py's plain-TestClient pattern for the route
tests, and test_workspace_resolver.py's mocked-repository pattern for the
dependency's branch-logic unit tests.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.deps import get_current_workspace_strict
from src.services.workspace.workspace_models import DEFAULT_WORKSPACE_SLUG, Workspace


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _ws(**overrides):
    base = {
        "id": "w1", "slug": "acme", "name": "Acme", "api_key": "valid-key", "host": "acme.example.com",
        "is_active": True, "logo": "https://acme.example.com/logo.png", "primary_color": "#0055CC",
        "welcome_message": "Welcome to Acme IQ", "quick_actions": [{"label": "Pricing", "prompt": "What does it cost?"}],
    }
    base.update(overrides)
    return Workspace(**base)


class TestWorkspaceConfigRoute:
    def test_valid_slug_query_param_returns_branding_fields(self, client):
        with patch(
            "src.api.deps._workspace_repository.get_by_slug", return_value=_ws()
        ):
            response = client.get("/workspace/config", params={"workspace_slug": "acme"})

        assert response.status_code == 200
        body = response.json()
        assert body["slug"] == "acme"
        assert body["name"] == "Acme"
        assert body["logo"] == "https://acme.example.com/logo.png"

    def test_valid_workspace_id_query_param_returns_200(self, client):
        with patch("src.api.deps._workspace_repository.get_by_id", return_value=_ws(id="w1")):
            response = client.get("/workspace/config", params={"workspace_id": "w1"})

        assert response.status_code == 200
        assert response.json()["id"] == "w1"

    def test_no_signal_falls_back_to_default_workspace(self, client):
        with patch(
            "src.api.deps._workspace_repository.get_default",
            return_value=Workspace.default(),
        ):
            response = client.get("/workspace/config")

        assert response.status_code == 200
        assert response.json()["slug"] == DEFAULT_WORKSPACE_SLUG

    def test_invalid_api_key_header_returns_401(self, client):
        with patch("src.api.deps._workspace_repository.get_by_api_key", return_value=None):
            response = client.get("/workspace/config", headers={"x-api-key": "bogus"})

        assert response.status_code == 401

    def test_inactive_workspace_api_key_returns_401(self, client):
        with patch(
            "src.api.deps._workspace_repository.get_by_api_key", return_value=_ws(is_active=False)
        ):
            response = client.get("/workspace/config", headers={"x-api-key": "disabled-key"})

        assert response.status_code == 401

    def test_invalid_host_header_returns_401(self, client):
        with patch("src.api.deps._workspace_repository.get_by_host", return_value=None):
            response = client.get("/workspace/config", headers={"host": "unknown.example.com"})

        assert response.status_code == 401

    def test_response_uses_camelcase_keys(self, client):
        with patch("src.api.deps._workspace_repository.get_by_slug", return_value=_ws()):
            response = client.get("/workspace/config", params={"workspace_slug": "acme"})

        body = response.json()
        assert "primaryColor" in body
        assert "welcomeMessage" in body
        assert "quickActions" in body
        assert "primary_color" not in body
        assert "welcome_message" not in body
        assert "quick_actions" not in body

    def test_never_leaks_internal_fields(self, client):
        with patch("src.api.deps._workspace_repository.get_by_slug", return_value=_ws()):
            response = client.get("/workspace/config", params={"workspace_slug": "acme"})

        body = response.json()
        assert "api_key" not in body
        assert "host" not in body
        assert "is_active" not in body

    def test_api_key_takes_priority_over_workspace_id_query_param(self, client):
        with patch(
            "src.api.deps._workspace_repository.get_by_api_key", return_value=_ws(id="from-key", slug="from-key-slug")
        ) as mock_get_by_key:
            response = client.get(
                "/workspace/config", params={"workspace_id": "other-id"}, headers={"x-api-key": "valid-key"}
            )

        assert response.status_code == 200
        assert response.json()["id"] == "from-key"
        mock_get_by_key.assert_called_once_with("valid-key")


class TestGetCurrentWorkspaceStrictUnit:
    """Direct unit coverage of the dependency's branch logic, bypassing
    TestClient — mirrors test_workspace_resolver.py's style."""

    def test_valid_api_key_returns_context(self):
        with patch("src.api.deps._workspace_repository.get_by_api_key", return_value=_ws()):
            ctx = get_current_workspace_strict(x_api_key="valid-key")

        assert ctx.slug == "acme"
        assert ctx.primary_color == "#0055CC"

    def test_invalid_api_key_raises_401(self):
        from fastapi import HTTPException

        with patch("src.api.deps._workspace_repository.get_by_api_key", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                get_current_workspace_strict(x_api_key="bogus")

        assert exc_info.value.status_code == 401

    def test_invalid_host_raises_401(self):
        from fastapi import HTTPException

        with patch("src.api.deps._workspace_repository.get_by_host", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                get_current_workspace_strict(host="unknown.example.com")

        assert exc_info.value.status_code == 401

    def test_no_signal_delegates_to_resolve_workspace(self):
        with patch(
            "src.api.deps.resolve_workspace", return_value="delegated-context"
        ) as mock_resolve:
            result = get_current_workspace_strict()

        assert result == "delegated-context"
        mock_resolve.assert_called_once()
