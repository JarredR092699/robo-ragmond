from src.rag.storage.vectorstore import RaysVectorStore

# 1. Initialize the vector store
vector_store = RaysVectorStore(
    persist_dir="./test_chroma_db",
    collection_name="test_collection"
)

# 2. Add dummy documents
documents = [
    "The Tampa Bay Rays play at Tropicana Field.",
    "Season tickets are available for all home games.",
    "Student discounts are offered for select games."
]
metadatas = [
    {"url": "https://www.mlb.com/rays/ballpark/gms-field/a-z-guide"},
    {"url": "https://www.mlb.com/rays/tickets/season-tickets/season-membership"},
    {"url": "https://www.mlb.com/rays/tickets/specials/student-ticket-offers"}
]
ids = ["doc1", "doc2", "doc3"]

vector_store.add_documents(documents, metadatas, ids)

# 3. Query the vector store
query = "Where do the Rays play?"
results = vector_store.query([query], n_results=2)
print("\nQuery Results:")
print(results)

# 4. (Optional) Test semantic similarity
pairs = [
    ("Where do the Rays play?", "What is the home stadium of the Rays?"),
    ("Are there student discounts?", "Can students get cheaper tickets?")
]
similarity_results = vector_store.test_semantic_similarity(pairs)
print("\nSemantic Similarity Results:")
print(similarity_results)