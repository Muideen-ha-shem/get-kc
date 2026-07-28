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

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "CustomerProfile":
        return cls(**{field: row.get(field) for field in cls.__dataclass_fields__})


class ProfileService:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def _client_for(self, access_token: str | None) -> Client:
        return get_authenticated_client(access_token) if access_token else self._client

    def get_or_create(
        self, auth_user_id: str, email: str, full_name: str | None = None, access_token: str | None = None
    ) -> CustomerProfile:
        existing = self.get_by_auth_user_id(auth_user_id, access_token=access_token)
        if existing is not None:
            return existing
        payload = {"auth_user_id": auth_user_id, "email": email, "full_name": full_name}
        response = self._client_for(access_token).table(_TABLE).insert(payload).execute()
        return CustomerProfile.from_row(response.data[0])

    def get_by_auth_user_id(self, auth_user_id: str, access_token: str | None = None) -> CustomerProfile | None:
        response = (
            self._client_for(access_token)
            .table(_TABLE)
            .select("*")
            .eq("auth_user_id", auth_user_id)
            .limit(1)
            .execute()
        )
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

    def record_login(self, auth_user_id: str, access_token: str | None = None) -> None:
        from datetime import datetime, timezone

        self._client_for(access_token).table(_TABLE).update(
            {"last_login": datetime.now(timezone.utc).isoformat()}
        ).eq("auth_user_id", auth_user_id).execute()
