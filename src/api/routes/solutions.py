"""``GET /solutions`` — the Public Portal's solution catalog, read directly
from ``PRODUCT_REGISTRY`` (the same single source of truth ``ProductRouter``
and the crawl/metadata pipeline already use). Read-only, no request body, no
side effects — the frontend fetches this instead of hand-duplicating product
data into its own TypeScript catalog.
"""

from fastapi import APIRouter

from ...shared.product_registry import PRODUCT_REGISTRY
from ..schemas import SolutionSummary

router = APIRouter()


@router.get("/solutions", response_model=list[SolutionSummary])
def list_solutions() -> list[SolutionSummary]:
    return [
        SolutionSummary(
            id=name,
            name=name,
            category=info["category"],
            business_problem=info["business_problem"],
            solution_type=info["solution_type"],
            learn_more_url=info["url"],
        )
        for name, info in PRODUCT_REGISTRY.items()
    ]
