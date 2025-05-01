import asyncio
from test_cleaning import crawl_and_get_content, clean_content

async def test_scrape_and_clean(url): 
    print(f"Testing crawl for: {url}")
    raw_content = await crawl_and_get_content(url)
    if raw_content: 
        print("\n--- Raw Crawled Content (first 7000 chars) ---")
        print(raw_content[:])
        cleaned = clean_content(raw_content)
        print("\n--- Cleaned Content (first 500 chars) ---")
        print(cleaned[:7000])
    else: 
        print("No content returned from crawler")

if __name__ == "__main__":
    url = "https://www.mlb.com/rays/tickets/single-game-tickets"
    asyncio.run(test_scrape_and_clean(url))