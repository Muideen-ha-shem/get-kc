import asyncio

from crawl4ai import AsyncWebCrawler

from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode

from crawl4ai.deep_crawling import BFSDeepCrawlStrategy

from sb import get_client  # helper to get the Supabase client

from embed import embed_documents  # Function to embed crawled documents

from supabase import PostgrestAPIError

import os

from dotenv import load_dotenv

load_dotenv()



async def main():

    url = "https://ha-shem.com/"  # Target website for crawling



    # Configuration for the browser used in crawling

    browser_cfg = BrowserConfig(
        headless=True,
        # Use a real user profile string structure
        user_agent_mode="random", 
        text_mode=True,  # Extract only visible text (no images/media)

    )



    # Configuration for how the crawler should run

    run_cfg = CrawlerRunConfig(


        # Wait for the network to be completely idle for at least 500ms
        # Add an explicit extra buffer (in seconds) before data extraction starts
        delay_before_return_html=2.0,
        # Bypass heavy processing that might crash during load state transitions
        js_code=None,

        excluded_tags=["script", "style", "form", "header", "footer", "nav"],  # Remove unwanted HTML tags

        excluded_selector="#nexer-navbar",  # Skip specific page element by CSS selector

        only_text=True,  # Extract just the text

        remove_forms=True,  # Skip form elements

        exclude_social_media_links=True,  # Don't follow social links 

        exclude_external_links=True,  # Stay within the main domain

        remove_overlay_elements=True,  # Clean overlays/popups



        simulate_user=True,  # Behave like a real user (e.g., scrolling, clicking)

        override_navigator=True,  # Mask headless browser properties

        verbose=True,  # Output crawl logs

        cache_mode=CacheMode.DISABLED,  # Disable caching of visited pages

        stream=True,  # Stream results as they're found



        # Set up depth-limited crawling strategy (BFS = breadth-first search)

        deep_crawl_strategy=BFSDeepCrawlStrategy(

            max_depth=2,  # Crawl up to 2 levels deep from the starting page

            include_external=False,  # Stay within the same domain

            # max_pages=10  # Optional: limit number of pages, good for debugging

        ),

    )



    # Initialize the asynchronous crawler with Playwright

    async with AsyncWebCrawler(

        config=browser_cfg,

        verbose=True,

        debug=True,

        use_playwright=True,  # Use Playwright for browser automation
        undetected_browser=True, # Use advanced anti-bot techniques

    ) as crawler:



        # Crawl the site using provided run configuration

        async for result in await crawler.arun(

            url=url,

            config=run_cfg

        ):

            process_result(result)  # handles the crawl output (one result = one page)

...


# The function for processing the results from the crawler

# connects to supabase
# writes one row per page into the crawled_pages table
# calls embed_documents that chunks and embeds the text and writes to documents table , see later

# Entry point: runs the main crawler function in an asyncio event loop


def process_result(result):

    """

    Process the result returned from the crawler

    """

    if result.success:

        # Convert result object into a dictionary

        result_json = result_dict(result)



        # Initialize Supabase client

        sb_client = get_client()



        try:

            # Insert the crawled data into Supabase

            table_name = os.getenv("SUPABASE_TABLE_NAME_PAGES", "crawled_pages")



            sb_client.table(table_name).insert(result_json).execute()

        except PostgrestAPIError as e:

            print(f"Error inserting into Supabase: {e}")

        

        try:
            # Generate embeddings for the document and store them using the Supabase client
            embed_documents(result_json, sb_client)
        except Exception as e:
            print(f"Error embedding documents: {e}")



        print("Data inserted and embedded successfully.")

    

    else:

        # Log any crawl failure along with the error message

        print(f"Crawl failed: {result.error_message}")



def result_dict(result) -> dict:

    """

    convert the result object into a dictionary

    """

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