"""product_metadata — maps a crawled URL to its product metadata.

The existing crawl -> clean -> chunk -> upload pipeline (crawl.py,
intensive_cleaner, chunk.py, upload_vectors.py) is keyed purely by URL, with
no separate "which crawl run does this belong to" concept. Rather than
restructure that pipeline, product identity is derived from the URL at
upload time — this needs no schema changes to the intermediate
crawled_pages table or cleaned_output/ directory, and works for any URL
regardless of when or how it was crawled.

Product data itself now lives in ``src.shared.product_registry`` (the single
source of truth shared with ``ProductRouter``); this module just re-exposes
the URL/domain/category subset of it for backward compatibility with
existing callers (``crawl_spidify.py``, ``crawl_zivaaira.py``,
``upload_vectors.py``) and adds URL -> product resolution on top, including
path-prefix matching for products that share a domain (the HAVIS-360
catalog, all under ha-shem.com) rather than owning their own domain
(SPIDIFY, ZivaAIRA).
"""

from __future__ import annotations

from typing import TypedDict
from urllib.parse import urlparse

from src.shared.product_registry import PRODUCT_REGISTRY


class ProductMetadata(TypedDict):
    product: str | None
    category: str | None
    source_type: str | None


# Backward-compatible view of the registry — just the fields callers here
# have always used. Derived, not hand-maintained, so it can never drift out
# of sync with PRODUCT_REGISTRY.
PRODUCT_SITES: dict[str, dict[str, str]] = {
    name: {"url": info["url"], "domain": info["domain"], "category": info["category"]}
    for name, info in PRODUCT_REGISTRY.items()
}

# Domain -> product, for products that own their whole domain
# (path_prefix is None).
_DOMAIN_TO_PRODUCT: dict[str, str] = {
    info["domain"]: name for name, info in PRODUCT_REGISTRY.items() if info["path_prefix"] is None
}

# Domain -> [(path_prefix, product), ...], for products that share a domain
# and are distinguished by URL path instead.
_PATH_PREFIXES_BY_DOMAIN: dict[str, list[tuple[str, str]]] = {}
for _name, _info in PRODUCT_REGISTRY.items():
    if _info["path_prefix"] is not None:
        _PATH_PREFIXES_BY_DOMAIN.setdefault(_info["domain"], []).append((_info["path_prefix"], _name))


def product_metadata_for_url(url: str) -> ProductMetadata:
    """Return product metadata for *url*, or all-``None`` if it's not a
    recognised product (e.g. general ha-shem.com company content that isn't
    under a registered product's path).
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()
    except Exception:
        domain, path = "", ""
    if domain.startswith("www."):
        domain = domain[4:]

    product = _DOMAIN_TO_PRODUCT.get(domain)

    if product is None:
        for prefix, candidate in _PATH_PREFIXES_BY_DOMAIN.get(domain, []):
            if path.startswith(prefix):
                product = candidate
                break

    if product is None:
        return {"product": None, "category": None, "source_type": None}

    return {
        "product": product,
        "category": PRODUCT_REGISTRY[product]["category"],
        "source_type": "official_product",
    }
