from fastapi import APIRouter, Depends, HTTPException

from ...services.auth.auth_service import AuthUser
from ...services.conversation.conversation_service import ConversationService
from ..deps import get_current_access_token_required, get_current_user_required
from ..schemas import (
    ConversationDetail,
    ConversationMessageSchema,
    ConversationSummary,
    CreateConversationRequest,
    RenameConversationRequest,
)

router = APIRouter(prefix="/conversations")

_conversation_service = ConversationService()


def _to_summary(row) -> ConversationSummary:
    return ConversationSummary(id=row.id, title=row.title, created_at=row.created_at, updated_at=row.updated_at)


@router.get("", response_model=list[ConversationSummary])
def list_conversations(
    search: str | None = None,
    user: AuthUser = Depends(get_current_user_required),
    access_token: str = Depends(get_current_access_token_required),
) -> list[ConversationSummary]:
    rows = _conversation_service.list_conversations(user.id, access_token=access_token, search=search)
    return [_to_summary(row) for row in rows]


@router.post("", response_model=ConversationSummary)
def create_conversation(
    request: CreateConversationRequest,
    user: AuthUser = Depends(get_current_user_required),
    access_token: str = Depends(get_current_access_token_required),
) -> ConversationSummary:
    row = _conversation_service.start_conversation(user.id, request.first_message, access_token=access_token)
    return _to_summary(row)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: str,
    user: AuthUser = Depends(get_current_user_required),
    access_token: str = Depends(get_current_access_token_required),
) -> ConversationDetail:
    conversation = _conversation_service.get_conversation(conversation_id, user.id, access_token=access_token)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = _conversation_service.get_messages(conversation_id, user.id, access_token=access_token) or []
    return ConversationDetail(
        conversation=_to_summary(conversation),
        messages=[
            ConversationMessageSchema(
                id=m.id, role=m.role, content=m.content, citations=m.citations,
                metadata=m.metadata, created_at=m.created_at,
            )
            for m in messages
        ],
    )


@router.patch("/{conversation_id}", response_model=ConversationSummary)
def rename_conversation(
    conversation_id: str,
    request: RenameConversationRequest,
    user: AuthUser = Depends(get_current_user_required),
    access_token: str = Depends(get_current_access_token_required),
) -> ConversationSummary:
    row = _conversation_service.rename_conversation(conversation_id, user.id, request.title, access_token=access_token)
    if row is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _to_summary(row)


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    user: AuthUser = Depends(get_current_user_required),
    access_token: str = Depends(get_current_access_token_required),
) -> dict[str, str]:
    deleted = _conversation_service.delete_conversation(conversation_id, user.id, access_token=access_token)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "deleted"}
