# import RaysCrawler
from src.rag.crawl.crawler import RaysCrawler
import asyncio

async def test_crawler():
    # create crawler instance 
    crawler = RaysCrawler()

    # crawl multiple urls 
    urls = [
        "https://www.mlb.com/rays/ballpark/gms-field/a-z-guide",
        "https://www.mlb.com/rays/community/education"
    ]

    # get content from all urls
    content_map = await crawler.crawl_urls(urls)
    
    # Print the results
    for url, content in content_map.items():
        print(f"\nURL: {url}")
        print(f"Content length: {len(content)} characters")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_crawler())

