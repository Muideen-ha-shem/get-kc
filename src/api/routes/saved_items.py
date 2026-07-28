from fastapi import APIRouter, Depends, HTTPException

from ...services.auth.auth_service import AuthUser
from ...services.saved_items.saved_comparison_service import SavedComparisonService
from ...services.saved_items.saved_recommendation_service import SavedRecommendationService
from ..deps import get_current_access_token_required, get_current_user_required
from ..schemas import (
    SaveComparisonRequest,
    SavedComparisonSchema,
    SaveRecommendationRequest,
    SavedRecommendationSchema,
)

router = APIRouter()

_comparison_service = SavedComparisonService()
_recommendation_service = SavedRecommendationService()


@router.post("/saved-comparisons", response_model=SavedComparisonSchema)
def save_comparison(
    request: SaveComparisonRequest,
    user: AuthUser = Depends(get_current_user_required),
    access_token: str = Depends(get_current_access_token_required),
) -> SavedComparisonSchema:
    row = _comparison_service.save(user.id, request.product_ids, access_token=access_token)
    return SavedComparisonSchema(id=row.id, product_ids=row.product_ids, created_at=row.created_at)


@router.get("/saved-comparisons", response_model=list[SavedComparisonSchema])
def list_saved_comparisons(
    user: AuthUser = Depends(get_current_user_required),
    access_token: str = Depends(get_current_access_token_required),
) -> list[SavedComparisonSchema]:
    rows = _comparison_service.list_for_user(user.id, access_token=access_token)
    return [SavedComparisonSchema(id=r.id, product_ids=r.product_ids, created_at=r.created_at) for r in rows]


@router.delete("/saved-comparisons/{comparison_id}")
def delete_saved_comparison(
    comparison_id: str,
    user: AuthUser = Depends(get_current_user_required),
    access_token: str = Depends(get_current_access_token_required),
) -> dict[str, str]:
    deleted = _comparison_service.delete(comparison_id, user.id, access_token=access_token)
    if not deleted:
        raise HTTPException(status_code=404, detail="Saved comparison not found")
    return {"status": "deleted"}


@router.post("/saved-recommendations", response_model=SavedRecommendationSchema)
def save_recommendation(
    request: SaveRecommendationRequest,
    user: AuthUser = Depends(get_current_user_required),
    access_token: str = Depends(get_current_access_token_required),
) -> SavedRecommendationSchema:
    row = _recommendation_service.save(
        user.id, request.products, request.question, request.recommendation, access_token=access_token
    )
    return SavedRecommendationSchema(
        id=row.id, products=row.products, question=row.question,
        recommendation=row.recommendation, created_at=row.created_at,
    )


@router.get("/saved-recommendations", response_model=list[SavedRecommendationSchema])
def list_saved_recommendations(
    user: AuthUser = Depends(get_current_user_required),
    access_token: str = Depends(get_current_access_token_required),
) -> list[SavedRecommendationSchema]:
    rows = _recommendation_service.list_for_user(user.id, access_token=access_token)
    return [
        SavedRecommendationSchema(
            id=r.id, products=r.products, question=r.question,
            recommendation=r.recommendation, created_at=r.created_at,
        )
        for r in rows
    ]


@router.delete("/saved-recommendations/{recommendation_id}")
def delete_saved_recommendation(
    recommendation_id: str,
    user: AuthUser = Depends(get_current_user_required),
    access_token: str = Depends(get_current_access_token_required),
) -> dict[str, str]:
    deleted = _recommendation_service.delete(recommendation_id, user.id, access_token=access_token)
    if not deleted:
        raise HTTPException(status_code=404, detail="Saved recommendation not found")
    return {"status": "deleted"}
