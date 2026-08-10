"""OrgSignupService — self-service organization signup (Phase 28).

Public-facing: an unauthenticated visitor supplies their own details plus
an organization name/slug and gets back a real, signed-in session with a
brand-new, already-active workspace they own. Every step reuses an
existing, already-tested service unmodified (AuthService, TenantService,
WorkspaceAdminService, ProfileService) — this module only sequences them.

No cross-table transaction exists anywhere in this codebase (raw
supabase-py, no ORM), so failure handling here is deliberately
best-effort, matching every other multi-step service in this repo:

- Step 1 (create the auth user) is the one step made idempotent against
  retry — if the email is already registered (e.g. the caller is retrying
  after a slug collision on a previous attempt), fall back to signing in
  with the supplied password rather than hard-failing.
- If workspace-admin assignment (step 4) fails after the user, session,
  and workspace already exist, this still returns success with the valid
  session rather than stranding an otherwise-signed-in-capable person
  behind an error — the missing admin row is repairable later via the
  existing POST /admin/users/{id}/roles endpoint.
- Profile creation (step 5) failures are swallowed entirely, mirroring
  /auth/sign-up's own precedent for the identical call.
"""

from __future__ import annotations

import logging

from ...sb import get_admin_client, get_client
from ...shared.logging import get_logger
from ..admin.tenant_service import TenantService
from ..admin.workspace_admin_service import WorkspaceAdminService
from ..auth.auth_service import AuthError, AuthService
from ..profile.profile_service import ProfileService
from .org_signup_models import OrgSignupError, OrgSignupResult

logger: logging.Logger = get_logger(__name__)


class OrgSignupService:
    def __init__(
        self,
        tenant_service: TenantService | None = None,
        workspace_admin_service: WorkspaceAdminService | None = None,
        profile_service: ProfileService | None = None,
    ) -> None:
        self._tenant_service = tenant_service or TenantService()
        self._workspace_admin_service = workspace_admin_service or WorkspaceAdminService()
        self._profile_service = profile_service or ProfileService()

    def sign_up_organization(
        self, *, full_name: str, email: str, password: str, org_name: str, slug: str, plan: str
    ) -> OrgSignupResult:
        admin_auth = AuthService(client=get_admin_client())
        try:
            new_user = admin_auth.admin_create_user(email, password, full_name)
        except AuthError as exc:
            if "already" not in str(exc).lower() and "duplicate" not in str(exc).lower():
                raise OrgSignupError(str(exc)) from exc
            new_user = None  # resolved via sign-in below instead

        anon_auth = AuthService(client=get_client())
        try:
            session = anon_auth.sign_in(email, password)
        except AuthError as exc:
            raise OrgSignupError(
                "An account with this email already exists with a different password."
            ) from exc
        user = new_user or session.user

        try:
            workspace = self._tenant_service.create_workspace(
                slug, org_name, host=None, actor_auth_user_id=user.id,
                owner_auth_user_id=user.id, plan=plan,
            )
        except ValueError as exc:
            raise OrgSignupError(str(exc)) from exc

        try:
            self._workspace_admin_service.add_admin(workspace.id, user.id)
        except Exception:
            logger.error(
                "org signup: failed to assign workspace_admin for workspace_id=%s auth_user_id=%s",
                workspace.id, user.id,
            )

        try:
            self._profile_service.get_or_create(
                user.id, email, full_name, access_token=session.access_token, workspace_id=workspace.id
            )
        except Exception:
            pass

        return OrgSignupResult(session=session, workspace=workspace)
