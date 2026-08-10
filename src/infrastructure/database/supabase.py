import os
from functools import lru_cache

import httpx
from dotenv import load_dotenv
from supabase import Client, ClientOptions, create_client

load_dotenv()


def _build_httpx_client() -> httpx.Client:
    """A plain HTTP/1.1 httpx client for supabase-py to use internally.

    postgrest-py and gotrue-py both hardcode ``http2=True`` when building
    their own default httpx client (unless one is supplied via
    ``ClientOptions.httpx_client`` — see below). Under sustained concurrent
    polling (several agent-dashboard tabs each hitting 3 endpoints every
    few seconds), that shared multiplexed HTTP/2 connection was observed to
    destabilize against Supabase's Cloudflare-fronted endpoint in two
    distinct ways: ``httpx.LocalProtocolError: Received pseudo-header in
    trailer`` and ``httpx.RemoteProtocolError: Server disconnected`` /
    ``ConnectionTerminated`` — and because HTTP/2 multiplexes many requests
    over one connection, a single bad connection took down every
    concurrently in-flight request at once, not just one. HTTP/1.1 with a
    small connection pool trades multiplexing for isolation: one failed
    connection only affects the request using it, and a modest pool means
    concurrent tabs aren't fully serialized onto a single connection either.
    """
    return httpx.Client(
        http2=False,
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10, keepalive_expiry=30),
    )


@lru_cache(maxsize=1)
def get_client() -> Client:
    """Create a Supabase client using the configured environment variables.

    Cached as a singleton (rather than a fresh client per call, as this
    used to do): every repository's default constructor calls this, so an
    uncached version means a brand-new httpx client — and a brand-new
    connection — on nearly every request. ``httpx.Client`` (which this
    wraps) is explicitly documented as safe to share across threads, so one
    long-lived client for the process is both correct and the standard
    supabase-py server pattern. Never used for anything user-token-scoped —
    see ``get_authenticated_client`` below, which intentionally stays
    uncached.
    """
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("Missing Supabase Credentials")
    return create_client(url, key, options=ClientOptions(httpx_client=_build_httpx_client()))


@lru_cache(maxsize=1)
def get_admin_client() -> Client:
    """Service-role Supabase client — bypasses RLS and can call
    ``auth.admin.*`` (suspend/reactivate/list users).

    NEVER expose ``SUPABASE_SERVICE_ROLE_KEY`` or a client built from it
    outside server-side admin-only service code (``src/services/admin/``,
    and ``AuthService``'s admin-facing methods). No response model may ever
    serialize this key. Distinct from ``get_client()``/
    ``get_authenticated_client()``, which remain anon-key-only and
    untouched — this function is purely additive (Phase 26). Cached as a
    singleton for the same connection-churn reason as ``get_client()``.
    """
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise ValueError("Missing Supabase service-role credentials")
    return create_client(url, key, options=ClientOptions(httpx_client=_build_httpx_client()))


def get_authenticated_client(access_token: str) -> Client:
    """A fresh Supabase client whose PostgREST requests carry *access_token*.

    Row Level Security policies keyed on ``auth.uid()`` (customer_profiles,
    conversations, conversation_messages) only resolve to the calling user
    when the request itself is authenticated as them — the module's
    ``SUPABASE_KEY`` (anon key) alone isn't enough, since ``auth.uid()``
    is null for an unauthenticated PostgREST request and every insert/
    select against those tables is denied. A new client per call (rather
    than mutating a shared/cached one) avoids any cross-request auth
    bleed under FastAPI's threaded request handling.

    Deliberately does NOT go through ``get_client()`` — that now returns a
    cached singleton (see its docstring), and calling ``.postgrest.auth()``
    mutates a client's headers *in place*. Doing that to the shared
    singleton would leak one user's access token into every other
    concurrent request using the anon client. This function must always
    build its own independent client instance.
    """
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("Missing Supabase Credentials")
    client = create_client(url, key, options=ClientOptions(httpx_client=_build_httpx_client()))
    client.postgrest.auth(access_token)
    return client
