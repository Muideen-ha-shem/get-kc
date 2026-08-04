"""FastAPI dependencies for Phase 20 authentication.

Anonymous access is the default everywhere: routes that should keep
working without a login use ``get_current_user_optional`` (returns
``None`` for missing/invalid tokens rather than raising). Only genuinely
protected routes (profile, conversations, dashboard data) use
``get_current_user_required``.
"""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Query

from ..services.admin.platform_admin_service import PlatformAdminService
from ..services.auth.auth_service import AuthService, AuthUser
from ..services.workspace.workspace_context import WorkspaceContext
from ..services.workspace.workspace_repository import WorkspaceRepository
from ..services.workspace.workspace_resolver import resolve_workspace, to_context

_auth_service = AuthService()
_workspace_repository = WorkspaceRepository()
_platform_admin_service = PlatformAdminService()


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


def get_current_workspace(
    workspace_id: str | None = Query(default=None),
    workspace_slug: str | None = Query(default=None),
    x_api_key: str | None = Header(default=None),
    host: str | None = Header(default=None),
) -> WorkspaceContext:
    """Resolve the tenant for this request (Phase 22).

    Every signal is optional — omitting all of them resolves to the
    default Ha-Shem workspace, preserving pre-Phase-22 behaviour exactly.
    """
    return resolve_workspace(
        workspace_id=workspace_id,
        workspace_slug=workspace_slug,
        api_key=x_api_key,
        host=host,
        repository=_workspace_repository,
    )


def get_current_workspace_strict(
    workspace_id: str | None = Query(default=None),
    workspace_slug: str | None = Query(default=None),
    x_api_key: str | None = Header(default=None),
    x_workspace_host: str | None = Header(default=None),
) -> WorkspaceContext:
    """Strict tenant resolution for the embeddable SDK (Phase 23).

    Unlike ``get_current_workspace`` (lenient — used by ``/chat``, must
    never change), an explicitly-asserted ``x-api-key`` or
    ``x-workspace-host`` that fails to resolve to an active workspace is a
    hard 401 here: a widget embedded with a bad key must not silently
    render the default Ha-Shem workspace's data.

    Deliberately does **not** hard-validate the raw HTTP ``Host`` header
    (the ambient, mandatory header every request carries — the target
    API's own hostname, not the embedding site's origin): treating it as a
    strict signal would 401 every request that omits an api key, since
    ``Host`` is essentially never a registered workspace host in normal
    operation. ``x-workspace-host`` is the deliberate opt-in equivalent —
    a widget configured for host-based multi-tenancy sends it explicitly
    (e.g. its own page's ``location.hostname``).

    With no api_key/workspace-host signal at all (dev/testing via
    ``workspace_id``/``workspace_slug`` query params, or nothing), this
    delegates the remaining tail to the existing pure ``resolve_workspace()``
    — same lenient id/slug/host/default behaviour, no duplicated resolution
    logic.
    """
    if x_api_key:
        workspace = _workspace_repository.get_by_api_key(x_api_key)
        if workspace is None or not workspace.is_active:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return to_context(workspace)

    if x_workspace_host:
        workspace = _workspace_repository.get_by_host(x_workspace_host)
        if workspace is None or not workspace.is_active:
            raise HTTPException(status_code=401, detail="Unrecognized host")
        return to_context(workspace)

    return resolve_workspace(
        workspace_id=workspace_id,
        workspace_slug=workspace_slug,
        api_key=None,
        host=None,
        repository=_workspace_repository,
    )


def require_super_admin(user: AuthUser = Depends(get_current_user_required)) -> AuthUser:
    """Phase 26 — gates every /admin/* route. Returns the AuthUser (not
    just a bool) so route handlers get actor_auth_user_id for audit
    logging directly from the dependency, same shape as every other
    route's ``user`` param."""
    if not _platform_admin_service.is_super_admin(user.id):
        raise HTTPException(status_code=403, detail="Super admin access required")
    return user
