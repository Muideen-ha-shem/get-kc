"""Crawl ZivaAIRA (https://aira.havis360.com/) into the crawled_pages table.

Reuses the same crawl configuration as crawl.py via crawl_site(). Run this,
then the existing test_clean.py -> chunk_runner.py -> upload_vectors.py
pipeline as usual (see PROJECT_STRUCTURE.md for the full multi-product
ingestion order) — product metadata is attached automatically at upload
time based on the URL's domain (see product_metadata.py).

NOT executed automatically — run manually: `python -m scripts.crawl_zivaaira`
"""

import asyncio

from scripts.crawl import crawl_site
from scripts.product_metadata import PRODUCT_SITES

if __name__ == "__main__":
    asyncio.run(crawl_site(PRODUCT_SITES["ZivaAIRA"]["url"]))
