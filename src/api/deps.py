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
from ..services.admin.workspace_admin_service import WorkspaceAdminService
from ..services.agents.agent_models import SupportAgent
from ..services.agents.agent_service import AgentService
from ..services.auth.auth_service import AuthService, AuthUser
from ..services.profile.profile_service import ProfileService
from ..services.workspace.workspace_context import WorkspaceContext
from ..services.workspace.workspace_repository import WorkspaceRepository
from ..services.workspace.workspace_resolver import resolve_workspace, to_context

_auth_service = AuthService()
_workspace_repository = WorkspaceRepository()
_platform_admin_service = PlatformAdminService()
_workspace_admin_service = WorkspaceAdminService()
_agent_service = AgentService()
_profile_service = ProfileService()


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


def get_current_chat_workspace(
    workspace_id: str | None = Query(default=None),
    workspace_slug: str | None = Query(default=None),
    x_api_key: str | None = Header(default=None),
    host: str | None = Header(default=None),
    user: AuthUser | None = Depends(get_current_user_optional),
    access_token: str | None = Depends(get_current_access_token),
) -> WorkspaceContext:
    """Tenant resolution for ``/chat`` and ``/chat/escalate`` — an
    authenticated customer's own workspace (from their ``customer_profiles``
    row) takes priority over ambient request signals.

    The public embeddable widget (anonymous, api-key/host-identified) and
    the authenticated customer dashboard both hit these two routes, but
    only the widget ever sends a workspace-identifying signal — the
    dashboard's chat call sends none (no ``workspace_id``, no
    ``x-api-key``, no host hint). Falling through to
    ``get_current_workspace``'s lenient default in that case silently
    served every non-Ha-Shem customer Ha-Shem's own knowledge base and
    products, a critical cross-tenant leak caught via live QA (a signed-in
    GreenBank Microfinance customer got confident, cited answers about
    Ha-Shem's actual SPIDIFY/ZivaAIRA product docs). Resolving identity
    first closes that gap without changing anything about the anonymous
    widget path below, which still falls through to the exact same
    ``resolve_workspace()`` ``get_current_workspace`` already used —
    unauthenticated requests behave identically to before.
    """
    if user is not None:
        try:
            profile = _profile_service.get_by_auth_user_id(user.id, access_token=access_token)
        except Exception:
            profile = None
        if profile is not None and profile.workspace_id:
            workspace = _workspace_repository.get_by_id(profile.workspace_id)
            if workspace is not None and workspace.is_active:
                return to_context(workspace)

    return resolve_workspace(
        workspace_id=workspace_id,
        workspace_slug=workspace_slug,
        api_key=x_api_key,
        host=host,
        repository=_workspace_repository,
    )


def get_current_agent(user: AuthUser = Depends(get_current_user_required)) -> SupportAgent:
    """Resolves the signed-in user's own agent identity — the workspace an
    agent operates in is an inherent property of who they are (their
    ``support_agents`` row), not something the request needs to assert.

    Every ``/agent/*`` and ``/agents/*`` route used to depend on
    ``get_current_workspace`` (Phase 22's lenient *request-context*
    resolver — query params/host/api-key) for this, but the authenticated
    agent dashboard never sends any of those signals. That silently
    resolved every agent to the default Ha-Shem workspace regardless of
    which workspace they actually belong to — for non-Ha-Shem agents this
    either 404'd or, worse, ``get_or_create``'d a spurious duplicate agent
    row under the wrong workspace. This dependency looks the agent up by
    identity instead, so the resolved workspace is always their real one.
    404s if the signed-in user has no ``support_agents`` row at all.
    """
    agent = _agent_service.get_by_auth_user_id_any_workspace(user.id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Not a registered agent")
    return agent


def require_super_admin(user: AuthUser = Depends(get_current_user_required)) -> AuthUser:
    """Phase 26 — gates every /admin/* route. Returns the AuthUser (not
    just a bool) so route handlers get actor_auth_user_id for audit
    logging directly from the dependency, same shape as every other
    route's ``user`` param."""
    if not _platform_admin_service.is_super_admin(user.id):
        raise HTTPException(status_code=403, detail="Super admin access required")
    return user


def require_workspace_admin(
    workspace_id: str, user: AuthUser = Depends(get_current_user_required)
) -> AuthUser:
    """Phase 27 — gates every /workspaces/{workspace_id}/knowledge/* route.
    A Super Admin may act on any workspace; a workspace_admin only on the
    one(s) they're scoped to. ``workspace_id`` is resolved automatically
    from the route's own path parameter of the same name."""
    if _platform_admin_service.is_super_admin(user.id):
        return user
    if not _workspace_admin_service.is_workspace_admin(user.id, workspace_id):
        raise HTTPException(status_code=403, detail="Workspace admin access required")
    return user
