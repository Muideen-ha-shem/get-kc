import os
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()


def get_client() -> Client:
    """Create a Supabase client using the configured environment variables."""
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("Missing Supabase Credentials")
    return create_client(url, key)


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
    """
    client = get_client()
    client.postgrest.auth(access_token)
    return client
