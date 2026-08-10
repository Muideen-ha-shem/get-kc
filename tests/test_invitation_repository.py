"""Tests for InvitationRepository (Phase 28) — mocked Supabase client."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from postgrest.exceptions import APIError

from src.services.org_signup.invitation_repository import InvitationRepository


def _row(**overrides):
    base = {
        "id": "i1", "workspace_id": "w1", "email": "teammate@acme.com", "role": "agent",
        "department": "Support", "invited_by": "u1", "status": "pending",
        "created_at": None, "accepted_at": None,
    }
    base.update(overrides)
    return base


class TestInvitationRepository:
    def test_create_inserts_row(self):
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.return_value.data = [_row()]
        repo = InvitationRepository(client=client)

        invitation = repo.create("w1", "teammate@acme.com", "agent", "Support", "u1")

        assert invitation.email == "teammate@acme.com"
        client.table.return_value.insert.assert_called_once_with(
            {
                "workspace_id": "w1", "email": "teammate@acme.com", "role": "agent",
                "department": "Support", "invited_by": "u1",
            }
        )

    def test_create_duplicate_pending_raises_value_error(self):
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.side_effect = APIError(
            {"message": "duplicate key", "code": "23505"}
        )
        repo = InvitationRepository(client=client)

        with pytest.raises(ValueError, match="already pending"):
            repo.create("w1", "teammate@acme.com", "agent", "Support", "u1")

    def test_create_other_api_error_propagates(self):
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.side_effect = APIError(
            {"message": "boom", "code": "99999"}
        )
        repo = InvitationRepository(client=client)

        with pytest.raises(APIError):
            repo.create("w1", "teammate@acme.com", "agent", "Support", "u1")

    def test_find_pending_by_email_returns_none_when_missing(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.ilike.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        repo = InvitationRepository(client=client)

        assert repo.find_pending_by_email("nobody@acme.com") is None

    def test_mark_accepted_updates_status(self):
        client = MagicMock()
        client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            _row(status="accepted", accepted_at="2026-01-01T00:00:00Z")
        ]
        repo = InvitationRepository(client=client)

        result = repo.mark_accepted("i1")

        assert result.status == "accepted"

    def test_revoke_scopes_by_workspace_id(self):
        client = MagicMock()
        repo = InvitationRepository(client=client)

        repo.revoke("i1", "w1")

        client.table.return_value.update.return_value.eq.return_value.eq.assert_called_once_with(
            "workspace_id", "w1"
        )
