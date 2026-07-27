from fastapi import APIRouter, HTTPException

from ..schemas import DemoRequest, DemoRequestResponse
from ..services.demo_requests import DemoRequestTableMissingError, submit_demo_request

router = APIRouter()


@router.post("/demo-request", response_model=DemoRequestResponse)
def create_demo_request(request: DemoRequest) -> DemoRequestResponse:
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

    return DemoRequestResponse(
        id=row.get("id"),
        name=row.get("name", request.name),
        email=row.get("email", request.email),
        company=row.get("company", request.company),
        use_case=row.get("use_case", request.use_case),
        product=row.get("product", request.product),
        status="received",
    )
