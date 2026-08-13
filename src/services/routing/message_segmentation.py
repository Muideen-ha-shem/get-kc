"""segment_message — deterministic clause-splitting for compound customer
messages ("I want to understand SPIDIFY, compare it with V-Login, and then
book a demo.") so each clause's intent can be resolved independently,
rather than a single action keyword appearing anywhere in the message
hijacking the entire request.

Live-confirmed bug this fixes: "book a demo" appearing at the end of a
longer message made the ENTIRE message — including two earlier, unrelated
knowledge requests — jump straight into the demo workflow, silently
dropping the "understand SPIDIFY"/"compare with V-Login" parts.

Deliberately conservative — splits only when an explicit, unambiguous
sequencing marker is present ("and then" / ", then"), never a bare comma
or bare "and"/"then" alone. This is the safety property that keeps it from
misfiring on ordinary prose: "SPIDIFY, our identity verification product,
is popular" (appositive commas) and "Compare SPIDIFY and V-Login" (a
genuine two-item comparison, no sequencing marker at all) both come back
as a single, unmodified segment. Only once the anchor proves the message
is a deliberate sequence of clauses does the text before it get split
further on commas. No LLM call — pure regex, same philosophy as every
other detector in this codebase.
"""

from __future__ import annotations

import re

_ANCHOR_RE = re.compile(r",?\s*and\s+then\s+|,\s*then\s+", re.IGNORECASE)
_COMMA_RE = re.compile(r",\s*")


def segment_message(message: str | None) -> list[str]:
    """Split *message* into independent clauses. Returns ``[message]``
    unchanged — a single segment — for anything without an explicit
    sequencing marker, which callers use as the signal to skip multi-intent
    handling entirely and behave exactly as before this feature existed."""
    if not message:
        return [message]
    if not _ANCHOR_RE.search(message):
        return [message]

    parts = _ANCHOR_RE.split(message, maxsplit=1)
    if len(parts) != 2:
        return [message]

    head, tail = parts
    clauses = [c.strip() for c in _COMMA_RE.split(head) if c.strip()]
    tail = tail.strip()
    if tail:
        clauses.append(tail)

    return clauses if len(clauses) > 1 else [message]
