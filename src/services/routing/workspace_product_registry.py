"""Workspace -> product catalog lookup seam (Phase 22).

Only the Ha-Shem workspace has a real catalog today (the module-level
``PRODUCT_REGISTRY``) — any other workspace_id (or ``None``) also resolves
to it, since there is no second tenant yet. Phase 23 replaces the body of
this function with a real per-workspace lookup (DB-backed, or a dict keyed
by workspace id); every call site already goes through this seam, so that
phase touches only this one function — not ``ProductRouter``, ``SourceRouter``,
or ``BusinessIntentEngine``, none of which are modified by this seam.
"""

from __future__ import annotations

from ...shared.product_registry import PRODUCT_REGISTRY, ProductInfo


def get_product_registry(workspace_id: str | None = None) -> dict[str, ProductInfo]:
    return PRODUCT_REGISTRY
