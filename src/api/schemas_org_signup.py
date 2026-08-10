"""Request/response schemas for self-service org signup and team
invitations (Phase 28). Separate file, same rationale as
schemas_admin.py/schemas_knowledge.py — keeps a cohesive, bounded schema
set out of the already-large schemas.py.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .schemas import AuthUserSchema
from .schemas_admin import WorkspaceAdminSchema

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SLUG_RE = re.compile(r"^[a-z0-9-]+$")

Department = Literal["Support", "Sales", "Solution Architect", "Customer Success", "General"]


class OrgSignupRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=200)
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=8, max_length=200)
    org_name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=100)
    plan: Literal["free", "starter", "pro"] = "free"

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        if not _EMAIL_RE.match(value):
            raise ValueError("must be a valid email address")
        return value

    @field_validator("slug")
    @classmethod
    def _validate_slug(cls, value: str) -> str:
        if not _SLUG_RE.match(value):
            raise ValueError("slug may only contain lowercase letters, numbers, and hyphens")
        return value


class OrgSignupResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: AuthUserSchema
    workspace: WorkspaceAdminSchema
    api_key: str


class InvitationCreateRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    role: Literal["workspace_admin", "agent"]
    department: Department | None = None

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        if not _EMAIL_RE.match(value):
            raise ValueError("must be a valid email address")
        return value


class WorkspaceInvitationSchema(BaseModel):
    id: str
    workspace_id: str
    email: str
    role: str
    department: str | None = None
    invited_by: str
    status: str
    created_at: str | None = None
    accepted_at: str | None = None


class AcceptInviteRequest(BaseModel):
    access_token: str = Field(..., min_length=1)
    password: str = Field(..., min_length=8, max_length=200)
