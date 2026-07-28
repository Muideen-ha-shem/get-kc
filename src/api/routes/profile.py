from fastapi import APIRouter, Depends

from ...services.auth.auth_service import AuthUser
from ...services.profile.profile_service import ProfileService
from ..deps import get_current_access_token_required, get_current_user_required
from ..schemas import CustomerProfileSchema, UpdateProfileRequest

router = APIRouter(prefix="/profile")

_profile_service = ProfileService()


def _to_schema(profile) -> CustomerProfileSchema:
    return CustomerProfileSchema(
        id=profile.id,
        email=profile.email,
        full_name=profile.full_name,
        company_name=profile.company_name,
        industry=profile.industry,
        phone=profile.phone,
    )


@router.get("", response_model=CustomerProfileSchema)
def get_profile(
    user: AuthUser = Depends(get_current_user_required),
    access_token: str = Depends(get_current_access_token_required),
) -> CustomerProfileSchema:
    profile = _profile_service.get_or_create(user.id, user.email or "", user.full_name, access_token=access_token)
    return _to_schema(profile)


@router.patch("", response_model=CustomerProfileSchema)
def update_profile(
    request: UpdateProfileRequest,
    user: AuthUser = Depends(get_current_user_required),
    access_token: str = Depends(get_current_access_token_required),
) -> CustomerProfileSchema:
    _profile_service.get_or_create(user.id, user.email or "", user.full_name, access_token=access_token)
    profile = _profile_service.update(user.id, access_token=access_token, **request.model_dump())
    return _to_schema(profile)
