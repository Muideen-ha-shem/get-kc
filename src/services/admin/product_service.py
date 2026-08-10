"""ProductService — per-workspace product enable/disable (Phase 26).

Validates product_id against PRODUCT_REGISTRY.keys() — read-only import,
PRODUCT_REGISTRY itself is never modified. Admin metadata only; does not
change what the live RAG/retrieval pipeline actually returns.
"""

from __future__ import annotations

from ...shared.product_registry import PRODUCT_REGISTRY
from .admin_models import WorkspaceProductFlag
from .product_repository import ProductRepository


class ProductService:
    def __init__(self, repository: ProductRepository | None = None) -> None:
        self._repo = repository or ProductRepository()

    def list_for_workspace(self, workspace_id: str) -> list[WorkspaceProductFlag]:
        return self._repo.list_for_workspace(workspace_id)

    def set_enabled(self, workspace_id: str, product_id: str, enabled: bool) -> WorkspaceProductFlag:
        if product_id not in PRODUCT_REGISTRY:
            raise ValueError(f"Unknown product_id: {product_id}")
        return self._repo.set_enabled(workspace_id, product_id, enabled)
