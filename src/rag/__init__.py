"""
Rays RAG System
--------------
A RAG (Retrieval Augmented Generation) system for Tampa Bay Rays content.
Provides functionality for crawling the Rays website, processing content,
and creating a searchable knowledge base.
"""

__version__ = "0.1.0"

# Import main components that should be available when importing the package
from src.rag.crawl.crawler import RaysCrawler
from src.rag.processing.cleaner import ContentCleaner
from src.rag.processing.chunker import ContentChunker
from src.rag.storage.vectorstore import RaysVectorStore
from src.rag.utils.markdown_utils import MarkdownGenerator

# Define what gets imported with "from robo_ragmond import *"
__all__ = [
    'RaysCrawler',
    'ContentCleaner',
    'ContentChunker',
    'RaysVectorStore',
    'MarkdownGenerator',
] 