"""detect_confirmation — recognizes a bare "yes"/"no" reply to a pending
action confirmation prompt.

"yes" is deliberately exact-match on the whole (trimmed, lowercased)
message, not a substring search — a bare "yes" reply is short and
unambiguous by construction; substring matching would risk misreading
"yes" inside an unrelated longer sentence as a confirmation. Live-confirmed
gap: "cancel"/"never mind" are asymmetric — "cancel that", "actually
cancel", and "never mind" are all natural, common phrasings that an
exact-match "cancel" misses entirely, and (unlike "yes") "cancel"/"never
mind" appearing as a substring of a genuine field answer (a name, email,
company) is vanishingly unlikely — so these are substring-matched instead.

This alone isn't what makes confirmation detection "contextual" (per the
product requirement that a stray "Hi" -> "Yes" must never trigger an
action) — the caller (ChatOrchestrator's Step 0.6) only ever consults this
when ``SessionContext.get_pending_action()`` returns a real pending action.
Without one, this function is never even called.
"""

from __future__ import annotations

from typing import Literal

_YES: frozenset[str] = frozenset({
    "yes", "yes please", "yeah", "yep", "sure", "go ahead", "do it",
    "proceed", "that's fine", "thats fine", "okay", "ok",
})

_NO_EXACT: frozenset[str] = frozenset({"no", "nope", "not now"})

_CANCEL_PHRASES: tuple[str, ...] = ("cancel", "never mind", "nevermind")

# Live-confirmed bug: once a pending action is cleared (the demo request
# above was already submitted), "Cancel that" has nothing left to cancel —
# `detect_confirmation` is never even consulted (no pending action for
# ChatOrchestrator's Step 0.6 to gate it on), so the bare phrase fell
# straight through to ordinary RAG, which hallucinated an unrelated
# "cancel your PayCheq subscription" answer. `detect_bare_cancellation`
# closes that gap WITHOUT a pending action — but deliberately exact-match,
# not substring, so a real product question like "How do I cancel my
# PayCheq subscription?" still reaches RAG (which may have a real answer)
# instead of being swallowed by this.
_BARE_CANCEL_PHRASES: frozenset[str] = frozenset({
    "cancel", "cancel that", "cancel this", "actually cancel", "stop",
    "stop that", "never mind", "nevermind",
})


def detect_confirmation(question: str | None) -> Literal["yes", "no"] | None:
    """Classify *question* as a confirmation ``"yes"``, ``"no"``, or
    ``None`` if it's neither a bare affirmative nor negative/cancelling
    reply."""
    if not question:
        return None
    cleaned = question.strip().lower().rstrip("!.")
    if cleaned in _YES:
        return "yes"
    if cleaned in _NO_EXACT:
        return "no"
    if any(phrase in cleaned for phrase in _CANCEL_PHRASES):
        return "no"
    return None


def detect_bare_cancellation(question: str | None) -> bool:
    """True for a short cancel/stop phrase with no pending action to
    attach it to — used by ChatOrchestrator to respond honestly ("nothing
    active to cancel") instead of letting it reach RAG. Exact-match on the
    whole trimmed message, unlike ``detect_confirmation``'s substring
    match, precisely so a real, longer product question isn't swallowed.
    """
    if not question:
        return False
    cleaned = question.strip().lower().rstrip("!.")
    return cleaned in _BARE_CANCEL_PHRASES
