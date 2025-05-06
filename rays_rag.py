"""
Rays RAG (Retrieval Augmented Generation) Implementation
This module:
1. Connects to our existing ChromaDB vectorstore
2. Implements a RAG pipeline to answer questions about Rays tickets and stadium information
3. Uses LangChain for the RAG implementation
"""

from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import torch
from langchain_core.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from dotenv import load_dotenv
import os
from src.rag.processing.cleaner import ContentCleaner
from src.rag.processing.chunker import ContentChunker
import re

try:
    import streamlit as st
    if "anthropic" in st.secrets and "api_key" in st.secrets["anthropic"]:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["anthropic"]["api_key"]
except ImportError:
    # Not running in Streamlit, ignore
    pass

# Load environment variables
load_dotenv()

# Configuration
COLLECTION_NAME = "rays_website_content_bge"

class RaysRAG:
    """
    RAG implementation for answering questions about Rays tickets and stadium information.
    """
    
    def __init__(self):
        """Initialize the RAG components."""
        # Use in-memory ChromaDB client for Streamlit Cloud
        self.client = chromadb.EphemeralClient()
        
        # Always use CPU for embeddings on Streamlit Cloud
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="BAAI/bge-large-en-v1.5",
            device="cpu"
        )
        
        try:
            self.collection = self.client.get_collection(
                name=COLLECTION_NAME,
                embedding_function=self.embedding_function
            )
        except chromadb.errors.NotFoundError:
            self.collection = self.client.create_collection(
                name=COLLECTION_NAME,
                embedding_function=self.embedding_function
            )
            # Parse markdown and populate collection
            self._populate_collection_from_markdown()
        
        # Initialize LLM
        self.llm = ChatAnthropic(
            temperature=0.1,  # Low temperature for more focused answers
            model="claude-3-5-sonnet-20240620"  # Using GPT-4 for better comprehension
        )
        
        # Create the RAG prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful assistant for the Tampa Bay Rays baseball team. 
            Your role is to provide accurate information about tickets, stadium facilities, and game day experiences.
            Any questions asked in another language should be responded to in that language. 
            Use the following pieces of context to answer the question. If it makes sense, provide a link to the source you are referring to.
            If you don't know the answer, just say that you don't know. DO NOT make up any information.
            Always maintain a friendly and professional tone.
            
            Context: {context}"""),
            ("human", "{question}")
        ])
        
        # Create the RAG chain
        self.setup_rag_chain()
    
    def _populate_collection_from_markdown(self):
        """
        Parse the markdown file and populate the ChromaDB collection with cleaned, chunked content.
        """
        md_path = "crawl/content/rays_content_raw.md"
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                md_text = f.read()
        except FileNotFoundError:
            raise RuntimeError(f"Knowledge base markdown file not found at {md_path}")
        if not md_text.strip():
            raise RuntimeError(f"Knowledge base markdown file at {md_path} is empty.")

        # Regex to extract sections: ## Section Name, **Source URL:**, then content until next ## or end
        section_pattern = re.compile(
            r"^##\s+(.*?)\s*\n+"
            r"\*\*Source URL:\*\*\s*(.*?)\s*\n+"
            r"(?:\*\*Crawled Length:\*\*.*?\n+)?"
            r"### Content:\s*\n+"
            r"([\s\S]*?)(?=^## |\Z)",
            re.MULTILINE
        )
        matches = section_pattern.findall(md_text)
        if not matches:
            raise RuntimeError("No sections found in the markdown knowledge base.")

        print(f"Found {len(matches)} sections in the markdown knowledge base.")

        cleaner = ContentCleaner()
        chunker = ContentChunker()
        documents = []
        metadatas = []
        ids = []
        for section_name, url, content in matches:
            print(f"\n--- Section: {section_name} | URL: {url} ---")
            print(f"Raw content (first 200 chars): {content[:200]}")
            cleaned = cleaner.clean_content(content)
            print(f"Cleaned content (first 200 chars): {cleaned[:200] if cleaned else 'None'}")
            if not cleaned:
                print("Content was empty after cleaning, skipping.")
                continue
            chunks = chunker.process_content(cleaned, url)
            print(f"Number of chunks: {len(chunks)}")
            for i, chunk in enumerate(chunks):
                documents.append(chunk["text"])
                metadatas.append(chunk["metadata"])
                ids.append(f"{url}_{i}")
        if not documents:
            raise RuntimeError("No documents were parsed from the markdown knowledge base.")
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
    
    def setup_rag_chain(self):
        """Set up the RAG retrieval and generation chain."""
        # Define the retrieval function
        def retrieve_docs(query: str) -> List[str]:
            results = self.collection.query(
                query_texts=[query],
                n_results=4,  # Retrieve top 4 most relevant chunks
                include=['documents', 'metadatas', 'distances']
            )
            return results['documents'][0]  # Return list of document texts
        
        # Create the RAG chain
        self.chain = (
            {"context": retrieve_docs, "question": RunnablePassthrough()}
            | self.prompt
            | self.llm
            | StrOutputParser()
        )
    
    def ask(self, question: str) -> str:
        """
        Ask a question and get a response using the RAG system.
        
        Args:
            question (str): The question about Rays tickets or stadium information
            
        Returns:
            str: The generated answer based on the retrieved context
        """
        try:
            response = self.chain.invoke(question)
            return response
        except Exception as e:
            return f"Sorry, I encountered an error while processing your question: {str(e)}"

def main():
    """Main function to test the RAG implementation."""
    # Initialize the RAG system
    rag = RaysRAG()
    
    # Test questions
    test_questions = [
        "What are the ticket specials available?",
        "Tell me about parking at the stadium",
        "What food options are available at the stadium?",
        "Are there any student discounts for tickets?",
        "How can I get season tickets?"
    ]
    
    # Test each question
    print("\n=== Testing RAG System ===")
    for question in test_questions:
        print(f"\nQ: {question}")
        answer = rag.ask(question)
        print(f"A: {answer}")
        print("-" * 80)

if __name__ == "__main__":
    main() 
    
