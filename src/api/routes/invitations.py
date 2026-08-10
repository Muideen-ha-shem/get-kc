"""Team invitation routes (Phase 28) — `/workspaces/{workspace_id}/invitations`.

Every route depends on `require_workspace_admin` (Phase 27's dependency):
a Super Admin may act on any workspace; a workspace_admin only on their own.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException

from ...services.org_signup.invitation_service import InvitationService
from ...services.auth.auth_service import AuthUser
from ..deps import require_workspace_admin
from ..schemas_org_signup import InvitationCreateRequest, WorkspaceInvitationSchema

router = APIRouter(prefix="/workspaces/{workspace_id}/invitations")

_invitation_service = InvitationService()


def _invite_redirect_url() -> str:
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    return f"{frontend_url.rstrip('/')}/accept-invite"


def _to_schema(invitation) -> WorkspaceInvitationSchema:
    return WorkspaceInvitationSchema(
        id=invitation.id, workspace_id=invitation.workspace_id, email=invitation.email,
        role=invitation.role, department=invitation.department, invited_by=invitation.invited_by,
        status=invitation.status, created_at=invitation.created_at, accepted_at=invitation.accepted_at,
    )


@router.post("", response_model=WorkspaceInvitationSchema)
def create_invitation(
    workspace_id: str, request: InvitationCreateRequest, user: AuthUser = Depends(require_workspace_admin)
) -> WorkspaceInvitationSchema:
    try:
        invitation = _invitation_service.create_invitation(
            workspace_id, request.email, request.role, request.department, user.id,
            redirect_to=_invite_redirect_url(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _to_schema(invitation)


@router.get("", response_model=list[WorkspaceInvitationSchema])
def list_invitations(
    workspace_id: str, user: AuthUser = Depends(require_workspace_admin)
) -> list[WorkspaceInvitationSchema]:
    return [_to_schema(i) for i in _invitation_service.list_pending(workspace_id)]


@router.delete("/{invitation_id}")
def revoke_invitation(
    workspace_id: str, invitation_id: str, user: AuthUser = Depends(require_workspace_admin)
) -> dict[str, str]:
    _invitation_service.revoke(invitation_id, workspace_id)
    return {"status": "revoked"}
