# Import Crawl4AI components
import asyncio
from typing import Optional
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator


async def crawl_and_get_content(url: str) -> Optional[str]:
    """Crawl a URL and return the full markdown content as a string."""
    print(f"\n--- Starting Crawl for: {url} ---")
    content = None
    try:
        browser_config = BrowserConfig(headless=True)
        markdown_generator = DefaultMarkdownGenerator(content_filter=PruningContentFilter())
        crawler_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            markdown_generator=markdown_generator
        )
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=url, config=crawler_config)
            if not result or not result.success:
                print(f"!!! Crawling failed for {url}. Error: {result.error_message if result else 'Unknown error'}")
                return None
            print("Crawling successful.")
            
            # Debug the raw result
            print("\nDebug - Raw Result:")
            print(f"Result type: {type(result)}")
            print(f"Markdown type: {type(result.markdown)}")
            
            content = getattr(result.markdown, 'fit_markdown', result.markdown)
            
            # Debug the processed content
            print("\nDebug - Content Info:")
            print(f"Content type: {type(content)}")
            print(f"Content length: {len(content) if content else 0} characters")
            
            if not content or len(content.strip()) == 0:
                print(f"!!! Warning: Crawled content for {url} is empty after filtering.")
                return None
            
    except Exception as e:
        print(f"!!! An error occurred during crawling for {url}. Error: {str(e)}")
        return None
    print(f"--- Crawl Complete for: {url} ---")
    return content


if __name__ == "__main__":
    print("Starting crawler script...")
    url = "https://mlb.com/rays/community"
    print(f"Attempting to crawl: {url}")
    content = asyncio.run(crawl_and_get_content(url))
    
    if content:
        print("\nCrawled Content:")
        print("=" * 80)  # This is just a separator line, not a content limit
        
        # Print content details
        print(f"\nContent Statistics:")
        print(f"Total characters: {len(content)}")
        print(f"Total lines: {len(content.splitlines())}")
        print(f"Total words: {len(content.split())}")
        
        # Print the full content
        print("\nFull Markdown Content Below:")
        print("=" * 80)
        print(content)  # This will print ALL content
        print("=" * 80)
        
        # Save to file with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'crawled_content_{timestamp}.md'
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\nContent has been saved to '{filename}' for easier viewing.")
    else:
        print("No content was retrieved.")