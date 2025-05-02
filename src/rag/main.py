"""
Main entry point for the RAG system.
Orchestrates the crawling, processing, and storage of content.
"""

import asyncio
from typing import Dict, List

from src.rag.crawl import RaysCrawler
from src.rag.processing import ContentCleaner, ContentChunker
from src.rag.storage import RaysVectorStore
from src.rag.utils import MarkdownGenerator

# Configuration
CHROMA_DB_DIR = "./chroma_db"
COLLECTION_NAME = "rays_website_content"
CONTENT_DIR = "./content"
OUTPUT_FILE = "rays_content_raw.md"

# URLs to crawl
URLS = [
    "https://www.mlb.com/rays/ballpark/gms-field/a-z-guide",
    "https://www.mlb.com/rays/tickets/specials/rays-rush",
    "https://www.mlb.com/rays/tickets/specials/salute-to-service",
    "https://www.mlb.com/rays/tickets/specials/student-ticket-offers",
    "https://www.mlb.com/rays/tickets/season-tickets/season-membership",
    "https://www.mlb.com/rays/tickets/single-game-tickets",
    "https://www.mlb.com/rays/tickets/premium/suites",
    "https://www.mlb.com/rays/gaming"
]

# Test queries
TEST_QUERIES = [
    "Can I bring a broom to the stadium?",
    "Who do the Rays play May 7th",
    "Where can I find information about season tickets?",
    "What food options are available?",
    "Are there any student discounts?"
]

SIMILARITY_TEST_PAIRS = [
    ("How much are tickets?", "Where can I park?"),
    ("Where can I park?", "Can I bring a broom to the stadium?"),
    ("Food at the stadium", "What concessions are available?")
]

async def main():
    """Main execution function."""
    print("\n=== Starting Rays Content Collection System ===\n")
    
    # Initialize components
    crawler = RaysCrawler()
    cleaner = ContentCleaner()
    chunker = ContentChunker()
    vector_store = RaysVectorStore(
        persist_dir=CHROMA_DB_DIR,
        collection_name=COLLECTION_NAME
    )
    md_gen = MarkdownGenerator(content_dir=CONTENT_DIR)
    
    # Step 1: Crawl content
    print("Crawling URLs...")
    url_content_map = await crawler.crawl_urls(URLS)
    
    if not url_content_map:
        print("No content was crawled. Exiting.")
        return
    
    # Step 2: Save raw content to markdown
    print("\nSaving raw content to markdown...")
    md_gen.save_content_to_markdown(
        url_content_map=url_content_map,
        output_file=OUTPUT_FILE,
        title="Tampa Bay Rays Website Content"
    )
    
    # Step 3: Process and store content
    print("\nProcessing and storing content...")
    for url, content in url_content_map.items():
        # Clean content
        cleaned_content = cleaner.clean_content(content)
        if not cleaned_content:
            print(f"Warning: Cleaning failed for {url}")
            continue
        
        # Create chunks with metadata
        chunks = chunker.process_content(cleaned_content, url)
        
        # Prepare data for vector store
        texts = [chunk["text"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]
        ids = [f"{url}_{i}" for i in range(len(chunks))]
        
        # Store in vector database
        vector_store.add_documents(
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
    
    # Step 4: Test queries
    print("\n=== Testing Queries ===")
    for query in TEST_QUERIES:
        results = vector_store.query([query])
        # Format and display results
        print(md_gen.format_query_results(query, results))
    
    # Step 5: Test semantic similarity
    print("\n=== Testing Semantic Similarity ===")
    similarity_results = vector_store.test_semantic_similarity(SIMILARITY_TEST_PAIRS)
    
    for result in similarity_results:
        print(f"\nComparing:")
        print(f"  Query 1: {result['query1']}")
        print(f"  Query 2: {result['query2']}")
        print(f"  Similarity Score: {result['similarity_score']:.2f}")
    
    print("\n=== Content Collection Complete ===")

if __name__ == "__main__":
    asyncio.run(main()) 