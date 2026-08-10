import asyncio
import os
from typing import Callable, Optional

from dotenv import load_dotenv
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from src.sb import get_client
from supabase import PostgrestAPIError

load_dotenv()


async def main():
    await crawl_site("https://ha-shem.com/")


async def crawl_site(
    url: str,
    max_depth: int = 2,
    *,
    headless: bool = False,
    wait_until: str = "domcontentloaded",
    delay_before_return_html: float = 2.0,
    page_timeout: int = 60000,
    on_result: Optional[Callable[[dict], None]] = None,
):
    """Crawl *url* (BFS, up to *max_depth*) and store each page in Supabase.

    Extracted so other entry-point scripts (crawl_spidify.py,
    crawl_zivaaira.py) can reuse the exact same crawl configuration for a
    different target site, instead of duplicating it.

    Args:
        headless, wait_until, delay_before_return_html, page_timeout:
            All default to exactly what this function used before these
            parameters existed, so ``crawl_site(url)`` — what ``main()``
            below still calls — behaves identically to before. Product
            sites that are client-rendered SPAs (confirmed for both
            SPIDIFY and ZivaAIRA — ``domcontentloaded`` fires before their
            JS finishes rendering and returns near-empty markdown) need
            ``wait_until="load"`` and a longer delay; see crawl_spidify.py
            / crawl_zivaaira.py.
        on_result: Phase 27 — optional callback invoked once per
            successfully-crawled page (same dict shape as the row written
            to ``crawled_pages``), letting a caller ingest results
            in-process without polling the staging table. ``None`` (the
            default) preserves the exact prior behaviour for every
            existing caller — none of the 13 ``crawl_*.py`` scripts pass
            this argument.
    """
    browser_cfg = BrowserConfig(
        headless=headless,
        user_agent_mode="random",
        text_mode=False,
    )

    run_cfg = CrawlerRunConfig(
        wait_until=wait_until,
        delay_before_return_html=delay_before_return_html,
        page_timeout=page_timeout,
        js_code=None,
        excluded_tags=["script", "style", "form", "header", "footer", "nav"],
        excluded_selector="#nexer-navbar",
        only_text=True,
        remove_forms=True,
        exclude_social_media_links=True,
        exclude_external_links=True,
        remove_overlay_elements=True,
        simulate_user=False,
        override_navigator=False,
        verbose=True,
        cache_mode=CacheMode.DISABLED,
        stream=True,
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=max_depth,
            include_external=False,
        ),
    )

    async with AsyncWebCrawler(
        config=browser_cfg,
        verbose=True,
        debug=True,
        use_playwright=True,
        undetected_browser=True,
    ) as crawler:
        async for result in await crawler.arun(url=url, config=run_cfg):
            process_result(result, on_result=on_result)


def process_result(result, on_result: Optional[Callable[[dict], None]] = None):
    if result.success:
        result_json = result_dict(result)
        sb_client = get_client()

        try:
            table_name = os.getenv("SUPABASE_TABLE_NAME_PAGES", "crawled_pages")
            sb_client.table(table_name).insert(result_json).execute()
        except PostgrestAPIError as e:
            print(f"Error inserting into Supabase: {e}")

        if on_result is not None:
            on_result(result_json)
    else:
        print(f"Crawl failed: {result.error_message}")


def result_dict(result) -> dict:
    return {
        "url": result.url,
        "links": result.links,
        "metadata": result.metadata,
        "markdown": result.markdown,
        "html": result.html,
        "cleaned_html": result.cleaned_html,
    }


if __name__ == "__main__":
    asyncio.run(main())
