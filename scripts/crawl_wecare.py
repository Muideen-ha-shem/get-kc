"""Crawl WeCare (https://ha-shem.com/HAVIS-360/wecare/) into the
crawled_pages table.

Reuses the same crawl configuration as crawl.py via crawl_site(). Unlike
SPIDIFY/ZivaAIRA — dedicated multi-page product sites on their own domain —
WeCare is a single product page on the main ha-shem.com site, so this
crawls only that page (``max_depth=0``, no link-following) rather than
deep-crawling. Product metadata is attached automatically at upload time
based on the URL's domain + path (see product_metadata.py /
src.shared.product_registry).

NOT executed automatically — run manually: `python -m scripts.crawl_wecare`
"""

import asyncio

from scripts.crawl import crawl_site
from scripts.product_metadata import PRODUCT_SITES

if __name__ == "__main__":
    asyncio.run(
        crawl_site(
            PRODUCT_SITES["WeCare"]["url"],
            max_depth=0,
            headless=True,
        )
    )
