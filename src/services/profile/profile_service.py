"""ProfileService — CRUD over ``customer_profiles``.

A lightweight profile, not AI memory: the fields here (company, industry,
etc.) feed Workstream 6 personalization, but nothing here stores
conversation content or derived preferences.

The migration's ``on_auth_user_created`` trigger auto-creates a blank row
per new auth user, but ``get_or_create`` still handles the case of a user
who signed up before that trigger existed (or any other race), so this
service never assumes the row is already there.

``customer_profiles`` has Row Level Security keyed on ``auth.uid()``, so
every call needs the caller's access token — see
``get_authenticated_client``'s docstring for why the module's own
(anon-key) client can't perform these reads/writes on its own.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from supabase import Client

from ...sb import get_authenticated_client, get_client
from ...services.workspace.workspace_models import DEFAULT_WORKSPACE_ID
from ...shared.logging import get_logger

logger: logging.Logger = get_logger(__name__)

_TABLE = "customer_profiles"


@dataclass(frozen=True)
class CustomerProfile:
    id: str
    auth_user_id: str
    email: str
    full_name: str | None = None
    company_name: str | None = None
    industry: str | None = None
    phone: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    last_login: str | None = None
    workspace_id: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "CustomerProfile":
        return cls(**{field: row.get(field) for field in cls.__dataclass_fields__})


class ProfileService:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def _client_for(self, access_token: str | None) -> Client:
        return get_authenticated_client(access_token) if access_token else self._client

    def get_or_create(
        self,
        auth_user_id: str,
        email: str,
        full_name: str | None = None,
        access_token: str | None = None,
        workspace_id: str = DEFAULT_WORKSPACE_ID,
    ) -> CustomerProfile:
        existing = self.get_by_auth_user_id(auth_user_id, access_token=access_token)
        if existing is not None:
            return existing
        payload = {
            "auth_user_id": auth_user_id,
            "email": email,
            "full_name": full_name,
            "workspace_id": workspace_id,
        }
        response = self._client_for(access_token).table(_TABLE).insert(payload).execute()
        return CustomerProfile.from_row(response.data[0])

    def get_by_auth_user_id(
        self, auth_user_id: str, access_token: str | None = None, workspace_id: str | None = None
    ) -> CustomerProfile | None:
        query = (
            self._client_for(access_token)
            .table(_TABLE)
            .select("*")
            .eq("auth_user_id", auth_user_id)
        )
        if workspace_id is not None:
            query = query.eq("workspace_id", workspace_id)
        response = query.limit(1).execute()
        if not response.data:
            return None
        return CustomerProfile.from_row(response.data[0])

    def update(self, auth_user_id: str, access_token: str | None = None, **fields: Any) -> CustomerProfile:
        allowed = {"full_name", "company_name", "industry", "phone"}
        payload = {key: value for key, value in fields.items() if key in allowed and value is not None}
        if not payload:
            existing = self.get_by_auth_user_id(auth_user_id, access_token=access_token)
            if existing is None:
                raise ValueError(f"No profile found for auth_user_id={auth_user_id}")
            return existing
        response = (
            self._client_for(access_token)
            .table(_TABLE)
            .update(payload)
            .eq("auth_user_id", auth_user_id)
            .execute()
        )
        if not response.data:
            raise ValueError(f"No profile found for auth_user_id={auth_user_id}")
        return CustomerProfile.from_row(response.data[0])

    def set_workspace_id(
        self, auth_user_id: str, workspace_id: str, access_token: str | None = None
    ) -> CustomerProfile:
        """Force-corrects which workspace this profile belongs to.

        Deliberately separate from ``update()``'s generic field allowlist —
        the ``on_auth_user_created`` DB trigger (see module docstring)
        creates a blank profile row with ``workspace_id=null`` the instant
        an auth user is inserted, which happens *before* a caller like
        org-signup or invite-acceptance has created/known the real
        workspace. ``get_or_create`` then finds that row already exists and
        returns it unchanged — silently leaving ``workspace_id`` null,
        which makes ``get_current_chat_workspace`` fall through to the
        default (Ha-Shem) workspace for that customer's every future chat
        request. Callers that just resolved/created the *real* workspace
        for a user must call this immediately after ``get_or_create`` to
        guarantee it's actually applied, not just attempted.
        """
        response = (
            self._client_for(access_token)
            .table(_TABLE)
            .update({"workspace_id": workspace_id})
            .eq("auth_user_id", auth_user_id)
            .execute()
        )
        if not response.data:
            raise ValueError(f"No profile found for auth_user_id={auth_user_id}")
        return CustomerProfile.from_row(response.data[0])

    def record_login(self, auth_user_id: str, access_token: str | None = None) -> None:
        from datetime import datetime, timezone

        self._client_for(access_token).table(_TABLE).update(
            {"last_login": datetime.now(timezone.utc).isoformat()}
        ).eq("auth_user_id", auth_user_id).execute()
