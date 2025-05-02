"""
Content cleaning module for the RAG system.
Provides functionality to clean and normalize crawled content.
"""

import re
from typing import Optional

class ContentCleaner:
    """Cleaner class for processing raw content."""
    
    @staticmethod
    def clean_html(content: str) -> str:
        """
        Remove HTML tags and entities from content.
        
        Args:
            content: Raw content with potential HTML
            
        Returns:
            str: Content with HTML removed
        """
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        # Replace HTML entities with space
        content = re.sub(r'&[a-zA-Z]+;', ' ', content)
        return content
    
    @staticmethod
    def normalize_whitespace(content: str) -> str:
        """
        Normalize whitespace and line breaks.
        
        Args:
            content: Content with potential whitespace issues
            
        Returns:
            str: Content with normalized whitespace
        """
        # Replace various newlines with standard newline
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        # Remove multiple consecutive newlines but preserve paragraph structure
        content = re.sub(r'\n\s*\n', '\n\n', content)
        # Normalize other whitespace
        content = re.sub(r'\s+', ' ', content)
        return content
    
    @staticmethod
    def clean_markdown_and_urls(content: str) -> str:
        """
        Clean markdown formatting and URLs while preserving meaningful text.
        
        Args:
            content: Content with markdown and URLs
            
        Returns:
            str: Cleaned content
        """
        # Extract text from markdown links
        content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)
        # Remove plain URLs
        content = re.sub(r'http[s]?://\S+', '', content)
        return content
    
    @staticmethod
    def normalize_punctuation(content: str) -> str:
        """
        Normalize quotes, apostrophes, and other punctuation.
        
        Args:
            content: Content with various punctuation styles
            
        Returns:
            str: Content with normalized punctuation
        """
        # Normalize quotes and apostrophes
        content = content.replace('"', '"').replace('"', '"')
        content = content.replace("'", "'").replace("'", "'")
        # Convert multiple punctuation to single
        content = re.sub(r'([!?.]){2,}', r'\1', content)
        # Convert multiple dashes to em-dash
        content = re.sub(r'[-_]{2,}', '—', content)
        return content
    
    @staticmethod
    def fix_spacing(content: str) -> str:
        """
        Fix spacing around punctuation and normalize special whitespace.
        
        Args:
            content: Content with potential spacing issues
            
        Returns:
            str: Content with corrected spacing
        """
        # Remove space before punctuation
        content = re.sub(r'\s+([.,!?])', r'\1', content)
        # Add space after punctuation if missing
        content = re.sub(r'([.,!?])([^\s])', r'\1 \2', content)
        # Replace non-breaking spaces
        content = content.replace('\xa0', ' ')
        return content
    
    def clean_content(self, content: str) -> Optional[str]:
        """
        Apply all cleaning steps to content.
        
        Args:
            content: Raw content to clean
            
        Returns:
            Optional[str]: Cleaned content, or None if input is invalid
        """
        if not content or not isinstance(content, str):
            return None
            
        # Apply cleaning steps in sequence
        content = self.clean_html(content)
        content = self.normalize_whitespace(content)
        content = self.clean_markdown_and_urls(content)
        content = self.normalize_punctuation(content)
        content = self.fix_spacing(content)
        
        # Trim whitespace from lines and entire text
        content = '\n'.join(line.strip() for line in content.split('\n'))
        content = content.strip()
        
        return content if content else None
