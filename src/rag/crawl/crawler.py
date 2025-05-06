# crawler.py
"""
Crawler module for the RAG system.
Handles website crawling and content extraction using Crawl4AI.
Saves the combined raw markdown content to the file specified in settings.py.
"""

import asyncio
from typing import Optional, Dict, List
from datetime import datetime
from pathlib import Path

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator


# --- Import settings from settings.py (using relative import) ---
try:
    # These variables MUST be defined in settings.py
    from .settings import URLS_TO_CRAWL, RAW_CONTENT_FILE # Note the leading dot
    print("--- Successfully imported variables from .settings in crawler.py ---") # Optional: Confirmation
except ImportError:
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print("!!! CRITICAL ERROR: Could not relatively import URLS_TO_CRAWL or RAW_CONTENT_FILE !!!")
    print("!!! from .settings. Please ensure settings.py exists in the same directory    !!!")
    print("!!! as crawler.py and defines these variables correctly.                      !!!")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    # Define empty fallbacks
    URLS_TO_CRAWL = []
    RAW_CONTENT_FILE = Path("error_settings_not_found.md")

# print("--- Attempting to import from settings.py directly in crawler.py ---") # Remove this line

# These prints will now use the correctly imported values or the fallbacks
print(f"--- Crawler initialized. Will crawl {len(URLS_TO_CRAWL)} URLs. ---")
print(f"--- Output will be written to: {RAW_CONTENT_FILE} ---")

# ... rest of crawler.py ...
class RaysCrawler:
    """Crawler class for Tampa Bay Rays website content."""

    # Consider getting cache_mode from settings: settings.env.CACHE_MODE
    def __init__(self, headless: bool = True, cache_mode_str: str = "BYPASS"):
        """
        Initialize the crawler with configuration.

        Args:
            headless: Whether to run browser in headless mode
            cache_mode_str: Cache mode string ('BYPASS', 'READ_ONLY', 'READ_WRITE')
        """
        try:
            # Convert cache mode string to Enum
            cache_mode = CacheMode[cache_mode_str.upper()]
        except KeyError:
            print(f"!!! Warning: Invalid CACHE_MODE '{cache_mode_str}'. Defaulting to BYPASS.")
            cache_mode = CacheMode.BYPASS

        self.browser_config = BrowserConfig(headless=headless)
        self.markdown_generator = DefaultMarkdownGenerator(
            content_filter=PruningContentFilter()
        )
        self.crawler_config = CrawlerRunConfig(
            cache_mode=cache_mode,
            markdown_generator=self.markdown_generator
        )

    async def crawl_url(self, url: str) -> Optional[str]:
        """
        Crawl a single URL and return the markdown content.

        Args:
            url: The URL to crawl

        Returns:
            Optional[str]: The markdown content if successful, None otherwise
        """
        print(f"\n--- Starting Crawl for: {url} ---")
        content = None
        try:
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                result = await crawler.arun(url=url, config=self.crawler_config)

                if not result or not result.success:
                    print(f"!!! Crawling failed for {url}. "
                          f"Error: {result.error_message if result else 'Unknown error'}")
                    return None

                print(f"    Crawling successful for {url}.")
                content = result.markdown # DefaultMarkdownGenerator returns a string

                if not content or len(content.strip()) == 0:
                    print(f"!!! Warning: Crawled content for {url} is empty after filtering.")
                    return None
        except Exception as e:
            import traceback
            print(f"!!! An unexpected error occurred during crawling for {url}. Error: {str(e)}")
            traceback.print_exc() # Print full traceback for debugging
            return None

        print(f"--- Crawl Complete for: {url} ---")
        return content

    async def crawl_urls(self, urls: List[str]) -> Dict[str, str]:
        """
        Crawl multiple URLs concurrently and return a mapping of URLs to their content.

        Args:
            urls: List of URLs to crawl

        Returns:
            Dict[str, str]: Mapping of URLs to their content
        """
        url_content_map = {}
        if not urls:
            return url_content_map

        print(f"\n=== Starting concurrent crawl for {len(urls)} URLs ===")
        tasks = [self.crawl_url(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True) # Capture exceptions too

        for i, url in enumerate(urls):
            result = results[i]
            if isinstance(result, Exception):
                print(f"!!! Task for {url} failed with exception: {result}")
            elif result: # Check if content is not None or empty string implicitly
                url_content_map[url] = result
            # No need for an else here, failed/empty crawls are already printed in crawl_url

        print(f"\n=== Finished crawling. Successfully retrieved content for {len(url_content_map)} out of {len(urls)} URLs ===")
        return url_content_map

async def get_rays_content_map(urls: List[str]) -> Dict[str, str]:
    """
    Convenience function to crawl Rays website content.

    Args:
        urls: List of URLs to crawl

    Returns:
        Dict[str, str]: Mapping of URLs to their content
    """
    # Consider getting cache mode from settings: settings.env.CACHE_MODE
    crawler = RaysCrawler()
    return await crawler.crawl_urls(urls)

async def main():
    """
    Main function to crawl URLs defined in settings and write the combined content
    to the markdown file specified in settings.
    """
    print("\n=== Running Main Execution Block ===")

    # URLS_TO_CRAWL is imported from settings at the top level
    if not URLS_TO_CRAWL:
        print("URLS_TO_CRAWL list in settings is empty. Nothing to crawl.")
        return

    # 1. Crawl the content
    content_map = await get_rays_content_map(URLS_TO_CRAWL)

    if not content_map:
        print("Crawling did not yield any content. Markdown file will not be updated.")
        return

    # 2. Write the collected content to the markdown file
    # RAW_CONTENT_FILE is imported from settings at the top level
    print(f"\n--- Attempting to write {len(content_map)} results to {RAW_CONTENT_FILE} ---")
    try:
        # Ensure the parent directory exists (settings.py already does this, but good practice)
        RAW_CONTENT_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Use 'w' mode to overwrite the file each time.
        with open(RAW_CONTENT_FILE, "w", encoding="utf-8") as f:
            f.write(f"# Raw Content Scraped on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"Scraped from {len(content_map)} URLs.\n\n")

            for url, content in content_map.items():
                f.write(f"---\n\n## Source: {url}\n\n") # Add a header for each URL
                f.write(content.strip()) # Write content, stripping leading/trailing whitespace
                f.write("\n\n") # Add space after content

        print(f"--- Successfully wrote content to {RAW_CONTENT_FILE} ---")
    except IOError as e:
        print(f"!!! Error writing to file {RAW_CONTENT_FILE}. Error: {e}")
    except Exception as e:
        import traceback
        print(f"!!! An unexpected error occurred during file writing. Error: {e}")
        traceback.print_exc()


# --- Entry point for running the script directly ---
if __name__ == "__main__":
    print("Crawler script starting execution...")
    if not URLS_TO_CRAWL:
        print("Variable 'URLS_TO_CRAWL' is empty or not imported correctly from settings.py. Cannot proceed.")
    else:
        # Run the main asynchronous function
        asyncio.run(main())
    print("Crawler script finished execution.")
