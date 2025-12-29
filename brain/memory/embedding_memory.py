# brain/embedding_memory.py
import json
import os
from sentence_transformers import SentenceTransformer, util

class EmbeddingMemory:
    def __init__(self, path="memory_embeddings.json"):
        self.path = path
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.memory = self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, "r") as f:
                data = json.load(f)
                for item in data:
                    item["embedding"] = item.get("embedding", [])
                return data
        return []

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.memory, f, indent=2)

    def store(self, user_id, key, text):
        embedding = self.model.encode(text).tolist()
        self.memory.append({"user": user_id, "key": key, "text": text, "embedding": embedding})
        self.save()

    def recall(self, query, top_k=3):
        if not self.memory:
            return []
        query_vec = self.model.encode(query)
        sims = [
            (util.cos_sim(query_vec, item["embedding"]).item(), item)
            for item in self.memory if item["embedding"]
        ]
        sims.sort(reverse=True, key=lambda x: x[0])
        return [item for _, item in sims[:top_k]]
