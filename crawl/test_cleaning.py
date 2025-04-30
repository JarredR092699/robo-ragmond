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
from chromadb import errors as chromadb_errors
from sentence_transformers import SentenceTransformer
import torch

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
    client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    
    # Initialize the BGE embedding model
    bge_embedding = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="BAAI/bge-large-en-v1.5",
        device="cuda" if torch.cuda.is_available() else "cpu"  # Use GPU if available
    )
    
    collection_name = f"{COLLECTION_NAME}_bge"  # Add suffix to differentiate from default embeddings
    
    try:
        # Try to get existing collection
        collection = client.get_collection(
            name=collection_name,
            embedding_function=bge_embedding
        )
        print(f"Using existing collection: {collection_name}")
        
    except (ValueError, chromadb.errors.NotFoundError) as e:
        # Create new collection if it doesn't exist
        print(f"Creating new collection: {collection_name}")
        try:
            collection = client.create_collection(
                name=collection_name,
                embedding_function=bge_embedding,
                metadata={"hnsw:space": "cosine"}  # Use cosine similarity for better matching
            )
        except ValueError as e:
            # Handle case where collection exists but with different embedding
            if "Embedding function name mismatch" in str(e):
                print("Warning: Found existing collection with different embedding function")
                print("Options:")
                print("1. Delete existing collection and create new one")
                print("2. Create new collection with different name")
                choice = input("Enter choice (1 or 2): ")
                
                if choice == "1":
                    print(f"Deleting existing collection: {collection_name}")
                    client.delete_collection(collection_name)
                    collection = client.create_collection(
                        name=collection_name,
                        embedding_function=bge_embedding,
                        metadata={"hnsw:space": "cosine"}
                    )
                else:
                    new_name = f"{collection_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    print(f"Creating new collection: {new_name}")
                    collection = client.create_collection(
                        name=new_name,
                        embedding_function=bge_embedding,
                        metadata={"hnsw:space": "cosine"}
                    )
            else:
                raise e
    
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
    Implements more sophisticated cleaning strategies for better embedding quality.
    """
    # Remove HTML tags and decode HTML entities
    content = re.sub(r'<[^>]+>', '', content)
    content = re.sub(r'&[a-zA-Z]+;', ' ', content)  # Replace HTML entities with space
    
    # Normalize whitespace
    content = re.sub(r'\s+', ' ', content)
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    
    # Remove multiple consecutive newlines but preserve paragraph structure
    content = re.sub(r'\n\s*\n', '\n\n', content)
    
    # Remove URLs but keep their text description if available
    content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)  # Markdown links
    content = re.sub(r'http[s]?://\S+', '', content)  # Plain URLs
    
    # Normalize quotes and apostrophes
    content = content.replace('"', '"').replace('"', '"')
    content = content.replace("'", "'").replace("'", "'")
    
    # Remove excessive punctuation but preserve sentence structure
    content = re.sub(r'([!?.]){2,}', r'\1', content)  # Convert multiple !!! or ??? to single
    content = re.sub(r'[-_]{2,}', '—', content)  # Convert multiple dashes to em-dash
    
    # Fix common spacing issues
    content = re.sub(r'\s+([.,!?])', r'\1', content)  # Remove space before punctuation
    content = re.sub(r'([.,!?])([^\s])', r'\1 \2', content)  # Add space after punctuation
    
    # Remove non-breaking spaces and other special whitespace
    content = content.replace('\xa0', ' ')
    
    # Trim whitespace from start and end of each line and the entire text
    content = '\n'.join(line.strip() for line in content.split('\n'))
    content = content.strip()
    
    return content

def process_content_for_chromadb(content: str, url: str) -> list:
    """
    Process crawled content into chunks suitable for ChromaDB.
    Returns a list of dictionaries with text and metadata.
    """
    # First clean the content
    cleaned_content = clean_content(content)
    
    # Split content into semantic chunks using multiple delimiters
    chunks = []
    current_chunk = ""
    max_chunk_size = 512  # Reduced for better semantic coherence
    min_chunk_size = 100  # Minimum size to avoid tiny chunks
    overlap_size = 50     # Reduced overlap to minimize redundancy
    
    # Split by headers first
    header_splits = re.split(r'(?:\r?\n|^)(#+\s|[A-Z][A-Z\s]+:)', cleaned_content)
    
    for split in header_splits:
        if not split.strip():
            continue
            
        # Further split by paragraphs if the section is too large
        paragraphs = split.split('\n\n')
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
                
            # If adding this paragraph would exceed chunk size
            if len(current_chunk) + len(paragraph) > max_chunk_size:
                if len(current_chunk) >= min_chunk_size:
                    chunks.append(current_chunk.strip())
                
                # Start new chunk with overlap from previous chunk
                if len(current_chunk) > overlap_size:
                    current_chunk = current_chunk[-overlap_size:] + "\n\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
    
    # Add the last chunk if it exists and meets minimum size
    if current_chunk and len(current_chunk) >= min_chunk_size:
        chunks.append(current_chunk.strip())
    
    # Create structured data for ChromaDB with enhanced metadata
    processed_chunks = []
    for i, chunk in enumerate(chunks):
        # Calculate chunk quality metrics
        sentences = len(re.split(r'[.!?]+', chunk))
        words = len(chunk.split())
        
        processed_chunks.append({
            "text": chunk,
            "metadata": {
                "source_url": url,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "timestamp": datetime.now().isoformat(),
                "chunk_size": len(chunk),
                "chunk_type": "content",
                "sentence_count": sentences,
                "word_count": words,
                "avg_sentence_length": words/sentences if sentences > 0 else 0
            }
        })
    
    return processed_chunks

def test_chromadb_retrieval():
    """
    Test retrieving content from ChromaDB to verify storage and embedding quality.
    Implements more sophisticated testing and evaluation metrics.
    """
    client, collection = initialize_chromadb()
    
    print("\n=== ChromaDB Collection Info ===")
    print(f"Collection name: {collection.name}")
    print(f"Number of items: {collection.count()}")
    
    # Test queries with different types of questions
    test_queries = [
        "What are the ticket specials?",
        "Tell me about parking at the stadium",
        "Where can I find information about season tickets?",
        "What food options are available?",
        "Are there any student discounts?"
    ]
    
    print("\n=== Testing Multiple Queries ===")
    for query in test_queries:
        print(f"\nQuery: {query}")
        results = collection.query(
            query_texts=[query],
            n_results=3,
            include=['documents', 'metadatas', 'distances']
        )
        
        # Process and display results with relevance scores
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0], 
            results['metadatas'][0], 
            results['distances'][0]
        )):
            relevance_score = 1 - (distance / 2)  # Convert distance to similarity score
            print(f"\nResult {i+1} (Relevance: {relevance_score:.2f}):")
            print(f"Source URL: {metadata['source_url']}")
            print(f"Chunk Stats: {metadata['word_count']} words, "
                  f"{metadata['sentence_count']} sentences")
            print(f"Content preview: {doc[:200]}...")
    
    # Test semantic similarity
    print("\n=== Testing Semantic Similarity ===")
    similar_queries = [
        ("How much are tickets?", "What is the ticket pricing?"),
        ("Where can I park?", "What are the parking options?"),
        ("Food at the stadium", "What concessions are available?")
    ]
    
    for query1, query2 in similar_queries:
        results1 = collection.query(
            query_texts=[query1],
            n_results=1,
            include=['documents', 'distances']
        )
        results2 = collection.query(
            query_texts=[query2],
            n_results=1,
            include=['documents', 'distances']
        )
        
        print(f"\nTesting semantic similarity between:")
        print(f"Query 1: {query1}")
        print(f"Query 2: {query2}")
        print(f"Distance between results: {abs(results1['distances'][0][0] - results2['distances'][0][0]):.4f}")

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
        
        try:
            # Get content using existing crawl function
            content = await crawl_and_get_content(url)
            
            if content:
                # Process content into chunks
                chunks = process_content_for_chromadb(content, url)
                
                if not chunks:
                    print(f"Warning: No valid chunks generated for {url}")
                    continue
                
                # Prepare data for ChromaDB
                texts = [chunk["text"] for chunk in chunks]
                metadatas = [chunk["metadata"] for chunk in chunks]
                ids = [f"{url}_{i}" for i in range(len(chunks))]
                
                # Verify we have valid data before adding to ChromaDB
                if texts and metadatas and ids and len(texts) == len(metadatas) == len(ids):
                    # Add to ChromaDB
                    collection.add(
                        documents=texts,
                        metadatas=metadatas,
                        ids=ids
                    )
                    print(f"Successfully stored {len(chunks)} chunks from {url}")
                else:
                    print(f"Warning: Invalid data generated for {url}")
                    print(f"Texts: {len(texts)}, Metadatas: {len(metadatas)}, IDs: {len(ids)}")
            else:
                print(f"Warning: No content retrieved from {url}")
                
        except Exception as e:
            print(f"Error processing {url}: {str(e)}")
            continue
    
    print("\nContent collection and storage complete!")
    
    # Test the retrieval
    test_chromadb_retrieval()

if __name__ == "__main__":
    # Run the main collection process
    asyncio.run(main())
