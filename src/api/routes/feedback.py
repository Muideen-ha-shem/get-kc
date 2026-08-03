from fastapi import APIRouter, Depends

from ...services.auth.auth_service import AuthUser
from ...services.feedback.feedback_service import FeedbackService
from ...services.workspace.workspace_context import WorkspaceContext
from ..deps import get_current_user_optional, get_current_workspace
from ..schemas import FeedbackSchema, SubmitFeedbackRequest

router = APIRouter()

_feedback_service = FeedbackService()


@router.post("/chat/feedback", response_model=FeedbackSchema)
def submit_feedback(
    request: SubmitFeedbackRequest,
    user: AuthUser | None = Depends(get_current_user_optional),
    workspace: WorkspaceContext = Depends(get_current_workspace),
) -> FeedbackSchema:
    row = _feedback_service.submit(
        request.question,
        request.answer,
        request.rating,
        comment=request.comment,
        user_id=user.id if user else None,
        session_id=request.session_id,
        conversation_id=request.conversation_id,
        workspace_id=workspace.workspace_id,
    )
    return FeedbackSchema(
        id=row.id, question=row.question, answer=row.answer,
        rating=row.rating, comment=row.comment, created_at=row.created_at,
    )
