"""Tests for DomainQualityFilter."""

from __future__ import annotations

from src.services.filtering.domain_filter import DomainQualityFilter


# ---------------------------------------------------------------------------
# Basic filtering
# ---------------------------------------------------------------------------


class TestDomainQualityFilterBasics:
    def test_empty_urls_returns_empty(self):
        domain_filter = DomainQualityFilter()
        assert domain_filter.filter([]) == []

    def test_generic_urls_pass_through(self):
        domain_filter = DomainQualityFilter()
        urls = ["https://random-blog.example.com/post"]
        assert domain_filter.filter(urls) == urls

    def test_never_raises_on_malformed_url(self):
        domain_filter = DomainQualityFilter()
        result = domain_filter.filter(["not a url", "", "://broken"])
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Blocking low-quality domains
# ---------------------------------------------------------------------------


class TestDomainQualityFilterBlocking:
    def test_drops_dictionary_sites(self):
        domain_filter = DomainQualityFilter()
        urls = [
            "https://en.wiktionary.org/wiki/what",
            "https://www.merriam-webster.com/dictionary/what",
            "https://www.dictionary.com/browse/what",
        ]
        assert domain_filter.filter(urls) == []

    def test_drops_quora(self):
        domain_filter = DomainQualityFilter()
        urls = ["https://www.quora.com/What-is-the-definition-of-what"]
        assert domain_filter.filter(urls) == []

    def test_keeps_good_urls_drops_bad_ones_in_mixed_list(self):
        domain_filter = DomainQualityFilter()
        urls = [
            "https://www.quora.com/something",
            "https://ha-shem.com/about",
            "https://en.wiktionary.org/wiki/x",
        ]
        result = domain_filter.filter(urls)
        assert "https://ha-shem.com/about" in result
        assert not any("quora" in u or "wiktionary" in u for u in result)

    def test_custom_blocked_domains(self):
        domain_filter = DomainQualityFilter(blocked_domains=["spam-site.example.com"])
        urls = ["https://spam-site.example.com/page", "https://legit.example.com/page"]
        result = domain_filter.filter(urls)
        assert result == ["https://legit.example.com/page"]

    def test_should_fetch_reflects_blocking(self):
        domain_filter = DomainQualityFilter()
        assert domain_filter.should_fetch("https://ha-shem.com") is True
        assert domain_filter.should_fetch("https://www.quora.com/x") is False


# ---------------------------------------------------------------------------
# Tier ordering
# ---------------------------------------------------------------------------


class TestDomainQualityFilterOrdering:
    def test_official_domain_sorted_first(self):
        domain_filter = DomainQualityFilter(official_domains=["ha-shem.com"])
        urls = [
            "https://www.facebook.com/hashemlimited",
            "https://random-blog.example.com",
            "https://ha-shem.com/about",
        ]
        result = domain_filter.filter(urls)
        assert result[0] == "https://ha-shem.com/about"

    def test_social_media_sorted_after_default(self):
        domain_filter = DomainQualityFilter()
        urls = [
            "https://www.facebook.com/page",
            "https://random-blog.example.com",
        ]
        result = domain_filter.filter(urls)
        assert result[0] == "https://random-blog.example.com"
        assert result[1] == "https://www.facebook.com/page"

    def test_trusted_news_sorted_before_social_media(self):
        domain_filter = DomainQualityFilter()
        urls = [
            "https://www.instagram.com/page",
            "https://www.reuters.com/story",
        ]
        result = domain_filter.filter(urls)
        assert result[0] == "https://www.reuters.com/story"

    def test_relative_order_preserved_within_tier(self):
        domain_filter = DomainQualityFilter()
        urls = [
            "https://siteA.example.com/1",
            "https://siteB.example.com/2",
            "https://siteC.example.com/3",
        ]
        assert domain_filter.filter(urls) == urls


# ---------------------------------------------------------------------------
# Social media blocking toggle
# ---------------------------------------------------------------------------


class TestDomainQualityFilterSocialMediaToggle:
    def test_social_media_kept_by_default(self):
        domain_filter = DomainQualityFilter()
        urls = ["https://www.facebook.com/page"]
        assert domain_filter.filter(urls) == urls

    def test_social_media_blocked_when_enabled(self):
        domain_filter = DomainQualityFilter(block_social_media=True)
        urls = ["https://www.facebook.com/page"]
        assert domain_filter.filter(urls) == []


# ---------------------------------------------------------------------------
# Environment variable defaults
# ---------------------------------------------------------------------------


class TestDomainQualityFilterEnvDefaults:
    def test_official_domains_from_env(self, monkeypatch):
        monkeypatch.setenv("OFFICIAL_DOMAINS", "ha-shem.com, ha-shemacademy.com")
        domain_filter = DomainQualityFilter()
        assert domain_filter._official_domains == ("ha-shem.com", "ha-shemacademy.com")

    def test_explicit_official_domains_override_env(self, monkeypatch):
        monkeypatch.setenv("OFFICIAL_DOMAINS", "should-not-be-used.com")
        domain_filter = DomainQualityFilter(official_domains=["explicit.com"])
        assert domain_filter._official_domains == ("explicit.com",)
