"""
Storage package for the RAG system.
Provides functionality to store and retrieve content using vector databases.
"""

from .vectorstore import RaysVectorStore

__all__ = [
    'RaysVectorStore',
]
