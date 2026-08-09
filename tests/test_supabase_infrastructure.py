"""Tests for src/infrastructure/database/supabase.py — client caching and
the auth-bleed invariant it must never violate.

get_client()/get_admin_client() are cached singletons (connection-churn
fix); get_authenticated_client() must stay fully independent of that cache
since it mutates a client's postgrest auth headers in place — sharing the
cached anon client there would leak one user's access token into every
other concurrent request.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.infrastructure.database import supabase as supabase_module


def _clear_caches():
    supabase_module.get_client.cache_clear()
    supabase_module.get_admin_client.cache_clear()


class TestClientCaching:
    def test_get_client_returns_the_same_instance_across_calls(self):
        _clear_caches()
        with patch.object(supabase_module, "create_client", return_value=MagicMock()) as mock_create, \
             patch.dict("os.environ", {"SUPABASE_URL": "https://x.supabase.co", "SUPABASE_KEY": "anon-key"}):
            first = supabase_module.get_client()
            second = supabase_module.get_client()

        assert first is second
        mock_create.assert_called_once()

    def test_get_admin_client_returns_the_same_instance_across_calls(self):
        _clear_caches()
        with patch.object(supabase_module, "create_client", return_value=MagicMock()) as mock_create, \
             patch.dict(
                 "os.environ",
                 {"SUPABASE_URL": "https://x.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "service-key"},
             ):
            first = supabase_module.get_admin_client()
            second = supabase_module.get_admin_client()

        assert first is second
        mock_create.assert_called_once()


class TestAuthenticatedClientDoesNotLeakIntoSharedClient:
    def test_authenticated_client_is_a_different_instance_than_the_cached_anon_client(self):
        _clear_caches()
        with patch.object(supabase_module, "create_client", side_effect=lambda *a, **k: MagicMock()), \
             patch.dict("os.environ", {"SUPABASE_URL": "https://x.supabase.co", "SUPABASE_KEY": "anon-key"}):
            anon_client = supabase_module.get_client()
            authed_client = supabase_module.get_authenticated_client("user-access-token")

        assert authed_client is not anon_client

    def test_authenticating_one_user_never_mutates_the_shared_anon_client(self):
        _clear_caches()
        with patch.object(supabase_module, "create_client", side_effect=lambda *a, **k: MagicMock()), \
             patch.dict("os.environ", {"SUPABASE_URL": "https://x.supabase.co", "SUPABASE_KEY": "anon-key"}):
            anon_client = supabase_module.get_client()
            supabase_module.get_authenticated_client("some-users-token")

        anon_client.postgrest.auth.assert_not_called()

    def test_two_different_users_get_independently_authenticated_clients(self):
        _clear_caches()
        with patch.object(supabase_module, "create_client", side_effect=lambda *a, **k: MagicMock()), \
             patch.dict("os.environ", {"SUPABASE_URL": "https://x.supabase.co", "SUPABASE_KEY": "anon-key"}):
            client_a = supabase_module.get_authenticated_client("token-a")
            client_b = supabase_module.get_authenticated_client("token-b")

        assert client_a is not client_b
        client_a.postgrest.auth.assert_called_once_with("token-a")
        client_b.postgrest.auth.assert_called_once_with("token-b")
