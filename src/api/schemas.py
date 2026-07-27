import re

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


class NextActionSchema(BaseModel):
    """A contextual next-step suggestion (Phase 19) — additive to
    ChatResponse, mirrors ``src.services.advisory.next_actions.NextAction``.
    Old clients that don't know this field simply ignore it."""

    label: str
    action_type: str
    target: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    next_actions: list[NextActionSchema] | None = None


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class DemoRequest(BaseModel):
    """Payload for ``POST /demo-request`` — "Request a demo" / "Contact
    sales" / "Talk to an expert" all submit through this same shape."""

    name: str = Field(..., min_length=1, max_length=200)
    email: str = Field(..., min_length=3, max_length=320)
    company: str | None = Field(None, max_length=200)
    use_case: str | None = Field(None, max_length=2000)
    product: str | None = Field(
        None, max_length=100, description="Solution the request relates to, e.g. 'SPIDIFY'."
    )

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        if not _EMAIL_RE.match(value):
            raise ValueError("must be a valid email address")
        return value


class DemoRequestResponse(BaseModel):
    id: int | None = None
    name: str
    email: str
    company: str | None = None
    use_case: str | None = None
    product: str | None = None
    status: str = "received"


class SolutionSummary(BaseModel):
    """One entry from ``GET /solutions`` — a curated, public-facing view of
    a ``src.shared.product_registry.PRODUCT_REGISTRY`` entry. Deliberately
    excludes retrieval-internal fields (path_prefix, domain, aliases,
    keywords) that aren't meaningful to a frontend catalog."""

    id: str
    name: str
    category: str
    business_problem: str
    solution_type: str
    learn_more_url: str
