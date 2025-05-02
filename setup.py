"""
Setup configuration for the RAG system.
"""

from setuptools import setup, find_packages

setup(
    name="robo-ragmond",
    version="0.1.0",
    description="RAG system for Tampa Bay Rays content",
    author="Your Name",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "crawl4ai",
        "chromadb",
        "sentence-transformers",
        "torch",
        "python-dotenv",
    ],
    python_requires=">=3.8",
) 