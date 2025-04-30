"""
Crawl4AI to ChromaDB Integration
This script:
1. Crawls multiple URLs from the Rays MLB website
2. Cleans and processes the content
3. Stores the content in ChromaDB vector store
4. Provides retrieval capabilities
"""

# --- Imports ---
import asyncio
import re
from datetime import datetime
from typing import Optional
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

# Import Crawl4AI components
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

# --- Configuration ---
CHROMA_DB_DIR = "./chroma_db"  # Where to store the ChromaDB database
COLLECTION_NAME = "rays_website_content"

# --- Core Functions ---
def initialize_chromadb():
    """
    Initialize ChromaDB client and collection.
    Returns the client and collection objects.
    """
    # Initialize the client with persistence
    client = chromadb.PersistentClient(path=CHROMA_DB_DIR)  # Changed to PersistentClient
    
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_functions.DefaultEmbeddingFunction()
    )
    
    return client, collection

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
            content = getattr(result.markdown, 'fit_markdown', result.markdown)
            if not content or len(content.strip()) == 0:
                print(f"!!! Warning: Crawled content for {url} is empty after filtering.")
                return None
    except Exception as e:
        print(f"!!! An error occurred during crawling for {url}. Error: {str(e)}")
        return None
    print(f"--- Crawl Complete for: {url} ---")
    return content

# --- Helper Functions ---
def clean_content(content: str) -> str:
    """
    Clean and normalize the crawled content before chunking.
    """
    # Remove HTML tags
    content = re.sub(r'<[^>]+>', '', content)
    
    # Normalize line breaks
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    
    # Remove multiple consecutive newlines but preserve paragraph structure
    content = re.sub(r'\n\s*\n', '\n\n', content)
    
    # Remove any special characters that might cause issues
    content = re.sub(r'[^\w\s.,!?\-\n]', '', content)
    
    # Trim whitespace from start and end
    content = content.strip()
    
    return content

def process_content_for_chromadb(content: str, url: str) -> list:
    """
    Process crawled content into chunks suitable for ChromaDB.
    Returns a list of dictionaries with text and metadata.
    """
    # First clean the content
    cleaned_content = clean_content(content)
    
    # Split content into paragraphs
    paragraphs = cleaned_content.split('\n\n')
    chunks = []
    current_chunk = ""
    max_chunk_size = 1000  # Maximum characters per chunk
    overlap_size = 200     # Number of characters to overlap between chunks
    
    for paragraph in paragraphs:
        # If adding this paragraph would exceed chunk size
        if len(current_chunk) + len(paragraph) > max_chunk_size:
            if current_chunk:  # Don't add empty chunks
                chunks.append(current_chunk.strip())
                
                # Start new chunk with overlap from previous chunk
                if len(current_chunk) > overlap_size:
                    current_chunk = current_chunk[-overlap_size:] + "\n\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                current_chunk = paragraph
        else:
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph
    
    # Add the last chunk if it exists
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    # Create structured data for ChromaDB
    processed_chunks = []
    for i, chunk in enumerate(chunks):
        processed_chunks.append({
            "text": chunk,
            "metadata": {
                "source_url": url,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "timestamp": datetime.now().isoformat(),
                "chunk_size": len(chunk),
                "chunk_type": "content"
            }
        })
    
    return processed_chunks

def test_chromadb_retrieval():
    """
    Test retrieving content from ChromaDB to verify storage.
    """
    client, collection = initialize_chromadb()
    
    print("\n=== ChromaDB Collection Info ===")
    print(f"Collection name: {collection.name}")
    print(f"Number of items: {collection.count()}")
    
    print("\n=== Testing Retrieval ===")
    results = collection.query(
        query_texts=["What are the ticket specials?"],
        n_results=3
    )
    
    print("\nQuery Results:")
    for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
        print(f"\nResult {i+1}:")
        print(f"Source URL: {metadata['source_url']}")
        print(f"Content preview: {doc[:200]}...")

# --- Main Execution ---
async def main():
    """Main function to crawl URLs and store in ChromaDB."""
    print("======= Starting Rays Website Content Collection =======")

    # Initialize ChromaDB
    client, collection = initialize_chromadb()

    # Define URLs to crawl
    urls_to_crawl = [
        "https://www.mlb.com/rays/ballpark/gms-field/a-z-guide",
        "https://www.mlb.com/rays/tickets/specials/rays-rush",
        "https://www.mlb.com/rays/tickets/specials/salute-to-service",
        "https://www.mlb.com/rays/tickets/specials/student-ticket-offers",
        "https://www.mlb.com/rays/tickets/season-tickets/season-membership",
        "https://www.mlb.com/rays/tickets/single-game-tickets",
        "https://www.mlb.com/rays/tickets/premium/suites",
        "https://www.mlb.com/rays/gaming"
    ]
    
    print("Starting content collection and storage process...")
    
    # Process each URL
    for url in urls_to_crawl:
        print(f"\nProcessing URL: {url}")
        
        # Get content using existing crawl function
        content = await crawl_and_get_content(url)
        
        if content:
            # Process content into chunks
            chunks = process_content_for_chromadb(content, url)
            
            # Prepare data for ChromaDB
            texts = [chunk["text"] for chunk in chunks]
            metadatas = [chunk["metadata"] for chunk in chunks]
            ids = [f"{url}_{i}" for i in range(len(chunks))]
            
            # Add to ChromaDB
            collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            print(f"Successfully stored {len(chunks)} chunks from {url}")
        else:
            print(f"Failed to process content from {url}")
    
    print("\nContent collection and storage complete!")

if __name__ == "__main__":
    # Run the main collection process
    asyncio.run(main())
    
    # Test the retrieval
    test_chromadb_retrieval()
