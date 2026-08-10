from fastapi import APIRouter, Depends, HTTPException

from ...services.auth.auth_service import AuthUser
from ...services.notifications.notification_service import NotificationService
from ...services.workspace.workspace_context import WorkspaceContext
from ..deps import get_current_access_token_required, get_current_user_required, get_current_workspace
from ..schemas import NotificationSchema, UnreadCountSchema

router = APIRouter()

_notification_service = NotificationService()


def _to_schema(row) -> NotificationSchema:
    return NotificationSchema(id=row.id, type=row.type, title=row.title, body=row.body, is_read=row.is_read, created_at=row.created_at)


@router.get("/notifications", response_model=list[NotificationSchema])
def list_notifications(
    user: AuthUser = Depends(get_current_user_required),
    access_token: str = Depends(get_current_access_token_required),
    workspace: WorkspaceContext = Depends(get_current_workspace),
) -> list[NotificationSchema]:
    rows = _notification_service.list_for_user(user.id, access_token=access_token, workspace_id=workspace.workspace_id)
    return [_to_schema(r) for r in rows]


@router.get("/notifications/unread-count", response_model=UnreadCountSchema)
def unread_count(
    user: AuthUser = Depends(get_current_user_required),
    access_token: str = Depends(get_current_access_token_required),
    workspace: WorkspaceContext = Depends(get_current_workspace),
) -> UnreadCountSchema:
    return UnreadCountSchema(
        count=_notification_service.unread_count(user.id, access_token=access_token, workspace_id=workspace.workspace_id)
    )


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    user: AuthUser = Depends(get_current_user_required),
    access_token: str = Depends(get_current_access_token_required),
) -> dict[str, str]:
    marked = _notification_service.mark_read(notification_id, user.id, access_token=access_token)
    if not marked:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"status": "read"}


@router.post("/notifications/read-all")
def mark_all_notifications_read(
    user: AuthUser = Depends(get_current_user_required),
    access_token: str = Depends(get_current_access_token_required),
) -> dict[str, str]:
    _notification_service.mark_all_read(user.id, access_token=access_token)
    return {"status": "ok"}
