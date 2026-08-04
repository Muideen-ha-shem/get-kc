import os

from fastapi import APIRouter, Depends, Header, HTTPException

from ...services.auth.auth_service import AuthError, AuthService, AuthUser
from ...services.profile.profile_service import ProfileService
from ..deps import extract_bearer_token, get_current_user_required
from ..schemas import (
    AuthSessionResponse,
    AuthUserSchema,
    PasswordResetRequest,
    PasswordUpdateRequest,
    SignInRequest,
    SignUpRequest,
)

router = APIRouter(prefix="/auth")

_auth_service = AuthService()
_profile_service = ProfileService()


def _password_reset_redirect_url() -> str:
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    return f"{frontend_url.rstrip('/')}/reset-password"


@router.post("/sign-up", response_model=AuthSessionResponse)
def sign_up(request: SignUpRequest) -> AuthSessionResponse:
    try:
        session = _auth_service.sign_up(request.email, request.password, request.full_name)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        _profile_service.get_or_create(
            session.user.id, session.user.email or request.email, request.full_name,
            access_token=session.access_token,
        )
    except Exception:
        # The account itself was created successfully — a profile-row hiccup
        # (e.g. the auto-create trigger already raced us to it) must not
        # fail the sign-up response. ProfileService.get_or_create is
        # idempotent, so the next authenticated call will self-heal this.
        pass
    return AuthSessionResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        user=AuthUserSchema(id=session.user.id, email=session.user.email, full_name=session.user.full_name),
    )


@router.post("/sign-in", response_model=AuthSessionResponse)
def sign_in(request: SignInRequest) -> AuthSessionResponse:
    try:
        session = _auth_service.sign_in(request.email, request.password)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    try:
        _profile_service.get_or_create(
            session.user.id, session.user.email or request.email, access_token=session.access_token
        )
        _profile_service.record_login(session.user.id, access_token=session.access_token)
    except Exception:
        # Same reasoning as sign-up: never fail a successful sign-in over a
        # non-essential profile-row write.
        pass
    return AuthSessionResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        user=AuthUserSchema(id=session.user.id, email=session.user.email, full_name=session.user.full_name),
    )


@router.post("/sign-out")
def sign_out(authorization: str | None = Header(default=None)) -> dict[str, str]:
    token = extract_bearer_token(authorization)
    if token:
        _auth_service.sign_out(token)
    return {"status": "signed_out"}


@router.post("/password-reset")
def request_password_reset(request: PasswordResetRequest) -> dict[str, str]:
    try:
        _auth_service.request_password_reset(request.email, redirect_to=_password_reset_redirect_url())
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "reset_email_sent"}


@router.post("/update-password")
def update_password(request: PasswordUpdateRequest) -> dict[str, str]:
    try:
        _auth_service.confirm_password_reset(request.access_token, request.new_password)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "password_updated"}


@router.get("/me", response_model=AuthUserSchema)
def me(user: AuthUser = Depends(get_current_user_required)) -> AuthUserSchema:
    return AuthUserSchema(id=user.id, email=user.email, full_name=user.full_name)
