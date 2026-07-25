"""Tests for QueryRewriter."""

from __future__ import annotations

from src.services.query.query_rewriter import QueryRewriter


# ---------------------------------------------------------------------------
# Basic rewriting
# ---------------------------------------------------------------------------


class TestQueryRewriterBasics:
    def test_empty_question_returns_original(self):
        rewriter = QueryRewriter()
        assert rewriter.rewrite("") == ""
        assert rewriter.rewrite("   ") == "   "

    def test_strips_filler_words(self):
        rewriter = QueryRewriter(filler_words=["what", "is", "the"])
        result = rewriter.rewrite("What is the pricing?")
        lower = result.lower()
        assert "what" not in lower.split()
        assert "pricing" in lower

    def test_pure_filler_question_falls_back_to_original(self):
        rewriter = QueryRewriter(filler_words=["what", "is", "the"])
        original = "What is the?"
        assert rewriter.rewrite(original) == original

    def test_never_raises_on_weird_input(self):
        rewriter = QueryRewriter()
        # Should not raise for any of these
        for weird in [None, 12345, object()]:
            try:
                result = rewriter.rewrite(weird)  # type: ignore[arg-type]
            except Exception as exc:
                raise AssertionError(f"rewrite() raised for {weird!r}: {exc}")


# ---------------------------------------------------------------------------
# Company name canonicalisation + site hint
# ---------------------------------------------------------------------------


class TestQueryRewriterCompany:
    def test_canonicalizes_short_company_name(self):
        rewriter = QueryRewriter(company_name="ha-shem", company_full_name="Ha-Shem Limited")
        result = rewriter.rewrite("What cybersecurity services does Ha-Shem offer?")
        assert "Ha-Shem Limited" in result

    def test_does_not_duplicate_already_full_name(self):
        rewriter = QueryRewriter(company_name="ha-shem", company_full_name="Ha-Shem Limited")
        result = rewriter.rewrite("Tell me about Ha-Shem Limited services")
        assert result.count("Ha-Shem Limited") == 1

    def test_site_hint_added_when_company_mentioned(self):
        rewriter = QueryRewriter(company_name="ha-shem", site_hint_domain="ha-shem.com")
        result = rewriter.rewrite("What does Ha-Shem do?")
        assert "site:ha-shem.com" in result

    def test_site_hint_not_added_when_company_not_mentioned(self):
        rewriter = QueryRewriter(company_name="ha-shem", site_hint_domain="ha-shem.com")
        result = rewriter.rewrite("What is the weather like today?")
        assert "site:ha-shem.com" not in result

    def test_no_company_configured_never_adds_site_hint(self):
        rewriter = QueryRewriter(site_hint_domain="ha-shem.com")  # no company_name
        result = rewriter.rewrite("What does Ha-Shem do?")
        assert "site:" not in result


# ---------------------------------------------------------------------------
# Freshness detection
# ---------------------------------------------------------------------------


class TestQueryRewriterFreshness:
    def test_freshness_keyword_appends_current_month_year(self):
        rewriter = QueryRewriter()
        result = rewriter.rewrite("What is the latest news about the company?")
        # Should contain a 4-digit year somewhere (current year)
        assert any(tok.isdigit() and len(tok) == 4 for tok in result.split())

    def test_no_freshness_keyword_no_date_appended(self):
        rewriter = QueryRewriter()
        result = rewriter.rewrite("What services do you offer?")
        assert not any(tok.isdigit() and len(tok) == 4 for tok in result.split())

    def test_detect_entities_reports_freshness_keyword(self):
        rewriter = QueryRewriter()
        entities = rewriter.detect_entities("What's the latest update?")
        assert entities["freshness"] == "latest"

    def test_detect_entities_no_freshness(self):
        rewriter = QueryRewriter()
        entities = rewriter.detect_entities("What services do you offer?")
        assert entities["freshness"] is None


# ---------------------------------------------------------------------------
# Entity detection
# ---------------------------------------------------------------------------


class TestQueryRewriterEntities:
    def test_detect_entities_company_flag(self):
        rewriter = QueryRewriter(company_name="ha-shem")
        assert rewriter.detect_entities("Tell me about Ha-Shem")["company"] is True
        assert rewriter.detect_entities("Tell me about a random topic")["company"] is False

    def test_detect_entities_products(self):
        rewriter = QueryRewriter(products=["Havis 360", "SolarWinds Training"])
        result = rewriter.detect_entities("Tell me about Havis 360 pricing")
        assert "Havis 360" in result["products"]
        assert "SolarWinds Training" not in result["products"]

    def test_products_survive_filler_stripping(self):
        rewriter = QueryRewriter(products=["Havis 360"])
        result = rewriter.rewrite("What is Havis 360?")
        assert "Havis 360" in result


# ---------------------------------------------------------------------------
# Environment variable defaults
# ---------------------------------------------------------------------------


class TestQueryRewriterEnvDefaults:
    def test_company_name_from_env(self, monkeypatch):
        monkeypatch.setenv("COMPANY_NAME", "acme")
        monkeypatch.delenv("COMPANY_FULL_NAME", raising=False)
        monkeypatch.delenv("OFFICIAL_DOMAINS", raising=False)
        rewriter = QueryRewriter()
        assert rewriter._company_name == "acme"

    def test_explicit_args_override_env(self, monkeypatch):
        monkeypatch.setenv("COMPANY_NAME", "should-not-be-used")
        rewriter = QueryRewriter(company_name="explicit-corp")
        assert rewriter._company_name == "explicit-corp"

    def test_site_hint_domain_from_official_domains_env(self, monkeypatch):
        monkeypatch.delenv("COMPANY_NAME", raising=False)
        monkeypatch.setenv("OFFICIAL_DOMAINS", "ha-shem.com,ha-shemacademy.com")
        rewriter = QueryRewriter()
        assert rewriter._site_hint_domain == "ha-shem.com"

    def test_no_env_configured_defaults_to_none(self, monkeypatch):
        monkeypatch.delenv("COMPANY_NAME", raising=False)
        monkeypatch.delenv("COMPANY_FULL_NAME", raising=False)
        monkeypatch.delenv("OFFICIAL_DOMAINS", raising=False)
        rewriter = QueryRewriter()
        assert rewriter._company_name is None
        assert rewriter._site_hint_domain is None
