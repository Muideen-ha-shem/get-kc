"""Tests for scripts/product_metadata.py."""

from __future__ import annotations

from scripts.product_metadata import product_metadata_for_url, PRODUCT_SITES


class TestProductMetadataForUrl:
    def test_spidify_domain(self):
        meta = product_metadata_for_url("https://havisspidify.com/features")
        assert meta["product"] == "SPIDIFY"
        assert meta["category"] == "Identity Verification"
        assert meta["source_type"] == "official_product"

    def test_zivaaira_domain(self):
        meta = product_metadata_for_url("https://aira.havis360.com/recruitment")
        assert meta["product"] == "ZivaAIRA"
        assert meta["category"] == "HR Recruitment"
        assert meta["source_type"] == "official_product"

    def test_www_prefix_stripped(self):
        meta = product_metadata_for_url("https://www.havisspidify.com/about")
        assert meta["product"] == "SPIDIFY"

    def test_unrecognized_domain_returns_all_none(self):
        meta = product_metadata_for_url("https://ha-shem.com/about")
        assert meta == {"product": None, "category": None, "source_type": None}

    def test_empty_url_returns_all_none(self):
        assert product_metadata_for_url("") == {"product": None, "category": None, "source_type": None}

    def test_malformed_url_does_not_raise(self):
        meta = product_metadata_for_url("not a url at all")
        assert meta["product"] is None

    def test_subdomain_path_and_query_ignored(self):
        meta = product_metadata_for_url("https://havisspidify.com/path/to/page?query=1#frag")
        assert meta["product"] == "SPIDIFY"


class TestProductSites:
    def test_product_sites_have_required_keys(self):
        for name, info in PRODUCT_SITES.items():
            assert "url" in info
            assert "domain" in info
            assert "category" in info

    def test_product_sites_domain_matches_url(self):
        for name, info in PRODUCT_SITES.items():
            assert info["domain"] in info["url"]
