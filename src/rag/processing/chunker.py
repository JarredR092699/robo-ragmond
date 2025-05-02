"""
Content chunking module for the RAG system.
Provides functionality to split content into semantic chunks for vector storage.
"""

import re
from typing import List, Dict
from datetime import datetime

class ContentChunker:
    """Chunker class for splitting content into semantic chunks."""
    
    def __init__(
        self,
        max_chunk_size: int = 512,
        min_chunk_size: int = 100,
        overlap_size: int = 50
    ):
        """
        Initialize chunker with size parameters.
        
        Args:
            max_chunk_size: Maximum size for text chunks
            min_chunk_size: Minimum size to avoid tiny chunks
            overlap_size: Size of overlap between chunks
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap_size = overlap_size
    
    def split_by_headers(self, content: str) -> List[str]:
        """
        Split content by headers and header-like patterns.
        
        Args:
            content: Text content to split
            
        Returns:
            List[str]: Content split by headers
        """
        # Split by markdown headers and uppercase section headers
        splits = re.split(r'(?:\r?\n|^)(#+\s|[A-Z][A-Z\s]+:)', content)
        # Filter out empty splits and recombine headers with their content
        result = []
        for i in range(0, len(splits)-1, 2):
            header = splits[i:i+2][1] if i+1 < len(splits) else ''
            content = splits[i:i+2][0] if i < len(splits) else ''
            if header and content:
                result.append(f"{header}{content}")
            elif content:
                result.append(content)
        return [s.strip() for s in result if s.strip()]
    
    def create_chunks(self, content: str) -> List[str]:
        """
        Create chunks from content with overlap.
        
        Args:
            content: Text content to chunk
            
        Returns:
            List[str]: List of content chunks
        """
        chunks = []
        current_chunk = ""
        
        # First split by headers
        sections = self.split_by_headers(content)
        
        for section in sections:
            # Split section into paragraphs
            paragraphs = section.split('\n\n')
            
            for paragraph in paragraphs:
                if not paragraph.strip():
                    continue
                
                # If adding this paragraph would exceed max size
                if len(current_chunk) + len(paragraph) > self.max_chunk_size:
                    if len(current_chunk) >= self.min_chunk_size:
                        chunks.append(current_chunk.strip())
                    
                    # Start new chunk with overlap from previous chunk
                    if len(current_chunk) > self.overlap_size:
                        current_chunk = current_chunk[-self.overlap_size:] + "\n\n" + paragraph
                    else:
                        current_chunk = paragraph
                else:
                    if current_chunk:
                        current_chunk += "\n\n" + paragraph
                    else:
                        current_chunk = paragraph
        
        # Add the last chunk if it meets minimum size
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def process_content(self, content: str, url: str) -> List[Dict]:
        """
        Process content into chunks with metadata.
        
        Args:
            content: Text content to process
            url: Source URL of the content
            
        Returns:
            List[Dict]: List of chunks with metadata
        """
        chunks = self.create_chunks(content)
        
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
