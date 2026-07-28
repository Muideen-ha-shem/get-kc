"""AuthService — thin wrapper around Supabase Auth.

Owns nothing beyond the Supabase client. All state (sessions, tokens)
lives in Supabase / the caller's browser; this service is stateless so it
composes cleanly with FastAPI's per-request dependency injection.

Anonymous access is unaffected by this module's existence — nothing here
is invoked unless a request explicitly hits an auth route or presents a
bearer token. Designed so a future ``sign_in_with_oauth`` (Google,
Microsoft) call is an additive method here, not an architecture change.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from supabase import Client

from ...sb import get_client
from ...shared.logging import get_logger

logger: logging.Logger = get_logger(__name__)


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str | None
    full_name: str | None = None


@dataclass(frozen=True)
class AuthSession:
    access_token: str
    refresh_token: str
    user: AuthUser


class AuthError(Exception):
    """Raised for any failed auth operation; message is safe to surface to the client."""


class AuthService:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def sign_up(self, email: str, password: str, full_name: str | None = None) -> AuthSession:
        credentials: dict[str, Any] = {"email": email, "password": password}
        if full_name:
            credentials["options"] = {"data": {"full_name": full_name}}
        try:
            response = self._client.auth.sign_up(credentials)
        except Exception as exc:
            logger.warning("sign_up failed: %s", exc)
            raise AuthError(str(exc)) from exc
        return self._to_session(response)

    def sign_in(self, email: str, password: str) -> AuthSession:
        try:
            response = self._client.auth.sign_in_with_password({"email": email, "password": password})
        except Exception as exc:
            logger.warning("sign_in failed: %s", exc)
            raise AuthError("Invalid email or password") from exc
        return self._to_session(response)

    def sign_out(self, access_token: str) -> None:
        """Revoke the given access token server-side.

        The API only ever receives a bearer access_token, not a full
        session (with refresh_token), so this uses the admin sign-out
        rather than reconstructing a session via ``set_session``. Requires
        the configured Supabase key to have service-role privileges; if it
        doesn't, we log and swallow the error, since the frontend clearing
        its local Supabase session already achieves sign-out for the user
        and the token will expire naturally regardless.
        """
        try:
            self._client.auth.admin.sign_out(access_token, "global")
        except Exception as exc:
            logger.warning("admin sign_out failed (non-fatal): %s", exc)

    def request_password_reset(self, email: str, redirect_to: str | None = None) -> None:
        options = {"redirect_to": redirect_to} if redirect_to else None
        try:
            self._client.auth.reset_password_for_email(email, options)
        except Exception as exc:
            logger.warning("request_password_reset failed: %s", exc)
            raise AuthError(str(exc)) from exc

    def get_user(self, access_token: str) -> AuthUser | None:
        try:
            response = self._client.auth.get_user(access_token)
        except Exception as exc:
            logger.info("get_user failed (likely expired/invalid token): %s", exc)
            return None
        if response is None or response.user is None:
            return None
        return self._to_user(response.user)

    @staticmethod
    def _to_user(user: Any) -> AuthUser:
        metadata = getattr(user, "user_metadata", None) or {}
        return AuthUser(id=user.id, email=user.email, full_name=metadata.get("full_name"))

    @classmethod
    def _to_session(cls, response: Any) -> AuthSession:
        session = response.session
        if session is None:
            raise AuthError("Check your email to confirm your account before signing in.")
        return AuthSession(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            user=cls._to_user(response.user),
        )
