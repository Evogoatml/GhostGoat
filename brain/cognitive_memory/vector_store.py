import chromadb

class MemoryStore:
    def __init__(self):
        self.chroma_client = chromadb.Client()
        self.collection = self.chroma_client.create_collection("aig_memories")

    def store(self, data):
        # Store embeddings and metadata
        self.collection.add(document=data['text'], metadata=data.get('meta', {}))
    
    def retrieve(self, query):
        # Semantic search
        return self.collection.query(query_texts=[query])