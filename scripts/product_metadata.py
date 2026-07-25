"""product_metadata — maps a crawled URL to its product metadata.

The existing crawl -> clean -> chunk -> upload pipeline (crawl.py,
intensive_cleaner, chunk.py, upload_vectors.py) is keyed purely by URL, with
no separate "which crawl run does this belong to" concept. Rather than
restructure that pipeline, product identity is derived from the URL's
domain at upload time — SPIDIFY and ZivaAIRA each live on their own domain,
so this needs no schema changes to the intermediate crawled_pages table or
cleaned_output/ directory, and works for any URL from either site
regardless of when or how it was crawled.
"""

from __future__ import annotations

from typing import TypedDict
from urllib.parse import urlparse


class ProductMetadata(TypedDict):
    product: str | None
    category: str | None
    source_type: str | None


# Single source of truth for which domain maps to which product — also used
# by scripts/crawl_spidify.py and scripts/crawl_zivaaira.py for the crawl
# target URL itself.
PRODUCT_SITES: dict[str, dict[str, str]] = {
    "SPIDIFY": {
        "url": "https://havisspidify.com/",
        "domain": "havisspidify.com",
        "category": "Identity Verification",
    },
    "ZivaAIRA": {
        "url": "https://aira.havis360.com/",
        "domain": "aira.havis360.com",
        "category": "HR Recruitment",
    },
}

_DOMAIN_TO_PRODUCT: dict[str, str] = {
    info["domain"]: name for name, info in PRODUCT_SITES.items()
}


def product_metadata_for_url(url: str) -> ProductMetadata:
    """Return product metadata for *url*, or all-``None`` if it's not a
    recognised product domain (e.g. general ha-shem.com company content).
    """
    try:
        domain = urlparse(url).netloc.lower()
    except Exception:
        domain = ""
    if domain.startswith("www."):
        domain = domain[4:]

    product = _DOMAIN_TO_PRODUCT.get(domain)
    if product is None:
        return {"product": None, "category": None, "source_type": None}

    return {
        "product": product,
        "category": PRODUCT_SITES[product]["category"],
        "source_type": "official_product",
    }
