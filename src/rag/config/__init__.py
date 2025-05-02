"""
Configuration package for the Rays RAG system.
Provides easy access to all configuration settings.
"""

from .settings import (
    # Path settings
    ROOT_DIR,
    DATA_DIR,
    CONTENT_DIR,
    CHROMA_DB_DIR,
    RAW_CONTENT_FILE,
    
    # ChromaDB settings
    COLLECTION_NAME,
    EMBEDDING_MODEL_NAME,
    COLLECTION_METADATA,
    
    # Content processing settings
    MAX_CHUNK_SIZE,
    MIN_CHUNK_SIZE,
    CHUNK_OVERLAP,
    
    # Crawler settings
    URLS_TO_CRAWL,
    
    # Test settings
    TEST_QUERIES,
    SIMILARITY_TEST_PAIRS,
    
    # Environment settings
    env,
)

__all__ = [
    # Path settings
    'ROOT_DIR',
    'DATA_DIR',
    'CONTENT_DIR',
    'CHROMA_DB_DIR',
    'RAW_CONTENT_FILE',
    
    # ChromaDB settings
    'COLLECTION_NAME',
    'EMBEDDING_MODEL_NAME',
    'COLLECTION_METADATA',
    
    # Content processing settings
    'MAX_CHUNK_SIZE',
    'MIN_CHUNK_SIZE',
    'CHUNK_OVERLAP',
    
    # Crawler settings
    'URLS_TO_CRAWL',
    
    # Test settings
    'TEST_QUERIES',
    'SIMILARITY_TEST_PAIRS',
    
    # Environment settings
    'env',
] 