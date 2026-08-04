"""Tests for ProductService (Phase 26) — validates product_id against
PRODUCT_REGISTRY, admin metadata only."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.services.admin.product_service import ProductService


class TestProductService:
    def test_set_enabled_rejects_unknown_product_id(self):
        repo = MagicMock()
        service = ProductService(repository=repo)

        with pytest.raises(ValueError, match="Unknown product_id"):
            service.set_enabled("w1", "NotAProduct", True)

        repo.set_enabled.assert_not_called()

    def test_set_enabled_accepts_known_product_id(self):
        repo = MagicMock()
        repo.set_enabled.return_value = MagicMock(product_id="SPIDIFY", enabled=True)
        service = ProductService(repository=repo)

        flag = service.set_enabled("w1", "SPIDIFY", True)

        assert flag.product_id == "SPIDIFY"
        repo.set_enabled.assert_called_once_with("w1", "SPIDIFY", True)

    def test_list_for_workspace_delegates(self):
        repo = MagicMock()
        repo.list_for_workspace.return_value = []
        service = ProductService(repository=repo)

        service.list_for_workspace("w1")

        repo.list_for_workspace.assert_called_once_with("w1")
