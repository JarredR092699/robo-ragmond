"""
Configuration settings for the Rays RAG system.
Centralizes all configuration variables and provides environment variable handling.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base Paths
ROOT_DIR = Path(__file__).parent.parent.parent.parent  # Get to the project root
DATA_DIR = ROOT_DIR / "data"
CONTENT_DIR = ROOT_DIR / "content"
CHROMA_DB_DIR = ROOT_DIR / "chroma_db"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
CONTENT_DIR.mkdir(exist_ok=True)
CHROMA_DB_DIR.mkdir(exist_ok=True)

# File Paths
RAW_CONTENT_FILE = CONTENT_DIR / "rays_content_raw.md"

# ChromaDB Settings
COLLECTION_NAME = "rays_website_content"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_METADATA = {"hnsw:space": "cosine"}

# Content Processing Settings
MAX_CHUNK_SIZE = 512  # Maximum size for text chunks
MIN_CHUNK_SIZE = 100  # Minimum size to avoid tiny chunks
CHUNK_OVERLAP = 50    # Overlap between chunks

# Crawler Settings
URLS_TO_CRAWL = [
    "https://www.mlb.com/rays/ballpark/gms-field/a-z-guide",
    "https://www.mlb.com/rays/tickets/specials/rays-rush",
    "https://www.mlb.com/rays/tickets/specials/salute-to-service",
    "https://www.mlb.com/rays/tickets/specials/student-ticket-offers",
    "https://www.mlb.com/rays/tickets/season-tickets/season-membership",
    "https://www.mlb.com/rays/tickets/single-game-tickets",
    "https://www.mlb.com/rays/tickets/premium/suites",
    "https://www.mlb.com/rays/gaming"
]

# Test Queries for Evaluation
TEST_QUERIES = [
    "Can I bring a broom to the stadium?",
    "Who do the Rays play May 7th",
    "Where can I find information about season tickets?",
    "What food options are available?",
    "Are there any student discounts?"
]

SIMILARITY_TEST_PAIRS = [
    ("How much are tickets?", "What is the ticket pricing?"),
    ("Where can I park?", "What are the parking options?"),
    ("Food at the stadium", "What concessions are available?")
]

# Environment Variables (with defaults)
class EnvSettings:
    """Environment-specific settings with defaults"""
    DEBUG = os.getenv("RAYS_RAG_DEBUG", "false").lower() == "true"
    LOG_LEVEL = os.getenv("RAYS_RAG_LOG_LEVEL", "INFO")
    CACHE_MODE = os.getenv("RAYS_RAG_CACHE_MODE", "BYPASS")
    
    @classmethod
    def is_production(cls):
        """Check if we're running in production mode"""
        return os.getenv("RAYS_RAG_ENV", "development") == "production"

# Export settings as module-level variables
env = EnvSettings()