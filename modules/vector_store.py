import chromadb
from chromadb.utils import embedding_functions
import os

class VectorStore:
    def __init__(self, collection_name="user_context"):
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chroma_db")
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.ef = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name=collection_name, 
            embedding_function=self.ef
        )

    def add_documents(self, documents, ids, metadatas=None):
        """Adds documents to the vector store."""
        self.collection.add(
            documents=documents,
            ids=ids,
            metadatas=metadatas
        )

    def query(self, query_text, n_results=3):
        """Queries the vector store for similar documents."""
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        return results

# Initialize a global instance for the brain squad
vector_store = VectorStore()
