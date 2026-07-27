import re

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]


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
