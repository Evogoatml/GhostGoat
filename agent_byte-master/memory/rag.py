import chromadb
from chromadb.utils import embedding_functions
from datetime import datetime

class RAGManager:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name="tasks_and_notes",
            embedding_function=self.embedding_fn
        )

    def add_task(self, task_id: int, text: str, metadata: dict):
        """Paper-style chunking: simple for now, can enhance to 128-word windows"""
        self.collection.add(
            documents=[text],
            metadatas=[{**metadata, "task_id": task_id, "timestamp": datetime.utcnow().isoformat()}],
            ids=[f"task_{task_id}"]
        )

    def query(self, query_text: str, n_results: int = 5):
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            include=["metadatas", "documents"]
        )
        return results
