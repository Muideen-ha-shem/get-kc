from __future__ import annotations

from typing import Any

from ...api.services.generator import generate_answer as legacy_generate_answer


class SupportService:
    """Business service for composing grounded support responses."""

    def generate_answer(self, question: str, context_text: str, sources: list[str]) -> dict[str, Any]:
        return legacy_generate_answer(question, context_text, sources)
