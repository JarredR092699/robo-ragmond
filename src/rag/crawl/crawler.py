"""
Crawler module for the RAG system.
Handles website crawling and content extraction using Crawl4AI.
"""

import asyncio
from typing import Optional, Dict
from datetime import datetime

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

class RaysCrawler:
    """Crawler class for Tampa Bay Rays website content."""
    
    def __init__(self, headless: bool = True, cache_mode: CacheMode = CacheMode.BYPASS):
        """
        Initialize the crawler with configuration.
        
        Args:
            headless: Whether to run browser in headless mode
            cache_mode: Cache mode for crawler (BYPASS, READ_ONLY, READ_WRITE)
        """
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
                    
                print("Crawling successful.")
                content = getattr(result.markdown, 'fit_markdown', result.markdown)
                
                if not content or len(content.strip()) == 0:
                    print(f"!!! Warning: Crawled content for {url} is empty after filtering.")
                    return None
                    
        except Exception as e:
            print(f"!!! An error occurred during crawling for {url}. Error: {str(e)}")
            return None
            
        print(f"--- Crawl Complete for: {url} ---")
        return content
    
    async def crawl_urls(self, urls: list[str]) -> Dict[str, str]:
        """
        Crawl multiple URLs and return a mapping of URLs to their content.
        
        Args:
            urls: List of URLs to crawl
            
        Returns:
            Dict[str, str]: Mapping of URLs to their content
        """
        url_content_map = {}
        
        for url in urls:
            content = await self.crawl_url(url)
            if content:
                url_content_map[url] = content
                
        return url_content_map

async def crawl_rays_content(urls: list[str]) -> Dict[str, str]:
    """
    Convenience function to crawl Rays website content.
    
    Args:
        urls: List of URLs to crawl
        
    Returns:
        Dict[str, str]: Mapping of URLs to their content
    """
    crawler = RaysCrawler()
    return await crawler.crawl_urls(urls)
