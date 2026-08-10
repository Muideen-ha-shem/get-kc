"""Public self-service organization signup routes (Phase 28) —
`/org-signup`, `/org-signup/slug-available`, `/org-signup/accept-invite`.

None of these depend on any auth — this is the one route module in the
whole API meant to be reachable by a completely anonymous visitor to
create their own account and workspace, or to complete a team invite
using only the token from their invite email.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ...services.admin.tenant_repository import AdminWorkspaceRepository
from ...services.auth.auth_service import AuthService
from ...services.org_signup.invitation_service import InvitationError, InvitationService
from ...services.org_signup.org_signup_models import OrgSignupError
from ...services.org_signup.org_signup_service import OrgSignupService
from .admin_workspaces import _to_workspace_schema
from ..schemas import AuthSessionResponse, AuthUserSchema
from ..schemas_org_signup import AcceptInviteRequest, OrgSignupRequest, OrgSignupResponse

router = APIRouter(prefix="/org-signup")

_org_signup_service = OrgSignupService()
_invitation_service = InvitationService()
_workspace_repository = AdminWorkspaceRepository()


@router.post("", response_model=OrgSignupResponse)
def sign_up_organization(request: OrgSignupRequest) -> OrgSignupResponse:
    try:
        result = _org_signup_service.sign_up_organization(
            full_name=request.full_name, email=request.email, password=request.password,
            org_name=request.org_name, slug=request.slug, plan=request.plan,
        )
    except OrgSignupError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    session = result.session
    return OrgSignupResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        user=AuthUserSchema(id=session.user.id, email=session.user.email, full_name=session.user.full_name),
        workspace=_to_workspace_schema(result.workspace),
        api_key=result.workspace.api_key,
    )


@router.get("/slug-available")
def check_slug_available(slug: str) -> dict[str, bool]:
    for workspace in _workspace_repository.list_all():
        if workspace.slug == slug:
            return {"available": False}
    return {"available": True}


@router.post("/accept-invite", response_model=AuthSessionResponse)
def accept_invite(request: AcceptInviteRequest) -> AuthSessionResponse:
    try:
        invitation = _invitation_service.accept_invitation(request.access_token, request.password)
    except InvitationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session = AuthService().sign_in(invitation.email, request.password)
    return AuthSessionResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        user=AuthUserSchema(id=session.user.id, email=session.user.email, full_name=session.user.full_name),
    )
