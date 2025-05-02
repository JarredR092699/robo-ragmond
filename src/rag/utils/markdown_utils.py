"""
Markdown utilities module for the RAG system.
Provides functionality to generate and manage markdown content.
"""

import os
from typing import Dict
from datetime import datetime
from pathlib import Path

class MarkdownGenerator:
    """Class for generating well-formatted markdown content."""
    
    def __init__(self, content_dir: str = "./content"):
        """
        Initialize the markdown generator.
        
        Args:
            content_dir: Directory to store markdown files
        """
        self.content_dir = Path(content_dir)
        self.content_dir.mkdir(exist_ok=True)
    
    def generate_header(self, title: str) -> str:
        """
        Generate a markdown header with title and timestamp.
        
        Args:
            title: Title for the markdown document
            
        Returns:
            str: Formatted markdown header
        """
        return f"""# {title}

*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

This document contains raw content crawled from various {title} pages.

"""
    
    def generate_toc(self, urls: list[str]) -> str:
        """
        Generate a table of contents from URLs.
        
        Args:
            urls: List of URLs to include in TOC
            
        Returns:
            str: Formatted table of contents
        """
        toc = "## Table of Contents\n\n"
        
        for url in urls:
            # Create page title from URL
            page_title = url.split('/')[-1].replace('-', ' ').title()
            # Create anchor from last part of URL
            anchor = url.split('/')[-1].lower()
            toc += f"- [{page_title}](#{anchor})\n"
        
        return toc + "\n---\n\n"
    
    def generate_content_section(self, url: str, content: str) -> str:
        """
        Generate a content section for a single URL.
        
        Args:
            url: Source URL of the content
            content: The content to format
            
        Returns:
            str: Formatted content section
        """
        # Create section title from URL
        page_title = url.split('/')[-1].replace('-', ' ').title()
        
        section = f"## {page_title}\n\n"
        section += f"**Source URL:** {url}\n\n"
        section += f"**Crawled Length:** {len(content)} characters\n\n"
        section += "### Content:\n\n"
        section += content
        section += "\n\n---\n\n"
        
        return section
    
    def save_content_to_markdown(
        self,
        url_content_map: Dict[str, str],
        output_file: str = "content_raw.md",
        title: str = "Website Content"
    ) -> str:
        """
        Save content to a markdown file with proper formatting.
        
        Args:
            url_content_map: Dictionary mapping URLs to their content
            output_file: Name of the output file
            title: Title for the markdown document
            
        Returns:
            str: Path to the generated markdown file
        """
        output_path = self.content_dir / output_file
        
        with open(output_path, 'w', encoding='utf-8') as f:
            # Write header
            f.write(self.generate_header(title))
            
            # Generate and write table of contents
            f.write(self.generate_toc(list(url_content_map.keys())))
            
            # Write content sections
            for url, content in url_content_map.items():
                f.write(self.generate_content_section(url, content))
        
        print(f"\nContent saved to: {output_path}")
        return str(output_path)
    
    @staticmethod
    def format_metadata(metadata: Dict) -> str:
        """
        Format metadata as markdown.
        
        Args:
            metadata: Dictionary of metadata
            
        Returns:
            str: Formatted metadata section
        """
        metadata_section = "**Metadata:**\n\n"
        for key, value in metadata.items():
            metadata_section += f"- {key}: {value}\n"
        return metadata_section + "\n"
    
    @staticmethod
    def format_query_results(
        query: str,
        results: Dict[str, list],
        max_preview_length: int = 200
    ) -> str:
        """
        Format query results as markdown.
        
        Args:
            query: The query string
            results: Dictionary of query results
            max_preview_length: Maximum length for content preview
            
        Returns:
            str: Formatted results section
        """
        output = f"### Query: {query}\n\n"
        
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        )):
            relevance_score = 1 - (distance / 2)
            output += f"#### Result {i+1} (Relevance: {relevance_score:.2f})\n\n"
            output += f"Source: {metadata.get('source_url', 'Unknown')}\n\n"
            output += f"Preview:\n```\n{doc[:max_preview_length]}...\n```\n\n"
        
        return output
