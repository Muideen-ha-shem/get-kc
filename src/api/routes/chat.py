from fastapi import APIRouter, Depends, HTTPException

from ...orchestrator.chat_orchestrator import chat_orchestrator
from ...services.auth.auth_service import AuthUser
from ...services.conversation.conversation_service import ConversationService
from ...services.profile.profile_service import ProfileService
from ...services.workspace.workspace_context import WorkspaceContext
from ..deps import get_current_access_token, get_current_user_optional, get_current_workspace
from ..schemas import ChatRequest, ChatResponse

router = APIRouter()

_profile_service = ProfileService()
_conversation_service = ConversationService()


def _profile_context(user: AuthUser | None, access_token: str | None) -> str | None:
    """Build a short natural-language hint used only to bias business-intent
    classification (Workstream 6 personalization) — never sent to retrieval
    or shown in the answer. ``None`` for anonymous users, preserving exact
    prior behaviour for them. Best-effort: a lookup failure must never break
    the chat response, since this is a non-essential enrichment."""
    if user is None:
        return None
    try:
        profile = _profile_service.get_by_auth_user_id(user.id, access_token=access_token)
    except Exception:
        return None
    if profile is None:
        return None
    parts = [p for p in (profile.company_name, profile.industry) if p]
    return " — ".join(parts) if parts else None


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    user: AuthUser | None = Depends(get_current_user_optional),
    access_token: str | None = Depends(get_current_access_token),
    workspace: WorkspaceContext = Depends(get_current_workspace),
) -> ChatResponse:
    try:
        response = chat_orchestrator.process_request_response(
            request.message,
            session_id=request.session_id,
            profile_context=_profile_context(user, access_token),
            workspace_id=workspace.workspace_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to process chat request") from exc

    # Conversation persistence (Workstream 4) — happens behind this same
    # contract, best-effort, never allowed to break the chat response.
    if user is not None and request.conversation_id:
        try:
            _conversation_service.record_turn(
                request.conversation_id,
                user.id,
                request.message,
                response.answer,
                sources=response.sources,
                next_actions=[a.model_dump() for a in (response.next_actions or [])],
                access_token=access_token,
            )
        except Exception:
            pass

    return response
