"""Result models for org_signup_service (Phase 28)."""

from __future__ import annotations

from dataclasses import dataclass

from ..admin.admin_models import AdminWorkspace
from ..auth.auth_service import AuthSession


class OrgSignupError(Exception):
    """Raised for any failed org-signup step whose message is safe to
    surface to the client (mirrors AuthError's precedent)."""


@dataclass(frozen=True)
class OrgSignupResult:
    session: AuthSession
    workspace: AdminWorkspace
