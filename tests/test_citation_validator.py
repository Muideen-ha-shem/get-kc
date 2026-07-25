"""Tests for CitationValidator."""

from __future__ import annotations

from src.services.validation.citation_validator import CitationValidator


def _citation(url="https://example.com", title="Title", source_type="web", score=0.8):
    return {"url": url, "title": title, "source_type": source_type, "score": score}


# ---------------------------------------------------------------------------
# Basics
# ---------------------------------------------------------------------------


class TestCitationValidatorBasics:
    def test_empty_list_returns_empty(self):
        validator = CitationValidator()
        assert validator.validate([]) == []
        assert validator.validate(None) == []

    def test_valid_citations_pass_through(self):
        validator = CitationValidator()
        citations = [_citation(url="https://a.example.com"), _citation(url="https://b.example.com")]
        assert validator.validate(citations) == citations

    def test_preserves_order(self):
        validator = CitationValidator()
        citations = [_citation(url=f"https://{i}.example.com") for i in range(5)]
        assert validator.validate(citations) == citations


# ---------------------------------------------------------------------------
# Placeholder URL removal
# ---------------------------------------------------------------------------


class TestCitationValidatorPlaceholders:
    def test_removes_unknown_url_case_insensitive(self):
        validator = CitationValidator()
        citations = [_citation(url="Unknown URL"), _citation(url="unknown url"), _citation(url="UNKNOWN URL")]
        assert validator.validate(citations) == []

    def test_removes_empty_url(self):
        validator = CitationValidator()
        citations = [_citation(url=""), _citation(url="   ")]
        assert validator.validate(citations) == []

    def test_removes_na_none_null_placeholders(self):
        validator = CitationValidator()
        citations = [_citation(url="N/A"), _citation(url="None"), _citation(url="null")]
        assert validator.validate(citations) == []

    def test_keeps_real_url_alongside_placeholder(self):
        validator = CitationValidator()
        citations = [_citation(url="Unknown URL"), _citation(url="https://real.example.com")]
        result = validator.validate(citations)
        assert len(result) == 1
        assert result[0]["url"] == "https://real.example.com"


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


class TestCitationValidatorDeduplication:
    def test_removes_duplicate_urls(self):
        validator = CitationValidator()
        citations = [_citation(url="https://a.example.com"), _citation(url="https://a.example.com")]
        result = validator.validate(citations)
        assert len(result) == 1

    def test_dedup_is_case_insensitive(self):
        validator = CitationValidator()
        citations = [_citation(url="https://A.example.com"), _citation(url="https://a.example.com")]
        result = validator.validate(citations)
        assert len(result) == 1

    def test_keeps_first_occurrence(self):
        validator = CitationValidator()
        first = _citation(url="https://a.example.com", title="First")
        second = _citation(url="https://a.example.com", title="Second")
        result = validator.validate([first, second])
        assert result == [first]


# ---------------------------------------------------------------------------
# Score filtering
# ---------------------------------------------------------------------------


class TestCitationValidatorScoreFiltering:
    def test_min_score_drops_low_score_citations(self):
        validator = CitationValidator(min_score=0.5)
        citations = [_citation(url="https://a.example.com", score=0.2), _citation(url="https://b.example.com", score=0.8)]
        result = validator.validate(citations)
        assert len(result) == 1
        assert result[0]["url"] == "https://b.example.com"

    def test_no_min_score_keeps_all(self):
        validator = CitationValidator()
        citations = [_citation(url="https://a.example.com", score=0.01)]
        assert validator.validate(citations) == citations

    def test_none_score_not_dropped_by_min_score(self):
        validator = CitationValidator(min_score=0.5)
        citations = [_citation(url="https://a.example.com", score=None)]
        assert validator.validate(citations) == citations


# ---------------------------------------------------------------------------
# Malformed input resilience
# ---------------------------------------------------------------------------


class TestCitationValidatorResilience:
    def test_skips_non_dict_entries(self):
        validator = CitationValidator()
        result = validator.validate([_citation(url="https://a.example.com"), "not a dict", 42, None])
        assert len(result) == 1

    def test_missing_url_key_treated_as_placeholder(self):
        validator = CitationValidator()
        result = validator.validate([{"title": "No URL key"}])
        assert result == []
