"""``GET /workspace/config`` — public branding config for the embeddable
HavisIQ SDK (Phase 23). Strict resolution: an invalid api_key/host is a
401, unlike /chat's lenient fallback — a misconfigured widget must not
silently serve the default Ha-Shem workspace's branding."""

from fastapi import APIRouter, Depends

from ...services.workspace.workspace_context import WorkspaceContext
from ..deps import get_current_workspace_strict
from ..schemas import WorkspaceConfigSchema

router = APIRouter()


@router.get("/workspace/config", response_model=WorkspaceConfigSchema, response_model_by_alias=True)
def get_workspace_config(
    workspace: WorkspaceContext = Depends(get_current_workspace_strict),
) -> WorkspaceConfigSchema:
    return WorkspaceConfigSchema(
        id=workspace.workspace_id,
        slug=workspace.slug,
        name=workspace.name,
        logo=workspace.logo,
        primary_color=workspace.primary_color,
        welcome_message=workspace.welcome_message,
        quick_actions=workspace.quick_actions,
    )
