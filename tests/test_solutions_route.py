"""Tests for GET /solutions — reads directly from PRODUCT_REGISTRY, no
mocking needed since it's a pure in-process data transform (no I/O)."""

from __future__ import annotations

import pytest

from src.shared.product_registry import PRODUCT_REGISTRY


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    from src.api.app import app

    return TestClient(app)


class TestListSolutions:
    def test_returns_200(self, client):
        response = client.get("/solutions")
        assert response.status_code == 200

    def test_returns_one_entry_per_registry_product(self, client):
        response = client.get("/solutions")
        data = response.json()
        assert len(data) == len(PRODUCT_REGISTRY)
        assert {item["id"] for item in data} == set(PRODUCT_REGISTRY)

    def test_entry_shape_matches_registry_data(self, client):
        response = client.get("/solutions")
        data = response.json()
        by_id = {item["id"]: item for item in data}

        spidify = by_id["SPIDIFY"]
        assert spidify["name"] == "SPIDIFY"
        assert spidify["category"] == PRODUCT_REGISTRY["SPIDIFY"]["category"]
        assert spidify["business_problem"] == PRODUCT_REGISTRY["SPIDIFY"]["business_problem"]
        assert spidify["solution_type"] == PRODUCT_REGISTRY["SPIDIFY"]["solution_type"]
        assert spidify["learn_more_url"] == PRODUCT_REGISTRY["SPIDIFY"]["url"]

    def test_never_exposes_retrieval_internal_fields(self, client):
        """path_prefix/domain/aliases/keywords are retrieval implementation
        details — the public catalog endpoint must not leak them."""
        response = client.get("/solutions")
        data = response.json()
        for item in data:
            assert "path_prefix" not in item
            assert "domain" not in item
            assert "aliases" not in item
            assert "keywords" not in item

    def test_includes_havis_360_products(self, client):
        response = client.get("/solutions")
        ids = {item["id"] for item in client.get("/solutions").json()}
        for product in ["V-Login", "STAAS", "WeCare", "PayCheq", "AppManage"]:
            assert product in ids

    def test_get_only(self, client):
        response = client.post("/solutions")
        assert response.status_code == 405
