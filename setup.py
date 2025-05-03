"""
Setup configuration for the RAG system.
"""

from setuptools import setup, find_packages

setup(
    name="robo-ragmond",
    version="0.1.0",
    description="RAG system for Tampa Bay Rays content",
    author="Jarred Robidoux",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "crawl4ai",
        "chromadb",
        "sentence-transformers",
        "torch",
        "python-dotenv",
        "langchain-core", 
        "langchain-anthropic"
    ],
    python_requires=">=3.9",
) 