"""action_workflow — deterministic field-collection, confirmation, and
execution for the three confirmed action workflows (escalation, appointment,
demo request).

Phase 2 of the action-integrity fix: Phase 1 (see ``routing.action_intent``)
stops these messages from ever reaching retrieval/web search and stops the
AI from claiming an unconfirmed action succeeded, but only ever produces a
single canned ack. This module adds the missing middle: collect exactly the
fields each backend structurally needs (one per turn, no free-text NLU),
show a plain summary, and only ever call a real backend service — never
generation, never a second classifier — once the customer explicitly
confirms. ``execute_action`` is the only function here with side effects;
everything else is pure text/state building, same testable-without-mocks
style as ``self_identity.py``/``action_intent.py``.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from ...shared.logging import get_logger
from ...shared.product_registry import PRODUCT_REGISTRY
from .session_context import PendingAction, SessionState

logger: logging.Logger = get_logger(__name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_OPTIONAL_FIELDS: frozenset[str] = frozenset({"company"})
_SKIP_WORDS: frozenset[str] = frozenset({"skip", "none", "n/a", "no"})

_FIELD_QUESTIONS: dict[str, str] = {
    "product": "Which HavisIQ solution would you like a demo of?",
    "name": "Could I get your name?",
    "email": "And what's the best email to reach you at?",
    "company": "Which company are you with? (reply \"skip\" if you'd rather not say)",
}


# ---------------------------------------------------------------------------
# Field requirements
# ---------------------------------------------------------------------------


def required_fields(kind: str, session_state: SessionState | None) -> list[str]:
    """The ordered queue of fields still needed to act on *kind*. Reuses
    ``session_state.last_product()`` (Phase 20) so a demo request never
    re-asks which product when the session already discussed one — matches
    the "don't ask again if already known" requirement.
    """
    if kind == "escalation":
        # create_direct() only needs workspace context (already available
        # server-side) — nothing is structurally required from the customer.
        return []
    if kind == "appointment":
        return ["slot", "name", "email"]
    if kind == "demo":
        fields = ["name", "email", "company"]
        if session_state is None or not session_state.last_product():
            fields = ["product", *fields]
        return fields
    return []


# ---------------------------------------------------------------------------
# Prompting
# ---------------------------------------------------------------------------


def _format_slot_options(appointment_service: Any, workspace_id: str | None) -> tuple[str, list[str]]:
    """Queries REAL availability and returns (display text, offered_slots)
    where each entry in offered_slots is ``"label::date::time"`` — an
    internal encoding (never shown to the customer) so the next turn's
    reply can be matched back to a real, bookable (date, time) pair without
    any date/time parsing."""
    if appointment_service is None:
        return ("", [])
    try:
        availability = appointment_service.get_availability(days=4, workspace_id=workspace_id)
    except Exception as exc:
        logger.warning("action_workflow: availability lookup failed — %s.", exc)
        return ("", [])

    offered: list[str] = []
    labels: list[str] = []
    for day in availability:
        if day.fully_booked:
            continue
        for slot in day.slots:
            if not slot.get("available"):
                continue
            label = f"{day.day_label} {slot['time']}"
            offered.append(f"{label}::{day.date}::{slot['time']}")
            labels.append(label)
            if len(labels) >= 6:
                break
        if len(labels) >= 6:
            break
    return (", ".join(labels), offered)


def build_field_prompt(
    pending: PendingAction, *, appointment_service: Any = None, workspace_id: str | None = None
) -> str:
    """The next question to ask, for the field at the front of
    ``pending.missing``. Callers are expected to have already checked
    ``pending.missing`` is non-empty (an escalation with zero required
    fields never calls this — see ``chat_orchestrator``)."""
    field = pending.missing[0]
    if field == "slot":
        slots_text, offered = _format_slot_options(appointment_service, workspace_id)
        pending.offered_slots = offered
        if not slots_text:
            return (
                "I'd love to get that booked, but I'm not seeing any open slots right "
                "now — could you tell me your name and email, and I'll follow up with "
                "the next available time?"
            )
        return f"I can help set that up — here's what's actually open: {slots_text}. Which works for you?"
    return _FIELD_QUESTIONS.get(field, "Could you tell me a bit more?")


def build_confirmation_summary(pending: PendingAction) -> str:
    """A plain-text recap of everything collected, asking for a final
    go-ahead — never a claim that anything has happened yet."""
    if pending.kind == "escalation":
        return (
            "I can raise this with a support specialist for you — I'll flag it now so "
            "someone follows up. Would you like me to go ahead?"
        )
    if pending.kind == "appointment":
        slot_label = pending.fields.get("slot_label", "the selected time")
        return (
            f"Here's what I have: {slot_label}, name: {pending.fields.get('name', '')}, "
            f"email: {pending.fields.get('email', '')}. Would you like me to confirm "
            "this appointment?"
        )
    # demo
    product = pending.fields.get("product", "the solution you mentioned")
    parts = [f"Product: {product}", f"Name: {pending.fields.get('name', '')}", f"Email: {pending.fields.get('email', '')}"]
    company = pending.fields.get("company", "")
    if company:
        parts.append(f"Company: {company}")
    summary = ", ".join(parts)
    return f"Here's what I have: {summary}. Would you like me to submit this demo request?"


# ---------------------------------------------------------------------------
# Field collection
# ---------------------------------------------------------------------------


def _match_product(text: str) -> str | None:
    lowered = text.lower()
    for name, info in PRODUCT_REGISTRY.items():
        if name.lower() in lowered:
            return name
        for alias in info.get("aliases", ()):
            if alias.lower() in lowered:
                return name
    return None


def collect_field(
    pending: PendingAction, message: str, *, appointment_service: Any = None, workspace_id: str | None = None
) -> tuple[PendingAction, str]:
    """Validate *message* against the field at the front of
    ``pending.missing`` and advance. Returns ``(updated_pending,
    response_text)`` — the response is either a re-prompt (invalid input,
    ``pending`` unchanged) or the next field's question / the final
    confirmation summary once every required field is filled."""
    field = pending.missing[0]
    cleaned = message.strip()

    if field == "email":
        if not _EMAIL_RE.match(cleaned):
            return pending, "That doesn't look like a valid email — could you double-check it?"
        pending.fields["email"] = cleaned

    elif field == "slot":
        matched = None
        lowered_msg = cleaned.lower()
        for entry in pending.offered_slots:
            label, date, time = entry.split("::")
            if label.lower() in lowered_msg:
                matched = (label, date, time)
                break
        if matched is None:
            slots_text = ", ".join(entry.split("::")[0] for entry in pending.offered_slots)
            return pending, f"I didn't catch a matching time — the open slots are: {slots_text}. Which one works?"
        pending.fields["slot_label"], pending.fields["date"], pending.fields["time"] = matched

    elif field == "product":
        product = _match_product(cleaned)
        if product is None:
            return pending, "I didn't recognize that solution — which HavisIQ product would you like a demo of?"
        pending.fields["product"] = product

    elif field in _OPTIONAL_FIELDS:
        pending.fields[field] = "" if cleaned.lower() in _SKIP_WORDS else cleaned

    else:  # "name" and any other free-text field — accepted as-is
        if not cleaned:
            return pending, "Sorry, I didn't catch that — could you repeat it?"
        pending.fields[field] = cleaned

    pending.missing = pending.missing[1:]
    if pending.missing:
        return pending, build_field_prompt(pending, appointment_service=appointment_service, workspace_id=workspace_id)

    pending.status = "awaiting_confirmation"
    return pending, build_confirmation_summary(pending)


# ---------------------------------------------------------------------------
# Execution — the only function with real side effects
# ---------------------------------------------------------------------------


def execute_action(
    pending: PendingAction,
    *,
    workspace_id: str | None,
    workspace_name: str | None,
    conversation_id: str | None,
    escalation_service: Any = None,
    appointment_service: Any = None,
) -> str:
    """Performs the real backend write and returns text built strictly from
    the real result — never text-first. Every branch either calls the
    backend and reports what actually happened, or (no service configured,
    or the backend itself rejects the request) reports an honest failure —
    never a fabricated success.
    """
    if pending.kind == "escalation":
        if escalation_service is None or not workspace_id or not workspace_name:
            return "I wasn't able to submit that just now — could you try again in a moment?"
        try:
            escalation = escalation_service.create_direct(
                workspace_id=workspace_id,
                workspace_name=workspace_name,
                conversation_id=conversation_id,
                question=pending.original_question or "Customer requested a specialist.",
                trigger_reason="explicit_request",
            )
        except Exception as exc:
            logger.warning("action_workflow: escalation creation failed — %s.", exc)
            return "I wasn't able to submit that just now — could you try again in a moment?"

        department = escalation.department or "support"
        if escalation.assigned_agent_id:
            return f"Done — I've connected this with a {department} specialist who will be with you shortly."
        return f"Your request has been submitted to our {department} team. No one is available this exact moment, but it's in the queue and someone will follow up shortly."

    if pending.kind == "appointment":
        if appointment_service is None:
            return "I wasn't able to submit that just now — could you try again in a moment?"
        date = pending.fields.get("date")
        time = pending.fields.get("time")
        name = pending.fields.get("name", "")
        email = pending.fields.get("email", "")
        try:
            appointment = appointment_service.book(date, time, name, email, workspace_id=workspace_id)
        except Exception as exc:
            slots_text, _ = _format_slot_options(appointment_service, workspace_id)
            logger.info("action_workflow: appointment booking failed — %s.", exc)
            if slots_text:
                return f"That time was just taken — here's what's still open: {slots_text}. Would you like to pick another?"
            return "That time is no longer available, and I'm not seeing anything else open right now — could you try again shortly?"
        return f"You're confirmed for {appointment.appointment_date} at {appointment.time_slot}."

    if pending.kind == "demo":
        try:
            from ...api.services.demo_requests import DemoRequestTableMissingError, submit_demo_request
        except ImportError:  # pragma: no cover - supports package execution
            from src.api.services.demo_requests import DemoRequestTableMissingError, submit_demo_request

        try:
            submit_demo_request(
                name=pending.fields.get("name", ""),
                email=pending.fields.get("email", ""),
                company=pending.fields.get("company") or None,
                use_case=pending.original_question or None,
                product=pending.fields.get("product"),
            )
        except DemoRequestTableMissingError as exc:
            logger.warning("action_workflow: demo_requests table missing — %s.", exc)
            return "I wasn't able to submit that just now — let me connect you with support instead."
        except Exception as exc:
            logger.warning("action_workflow: demo request submission failed — %s.", exc)
            return "I wasn't able to submit that just now — could you try again in a moment?"

        product = pending.fields.get("product", "that solution")
        return f"Your {product} demo request has been submitted. Our sales team will follow up using the contact details you gave me."

    return "I wasn't able to submit that just now — could you try again in a moment?"
