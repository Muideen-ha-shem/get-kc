"""Shared customer-facing fallback copy — used anywhere a chat answer must be
produced without any grounded evidence or LLM output to work from. Centralized
so every fallback path reads identically to the customer, and so the tone
standard (empathetic, no internal/system language, offers to keep helping
inside HavisIQ) only needs to be written once. See response_generator.py's
tone guardrail for the same standard applied to LLM-generated answers.
"""

from __future__ import annotations

NO_EVIDENCE_FALLBACK = (
    "I want to make sure I give you accurate information, so let me ask — "
    "could you tell me a bit more about what you're trying to achieve? "
    "I'm happy to help you find the right HavisIQ solution, or connect you "
    "with a specialist if that's easier."
)

GENERATION_FAILED_FALLBACK = (
    "I want to make sure I get this right for you — could you rephrase "
    "that, or tell me a little more about what you need? I'm here to help."
)
