"""Regression tests for the RLS bug: ``customer_profiles``/``conversations``/
``conversation_messages`` all have Row Level Security keyed on
``auth.uid()``, so a write/read through the module's own anon-key client
(with no user context attached) is denied by Postgres — this was hit live
as ``postgrest.exceptions.APIError: new row violates row-level security
policy for table "customer_profiles"`` from ``POST /auth/sign-in``.

The fix: every service method that touches these tables accepts an
``access_token`` and, when given one, performs the call through a
per-request client with that token attached via ``client.postgrest.auth()``
(``get_authenticated_client``) so ``auth.uid()`` resolves to the caller.
These tests confirm the token is actually threaded through, using a mocked
``get_authenticated_client`` rather than hitting real Supabase.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.services.conversation.conversation_repository import ConversationRepository
from src.services.profile.profile_service import ProfileService


class TestProfileServiceUsesAuthenticatedClient:
    def test_get_or_create_insert_uses_authenticated_client_when_token_given(self):
        default_client = MagicMock()
        default_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        authed_client = MagicMock()
        authed_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        authed_client.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "p1", "auth_user_id": "u1", "email": "a@b.com", "full_name": None,
             "company_name": None, "industry": None, "phone": None,
             "created_at": None, "updated_at": None, "last_login": None}
        ]

        with patch(
            "src.services.profile.profile_service.get_authenticated_client", return_value=authed_client
        ) as mock_get_authed:
            service = ProfileService(client=default_client)
            service.get_or_create("u1", "a@b.com", access_token="real-jwt")

        mock_get_authed.assert_called_with("real-jwt")
        authed_client.table.return_value.insert.assert_called_once()
        default_client.table.return_value.insert.assert_not_called()

    def test_no_token_falls_back_to_default_client(self):
        default_client = MagicMock()
        default_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        default_client.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "p1", "auth_user_id": "u1", "email": "a@b.com", "full_name": None,
             "company_name": None, "industry": None, "phone": None,
             "created_at": None, "updated_at": None, "last_login": None}
        ]
        service = ProfileService(client=default_client)

        service.get_or_create("u1", "a@b.com")

        default_client.table.return_value.insert.assert_called_once()


class TestConversationRepositoryUsesAuthenticatedClient:
    def test_create_conversation_uses_authenticated_client_when_token_given(self):
        default_client = MagicMock()
        authed_client = MagicMock()
        authed_client.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "c1", "user_id": "u1", "title": "New conversation", "created_at": None, "updated_at": None}
        ]

        with patch(
            "src.services.conversation.conversation_repository.get_authenticated_client", return_value=authed_client
        ) as mock_get_authed:
            repo = ConversationRepository(client=default_client)
            repo.create_conversation("u1", access_token="real-jwt")

        mock_get_authed.assert_called_with("real-jwt")
        authed_client.table.return_value.insert.assert_called_once()
        default_client.table.assert_not_called()
