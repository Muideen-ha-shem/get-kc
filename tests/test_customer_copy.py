"""Tests for the shared customer-facing fallback copy — ensures every
fallback string stays non-jargony (no internal/system language) regardless
of which call site uses it."""

from __future__ import annotations

import pytest

from src.shared.customer_copy import GENERATION_FAILED_FALLBACK, NO_EVIDENCE_FALLBACK

_FORBIDDEN_WORDS = ("evidence", "context", "knowledge base", "retrieval", "system")


@pytest.mark.parametrize("text", [NO_EVIDENCE_FALLBACK, GENERATION_FAILED_FALLBACK])
def test_fallback_is_non_empty(text):
    assert text.strip()


@pytest.mark.parametrize("text", [NO_EVIDENCE_FALLBACK, GENERATION_FAILED_FALLBACK])
@pytest.mark.parametrize("word", _FORBIDDEN_WORDS)
def test_fallback_avoids_internal_jargon(text, word):
    assert word not in text.lower()
