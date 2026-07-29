from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_current_access_token, get_current_user_optional
from ..schemas import DemoRequest, DemoRequestResponse
from ..services.demo_requests import DemoRequestTableMissingError, submit_demo_request
from ...services.auth.auth_service import AuthUser
from ...services.notifications.notification_service import NotificationService

router = APIRouter()

_notification_service = NotificationService()


@router.post("/demo-request", response_model=DemoRequestResponse)
def create_demo_request(
    request: DemoRequest,
    user: AuthUser | None = Depends(get_current_user_optional),
    access_token: str | None = Depends(get_current_access_token),
) -> DemoRequestResponse:
    try:
        row = submit_demo_request(
            name=request.name,
            email=request.email,
            company=request.company,
            use_case=request.use_case,
            product=request.product,
        )
    except DemoRequestTableMissingError as exc:
        raise HTTPException(
            status_code=503,
            detail="We can't accept demo requests right now — please email us directly and we'll follow up.",
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to submit demo request") from exc

    if user is not None:
        _notification_service.notify(
            user.id, "demo_request", "Demo request received",
            f"We received your request{f' about {request.product}' if request.product else ''}.",
            access_token=access_token,
        )

    return DemoRequestResponse(
        id=row.get("id"),
        name=row.get("name", request.name),
        email=row.get("email", request.email),
        company=row.get("company", request.company),
        use_case=row.get("use_case", request.use_case),
        product=row.get("product", request.product),
        status="received",
    )
