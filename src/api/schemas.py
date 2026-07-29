import re

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = Field(
        None, description="Client-generated session id (Phase 20). Enables pronoun "
        "resolution and conversation awareness across turns. Omit for stateless, "
        "single-turn behaviour identical to prior phases."
    )
    conversation_id: str | None = Field(
        None, description="An existing conversation (Phase 20, authenticated users "
        "only) to persist this turn into. Ignored for anonymous requests."
    )


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
    session_id: str | None = Field(
        None, description="Echoes the request's session_id, or a freshly generated "
        "one when none was supplied — Phase 20 clients should persist this and send "
        "it on the next turn."
    )


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


class SignUpRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=8, max_length=200)
    full_name: str | None = Field(None, max_length=200)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        if not _EMAIL_RE.match(value):
            raise ValueError("must be a valid email address")
        return value


class SignInRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=1, max_length=200)


class PasswordResetRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        if not _EMAIL_RE.match(value):
            raise ValueError("must be a valid email address")
        return value


class AuthUserSchema(BaseModel):
    id: str
    email: str | None = None
    full_name: str | None = None


class AuthSessionResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: AuthUserSchema


class CustomerProfileSchema(BaseModel):
    id: str
    email: str
    full_name: str | None = None
    company_name: str | None = None
    industry: str | None = None
    phone: str | None = None


class UpdateProfileRequest(BaseModel):
    full_name: str | None = Field(None, max_length=200)
    company_name: str | None = Field(None, max_length=200)
    industry: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=50)


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: str | None = None
    updated_at: str | None = None


class ConversationMessageSchema(BaseModel):
    id: str
    role: str
    content: str
    citations: list = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    created_at: str | None = None


class ConversationDetail(BaseModel):
    conversation: ConversationSummary
    messages: list[ConversationMessageSchema]


class CreateConversationRequest(BaseModel):
    first_message: str | None = Field(None, max_length=2000)


class RenameConversationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


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


class SaveComparisonRequest(BaseModel):
    product_ids: list[str] = Field(..., min_length=2, max_length=10)


class SavedComparisonSchema(BaseModel):
    id: str
    product_ids: list[str]
    created_at: str | None = None


class SaveRecommendationRequest(BaseModel):
    products: list[str] = Field(..., min_length=1, max_length=10)
    question: str = Field(..., min_length=1, max_length=2000)
    recommendation: str = Field(..., min_length=1, max_length=8000)


class SavedRecommendationSchema(BaseModel):
    id: str
    products: list[str]
    question: str
    recommendation: str
    created_at: str | None = None


class AppointmentSlotSchema(BaseModel):
    time: str
    available: bool


class DailyAvailabilitySchema(BaseModel):
    date: str
    day_label: str
    slots: list[AppointmentSlotSchema]
    fully_booked: bool


class BookAppointmentRequest(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    time: str
    name: str = Field(..., min_length=1, max_length=200)
    email: str = Field(..., min_length=3, max_length=320)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        if not _EMAIL_RE.match(value):
            raise ValueError("must be a valid email address")
        return value


class AppointmentSchema(BaseModel):
    id: str
    date: str
    time: str
    name: str
    email: str
    status: str


class SubmitFeedbackRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    answer: str = Field(..., min_length=1, max_length=8000)
    rating: str = Field(..., pattern="^(helpful|not_helpful)$")
    comment: str | None = Field(None, max_length=2000)
    session_id: str | None = None
    conversation_id: str | None = None


class FeedbackSchema(BaseModel):
    id: str
    question: str
    answer: str
    rating: str
    comment: str | None = None
    created_at: str | None = None


class NotificationSchema(BaseModel):
    id: str
    type: str
    title: str
    body: str | None = None
    is_read: bool
    created_at: str | None = None


class UnreadCountSchema(BaseModel):
    count: int
