import asyncio
import os
from dotenv import load_dotenv
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from src.sb import get_client
from supabase import PostgrestAPIError

load_dotenv()


async def main():
    url = "https://ha-shem.com/"

    browser_cfg = BrowserConfig(
        headless=False,
        user_agent_mode="random",
        text_mode=False,
    )

    run_cfg = CrawlerRunConfig(
        delay_before_return_html=2.0,
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
            max_depth=2,
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
            process_result(result)


def process_result(result):
    if result.success:
        result_json = result_dict(result)
        sb_client = get_client()

        try:
            table_name = os.getenv("SUPABASE_TABLE_NAME_PAGES", "crawled_pages")
            sb_client.table(table_name).insert(result_json).execute()
        except PostgrestAPIError as e:
            print(f"Error inserting into Supabase: {e}")
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
