"""
Vector store module for the RAG system.
Provides functionality to store and retrieve content using ChromaDB.
"""

import os
from typing import List, Dict, Tuple, Optional, Any
import torch
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from chromadb import errors as chromadb_errors
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class RaysVectorStore:
    """Vector store class for managing content embeddings and retrieval."""
    
    def __init__(
        self,
        persist_dir: str,
        collection_name: str
    ):
        """
        Initialize the vector store.
        
        Args:
            persist_dir: Directory to persist ChromaDB data
            collection_name: Name of the collection to use
        """
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        
        # Ensure persistence directory exists
        os.makedirs(persist_dir, exist_ok=True)
        
        # Initialize client and collection
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self._initialize_collection()
    
    def _initialize_collection(self):
        """
        Initialize or get existing ChromaDB collection.
        
        Returns:
            chromadb.Collection: The initialized collection
        """
        # Use sentence-transformers for better embeddings
        embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="multi-qa-MiniLM-L6-cos-v1"
        )
        
        try:
            # Try to get existing collection
            collection = self.client.get_collection(
                name=self.collection_name,
                embedding_function=embedding_function
            )
            print(f"Using existing collection: {self.collection_name}")
            
        except (ValueError, chromadb.errors.NotFoundError):
            # Create new collection if it doesn't exist
            print(f"Creating new collection: {self.collection_name}")
            try:
                collection = self.client.create_collection(
                    name=self.collection_name,
                    embedding_function=embedding_function,
                    metadata={"hnsw:space": "cosine"}  # Use cosine similarity
                )
            except ValueError as e:
                # Handle case where collection exists but with different embedding
                if "Embedding function name mismatch" in str(e):
                    print("Warning: Found existing collection with different embedding function")
                    print("Deleting existing collection and creating new one")
                    self.client.delete_collection(self.collection_name)
                    collection = self.client.create_collection(
                        name=self.collection_name,
                        embedding_function=embedding_function,
                        metadata={"hnsw:space": "cosine"}
                    )
                else:
                    raise e
        
        return collection
    
    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None
    ) -> None:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of text documents to add
            metadatas: Optional list of metadata dictionaries
            ids: Optional list of document IDs
        """
        if not documents:
            return
            
        if not ids:
            # Generate sequential IDs if none provided
            ids = [f"doc_{i}" for i in range(len(documents))]
            
        if not metadatas:
            # Create empty metadata if none provided
            metadatas = [{} for _ in documents]
            
        # Verify we have valid data
        if len(documents) != len(metadatas) or len(documents) != len(ids):
            raise ValueError("Length mismatch between documents, metadatas, and ids")
            
        # Add to collection
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
    
    def query(
        self,
        query_texts: List[str],
        n_results: int = 3,
        where: Optional[Dict] = None,
        where_document: Optional[Dict] = None
    ) -> Dict[str, List]:
        """
        Query the vector store for similar documents.
        
        Args:
            query_texts: List of query strings
            n_results: Number of results to return per query
            where: Optional filter conditions for metadata
            where_document: Optional filter conditions for documents
            
        Returns:
            Dict containing documents, metadatas, and distances
        """
        return self.collection.query(
            query_texts=query_texts,
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=['documents', 'metadatas', 'distances']
        )
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection.
        
        Returns:
            Dict containing collection statistics
        """
        return {
            "name": self.collection.name,
            "count": self.collection.count(),
            "metadata": self.collection.metadata
        }
    
    def test_semantic_similarity(
        self,
        query_pairs: List[Tuple[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Test semantic similarity between pairs of queries.
        
        Args:
            query_pairs: List of query string pairs to compare
            
        Returns:
            List of dictionaries containing similarity metrics
        """
        results = []
        for query1, query2 in query_pairs:
            try:
                # Get embeddings for both queries
                results1 = self.query([query1], n_results=1)
                results2 = self.query([query2], n_results=1)
                
                # Check if we got any results for either query
                if not results1['distances'] or not results2['distances']:
                    results.append({
                        "query1": query1,
                        "query2": query2,
                        "similarity_score": 0.0,
                        "distances": {
                            "query1": None,
                            "query2": None
                        },
                        "error": "No results found for one or both queries"
                    })
                    continue
                
                # Calculate similarity using cosine distance
                # ChromaDB returns cosine distances, where 0 means identical
                # and 2 means completely different
                distance1 = results1['distances'][0][0]
                distance2 = results2['distances'][0][0]
                
                # Convert distances to similarity score (0 to 1)
                similarity_score = 1 - (distance1 + distance2) / 2
                
                results.append({
                    "query1": query1,
                    "query2": query2,
                    "similarity_score": similarity_score,
                    "distances": {
                        "query1": distance1,
                        "query2": distance2
                    }
                })
            except Exception as e:
                results.append({
                    "query1": query1,
                    "query2": query2,
                    "similarity_score": 0.0,
                    "distances": {
                        "query1": None,
                        "query2": None
                    },
                    "error": str(e)
                })
        
        return results 