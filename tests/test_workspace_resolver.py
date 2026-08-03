"""Tests for resolve_workspace() — priority-order tenant resolution.

Repository is mocked; no network access.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from src.services.workspace.workspace_models import Workspace
from src.services.workspace.workspace_resolver import resolve_workspace


def _ws(**overrides):
    base = {"id": "w1", "slug": "acme", "name": "Acme", "api_key": None, "host": None, "is_active": True}
    base.update(overrides)
    return Workspace(**base)


class TestPriorityOrder:
    def test_explicit_workspace_id_wins_over_everything(self):
        repo = MagicMock()
        repo.get_by_id.return_value = _ws(id="w1", slug="by-id")

        ctx = resolve_workspace(
            workspace_id="w1", workspace_slug="other-slug", api_key="key", host="host", repository=repo
        )

        assert ctx.slug == "by-id"
        repo.get_by_slug.assert_not_called()
        repo.get_by_api_key.assert_not_called()
        repo.get_by_host.assert_not_called()

    def test_slug_wins_when_no_id_given(self):
        repo = MagicMock()
        repo.get_by_slug.return_value = _ws(slug="by-slug")

        ctx = resolve_workspace(
            workspace_id=None, workspace_slug="acme", api_key="key", host="host", repository=repo
        )

        assert ctx.slug == "by-slug"
        repo.get_by_api_key.assert_not_called()
        repo.get_by_host.assert_not_called()

    def test_api_key_wins_when_no_id_or_slug(self):
        repo = MagicMock()
        repo.get_by_api_key.return_value = _ws(slug="by-key")

        ctx = resolve_workspace(
            workspace_id=None, workspace_slug=None, api_key="key", host="host", repository=repo
        )

        assert ctx.slug == "by-key"
        repo.get_by_host.assert_not_called()

    def test_host_used_last(self):
        repo = MagicMock()
        repo.get_by_host.return_value = _ws(slug="by-host")

        ctx = resolve_workspace(
            workspace_id=None, workspace_slug=None, api_key=None, host="chat.acme.com", repository=repo
        )

        assert ctx.slug == "by-host"


class TestFallthrough:
    def test_unknown_slug_falls_through_to_default(self):
        repo = MagicMock()
        repo.get_by_slug.return_value = None
        repo.get_default.return_value = _ws(slug="ha-shem", id="default-id")

        ctx = resolve_workspace(
            workspace_id=None, workspace_slug="unknown", api_key=None, host=None, repository=repo
        )

        assert ctx.slug == "ha-shem"
        assert ctx.is_default is True

    def test_inactive_workspace_falls_through_to_default(self):
        repo = MagicMock()
        repo.get_by_slug.return_value = _ws(slug="disabled", is_active=False)
        repo.get_default.return_value = _ws(slug="ha-shem")

        ctx = resolve_workspace(
            workspace_id=None, workspace_slug="disabled", api_key=None, host=None, repository=repo
        )

        assert ctx.slug == "ha-shem"

    def test_no_signal_at_all_resolves_default(self):
        repo = MagicMock()
        repo.get_default.return_value = _ws(slug="ha-shem")

        ctx = resolve_workspace(
            workspace_id=None, workspace_slug=None, api_key=None, host=None, repository=repo
        )

        assert ctx.slug == "ha-shem"
        assert ctx.is_default is True
