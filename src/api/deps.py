"""FastAPI dependencies for Phase 20 authentication.

Anonymous access is the default everywhere: routes that should keep
working without a login use ``get_current_user_optional`` (returns
``None`` for missing/invalid tokens rather than raising). Only genuinely
protected routes (profile, conversations, dashboard data) use
``get_current_user_required``.
"""

from __future__ import annotations

from fastapi import Header, HTTPException

from ..services.auth.auth_service import AuthService, AuthUser

_auth_service = AuthService()


def extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization[len("bearer "):].strip()
    return token or None


def get_current_user_optional(authorization: str | None = Header(default=None)) -> AuthUser | None:
    token = extract_bearer_token(authorization)
    if not token:
        return None
    return _auth_service.get_user(token)


def get_current_user_required(authorization: str | None = Header(default=None)) -> AuthUser:
    user = get_current_user_optional(authorization)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def get_current_access_token(authorization: str | None = Header(default=None)) -> str | None:
    """The raw bearer token, when present — needed alongside ``AuthUser``
    wherever a route calls into a service that performs Row Level
    Security-protected Supabase reads/writes (profile, conversations)."""
    return extract_bearer_token(authorization)


def get_current_access_token_required(authorization: str | None = Header(default=None)) -> str:
    token = get_current_access_token(authorization)
    if token is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return token
