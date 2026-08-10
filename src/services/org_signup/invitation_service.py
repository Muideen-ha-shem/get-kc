"""InvitationService — team invitations for a workspace (Phase 28).

Sends invites via Supabase Auth's own hosted invite email
(auth.admin.invite_user_by_email) rather than a new third-party email
provider. workspace_invitations is the single source of truth for what
role/department an invite was for — Supabase's own invite-email metadata
is not relied on for anything beyond delivering the email; acceptance
resolves purely by matching the invitee's verified email address.
"""

from __future__ import annotations

from ...sb import get_admin_client
from ...shared.logging import get_logger
from ..admin.workspace_admin_service import WorkspaceAdminService
from ..agents.agent_service import AgentService
from ..auth.auth_service import AuthError, AuthService
from ..profile.profile_service import ProfileService
from .invitation_models import WorkspaceInvitation
from .invitation_repository import InvitationRepository

logger = get_logger(__name__)


class InvitationError(Exception):
    """Raised for any failed invitation step whose message is safe to
    surface to the client."""


class InvitationService:
    def __init__(
        self,
        repository: InvitationRepository | None = None,
        workspace_admin_service: WorkspaceAdminService | None = None,
        agent_service: AgentService | None = None,
        profile_service: ProfileService | None = None,
    ) -> None:
        self._repo = repository or InvitationRepository()
        self._workspace_admin_service = workspace_admin_service or WorkspaceAdminService()
        self._agent_service = agent_service or AgentService()
        self._profile_service = profile_service or ProfileService()

    def create_invitation(
        self, workspace_id: str, email: str, role: str, department: str | None, invited_by: str,
        redirect_to: str | None = None,
    ) -> WorkspaceInvitation:
        invitation = self._repo.create(workspace_id, email, role, department, invited_by)
        try:
            AuthService(client=get_admin_client()).admin_invite_user(email, redirect_to=redirect_to)
        except AuthError as exc:
            logger.warning("invite email failed for %s (invitation row still created): %s", email, exc)
        return invitation

    def list_pending(self, workspace_id: str) -> list[WorkspaceInvitation]:
        return self._repo.list_for_workspace(workspace_id)

    def revoke(self, invitation_id: str, workspace_id: str) -> None:
        self._repo.revoke(invitation_id, workspace_id)

    def accept_invitation(self, access_token: str, new_password: str) -> WorkspaceInvitation:
        user = AuthService().get_user(access_token)
        if user is None or user.email is None:
            raise InvitationError("This invite link is invalid or has expired.")

        invitation = self._repo.find_pending_by_email(user.email)
        if invitation is None:
            raise InvitationError("No pending invitation found for this email.")

        get_admin_client().auth.admin.update_user_by_id(user.id, {"password": new_password})

        if invitation.role == "workspace_admin":
            self._workspace_admin_service.add_admin(invitation.workspace_id, user.id)
        else:
            self._agent_service.get_or_create(
                user.id, user.email, user.full_name or user.email, invitation.workspace_id,
                department=invitation.department or "General",
            )

        accepted = self._repo.mark_accepted(invitation.id)

        try:
            self._profile_service.get_or_create(
                user.id, user.email, user.full_name, access_token=access_token,
                workspace_id=invitation.workspace_id,
            )
        except Exception:
            pass

        return accepted
