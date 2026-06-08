"""RAG System - Vector Database with Semantic Search"""
import os
import json
import logging
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from config import config

logger = logging.getLogger(__name__)

class RAGSystem:
    def __init__(self):
        self.embedding_model = SentenceTransformer(config.rag.embedding_model)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=config.rag.vector_db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="alo_knowledge",
            metadata={"hnsw:space": "cosine"}
        )
        
        logger.info(f"RAG system initialized with {self.collection.count()} documents")
    
    def _chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split text into chunks with overlap"""
        chunks = []
        chunk_size = config.rag.chunk_size
        overlap = config.rag.chunk_overlap
        
        # Simple chunking by characters
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size]
            if chunk.strip():
                chunk_id = hashlib.md5(f"{chunk}{i}".encode()).hexdigest()
                chunks.append({
                    "id": chunk_id,
                    "text": chunk,
                    "metadata": {
                        **metadata,
                        "chunk_index": i // (chunk_size - overlap),
                        "timestamp": datetime.now().isoformat()
                    }
                })
        
        return chunks
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> int:
        """
        Add documents to vector database
        documents: [{"text": str, "metadata": dict}]
        """
        all_chunks = []
        for doc in documents:
            chunks = self._chunk_text(doc["text"], doc.get("metadata", {}))
            all_chunks.extend(chunks)
        
        if not all_chunks:
            return 0
        
        # Extract data for ChromaDB
        ids = [chunk["id"] for chunk in all_chunks]
        texts = [chunk["text"] for chunk in all_chunks]
        metadatas = [chunk["metadata"] for chunk in all_chunks]
        
        # Generate embeddings
        embeddings = self.embedding_model.encode(texts, show_progress_bar=False).tolist()
        
        # Add to collection
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
        
        logger.info(f"Added {len(all_chunks)} chunks to RAG")
        return len(all_chunks)
    
    def add_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """Convenience method to add single text"""
        return self.add_documents([{"text": text, "metadata": metadata or {}}])
    
    def add_file(self, filepath: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """Add file contents to RAG"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            file_metadata = metadata or {}
            file_metadata.update({
                "source": filepath,
                "filename": os.path.basename(filepath),
                "type": "file"
            })
            
            return self.add_text(content, file_metadata)
        except Exception as e:
            logger.error(f"Error adding file {filepath}: {e}")
            return 0
    
    def add_directory(self, directory: str, extensions: Optional[List[str]] = None) -> int:
        """Recursively add all files from directory"""
        extensions = extensions or ['.py', '.txt', '.md', '.json', '.yaml', '.yml']
        total_chunks = 0
        
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    filepath = os.path.join(root, file)
                    chunks = self.add_file(filepath)
                    total_chunks += chunks
        
        return total_chunks
    
    def search(self, query: str, n_results: Optional[int] = None, filter_metadata: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Semantic search in vector database
        Returns list of relevant chunks with metadata
        """
        n_results = n_results or config.rag.max_results
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode(query, show_progress_bar=False).tolist()
        
        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_metadata
        )
        
        # Format results
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                distance = results['distances'][0][i]
                similarity = 1 - distance  # Convert distance to similarity
                
                if similarity >= config.rag.similarity_threshold:
                    formatted_results.append({
                        "text": doc,
                        "metadata": results['metadatas'][0][i],
                        "similarity": similarity,
                        "id": results['ids'][0][i]
                    })
        
        logger.debug(f"Search for '{query}' returned {len(formatted_results)} results")
        return formatted_results
    
    def retrieve_context(self, query: str, max_tokens: int = 2000) -> str:
        """Retrieve relevant context for a query, respecting token limit"""
        results = self.search(query)
        
        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 4  # Rough estimation: 1 token ≈ 4 chars
        
        for result in results:
            text = result["text"]
            if total_chars + len(text) > max_chars:
                break
            context_parts.append(f"[Source: {result['metadata'].get('source', 'unknown')}]\n{text}")
            total_chars += len(text)
        
        return "\n\n---\n\n".join(context_parts) if context_parts else ""
    
    def delete_by_metadata(self, filter_metadata: Dict) -> int:
        """Delete documents matching metadata filter"""
        try:
            # Get matching IDs
            results = self.collection.get(where=filter_metadata)
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                logger.info(f"Deleted {len(results['ids'])} documents")
                return len(results['ids'])
            return 0
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            return 0
    
    def clear_all(self):
        """Clear entire database"""
        self.client.delete_collection("alo_knowledge")
        self.collection = self.client.get_or_create_collection(
            name="alo_knowledge",
            metadata={"hnsw:space": "cosine"}
        )
        logger.info("Cleared all RAG data")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        count = self.collection.count()
        return {
            "total_chunks": count,
            "embedding_model": config.rag.embedding_model,
            "vector_db_path": config.rag.vector_db_path
        }

rag_system = RAGSystem()
