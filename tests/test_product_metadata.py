"""Tests for scripts/product_metadata.py."""

from __future__ import annotations

import pytest

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

    def test_all_thirteen_products_present(self):
        expected = {
            "SPIDIFY", "ZivaAIRA", "V-Login", "STAAS", "WeCare", "Havis Xpend",
            "Havis Vacay", "Havis iReport", "Havis REMA", "Havis eCertify",
            "KwikAlert", "AppManage", "PayCheq",
        }
        assert set(PRODUCT_SITES) == expected


class TestProductMetadataPathBasedMatching:
    """The HAVIS-360 catalog shares the ha-shem.com domain — these products
    are distinguished by URL path, not domain, unlike SPIDIFY/ZivaAIRA."""

    @pytest.mark.parametrize(
        "path,expected_product,expected_category",
        [
            ("/HAVIS-360/v-login/", "V-Login", "Visitor & Access Management"),
            ("/HAVIS-360/staas/", "STAAS", "Workforce Attendance"),
            ("/HAVIS-360/wecare/", "WeCare", "Customer & Employee Support"),
            ("/HAVIS-360/havis-xpend/", "Havis Xpend", "Expense Management"),
            ("/HAVIS-360/havis-vacay/", "Havis Vacay", "Leave Management"),
            ("/HAVIS-360/havis-ireport/", "Havis iReport", "Reporting"),
            ("/HAVIS-360/havis-rema/", "Havis REMA", "Receipt & Document Management"),
            ("/HAVIS-360/havis-ecertify/", "Havis eCertify", "Learning & Certification"),
            ("/HAVIS-360/kwikalert/", "KwikAlert", "Emergency Communication"),
            ("/HAVIS-360/appmanage/", "AppManage", "Software Licensing"),
            ("/HAVIS-360/paycheq/", "PayCheq", "Payroll"),
        ],
    )
    def test_havis_360_path_resolves_to_product(self, path, expected_product, expected_category):
        meta = product_metadata_for_url(f"https://ha-shem.com{path}")
        assert meta["product"] == expected_product
        assert meta["category"] == expected_category
        assert meta["source_type"] == "official_product"

    def test_havis_360_subpage_still_matches(self):
        meta = product_metadata_for_url("https://ha-shem.com/HAVIS-360/staas/pricing")
        assert meta["product"] == "STAAS"

    def test_path_matching_is_case_insensitive(self):
        meta = product_metadata_for_url("https://ha-shem.com/HAVIS-360/PayCheq/")
        assert meta["product"] == "PayCheq"

    def test_unrelated_ha_shem_page_still_returns_none(self):
        """Regression: general ha-shem.com content (not under a registered
        product path) must not be swept into a product's knowledge base."""
        meta = product_metadata_for_url("https://ha-shem.com/about")
        assert meta == {"product": None, "category": None, "source_type": None}

    def test_havis_360_root_without_product_slug_returns_none(self):
        meta = product_metadata_for_url("https://ha-shem.com/HAVIS-360/")
        assert meta["product"] is None

    def test_dedicated_domain_products_unaffected_by_path_logic(self):
        """SPIDIFY/ZivaAIRA still match on domain alone, any path."""
        assert product_metadata_for_url("https://havisspidify.com/anything")["product"] == "SPIDIFY"
        assert product_metadata_for_url("https://aira.havis360.com/anything")["product"] == "ZivaAIRA"
