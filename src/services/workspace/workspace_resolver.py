"""resolve_workspace — priority-order tenant resolution.

Pure function, no FastAPI import, independently testable. Priority order:

    1. explicit workspace_id
    2. workspace_slug
    3. api_key
    4. host
    5. default (Ha-Shem)

An unknown or inactive value at any tier falls through to the next tier
rather than raising — workspace must stay optional and must never break
a request, per Phase 22's backward-compatibility requirement.
"""

from __future__ import annotations

from .workspace_context import WorkspaceContext
from .workspace_models import Workspace
from .workspace_repository import WorkspaceRepository


def to_context(workspace: Workspace, *, is_default: bool = False) -> WorkspaceContext:
    return WorkspaceContext(
        workspace_id=workspace.id,
        slug=workspace.slug,
        name=workspace.name,
        is_default=is_default,
        logo=workspace.logo,
        primary_color=workspace.primary_color,
        welcome_message=workspace.welcome_message,
        quick_actions=workspace.quick_actions,
    )


def resolve_workspace(
    *,
    workspace_id: str | None,
    workspace_slug: str | None,
    api_key: str | None,
    host: str | None,
    repository: WorkspaceRepository,
) -> WorkspaceContext:
    lookups = (
        (workspace_id, repository.get_by_id),
        (workspace_slug, repository.get_by_slug),
        (api_key, repository.get_by_api_key),
        (host, repository.get_by_host),
    )
    for value, lookup in lookups:
        if not value:
            continue
        workspace = lookup(value)
        if workspace is not None and workspace.is_active:
            return to_context(workspace)

    return to_context(repository.get_default(), is_default=True)
