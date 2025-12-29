"""
Unified Memory System Interface
Provides common interface for different memory backends
"""

import logging
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from unified_config import MemoryBackend, MemoryConfig, get_config

logger = logging.getLogger(__name__)


@dataclass
class MemoryItem:
    """Memory item"""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class MemoryInterface(ABC):
    """Abstract base class for memory interfaces"""
    
    @abstractmethod
    async def store(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """Store a memory item"""
        pass
    
    @abstractmethod
    async def retrieve(self, query: str, top_k: int = 5) -> List[MemoryItem]:
        """Retrieve similar memory items"""
        pass
    
    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        """Delete a memory item"""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        pass


class ChromaDBMemory(MemoryInterface):
    """ChromaDB memory backend"""
    
    def __init__(self, config: MemoryConfig):
        self.config = config
        self.client = None
        self.collection = None
        self._initialize()
    
    def _initialize(self):
        """Initialize ChromaDB"""
        try:
            import chromadb
            from chromadb.config import Settings
            
            self.client = chromadb.PersistentClient(
                path=self.config.path,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.config.collection_name,
                metadata={"description": "GhostGoat unified memory"}
            )
            
            logger.info(f"ChromaDB initialized at {self.config.path}")
        except ImportError:
            raise ImportError("ChromaDB not installed. Install with: pip install chromadb")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    async def store(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """Store memory in ChromaDB"""
        import uuid
        
        memory_id = str(uuid.uuid4())
        metadata = metadata or {}
        metadata["timestamp"] = datetime.now().isoformat()
        
        # Generate embedding if needed
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(self.config.embedding_model)
            embedding = model.encode(content).tolist()
        except ImportError:
            logger.warning("sentence-transformers not available, storing without embedding")
            embedding = None
        
        if embedding:
            self.collection.add(
                ids=[memory_id],
                documents=[content],
                embeddings=[embedding],
                metadatas=[metadata]
            )
        else:
            self.collection.add(
                ids=[memory_id],
                documents=[content],
                metadatas=[metadata]
            )
        
        return memory_id
    
    async def retrieve(self, query: str, top_k: int = 5) -> List[MemoryItem]:
        """Retrieve similar memories from ChromaDB"""
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(self.config.embedding_model)
            query_embedding = model.encode(query).tolist()
        except ImportError:
            logger.warning("sentence-transformers not available, using text search")
            results = self.collection.get()
            # Simple text matching fallback
            query_lower = query.lower()
            matches = []
            for i, doc in enumerate(results.get("documents", [])):
                if query_lower in doc.lower():
                    matches.append({
                        "id": results["ids"][i],
                        "content": doc,
                        "metadata": results["metadatas"][i] if results.get("metadatas") else {},
                        "distance": 0.0
                    })
            matches = matches[:top_k]
        else:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            
            matches = []
            if results.get("ids") and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    matches.append({
                        "id": results["ids"][0][i],
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                        "distance": results["distances"][0][i] if results.get("distances") else 0.0
                    })
        
        return [
            MemoryItem(
                id=match["id"],
                content=match["content"],
                metadata=match["metadata"],
                timestamp=match["metadata"].get("timestamp")
            )
            for match in matches
        ]
    
    async def delete(self, memory_id: str) -> bool:
        """Delete memory from ChromaDB"""
        try:
            self.collection.delete(ids=[memory_id])
            return True
        except Exception as e:
            logger.error(f"Failed to delete memory: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get ChromaDB statistics"""
        count = self.collection.count()
        return {
            "backend": "chromadb",
            "count": count,
            "collection": self.config.collection_name,
            "path": self.config.path
        }


class KnowledgeTankMemory(MemoryInterface):
    """Knowledge Tank memory backend"""
    
    def __init__(self, config: MemoryConfig):
        self.config = config
        self.tank = None
        self._initialize()
    
    def _initialize(self):
        """Initialize Knowledge Tank"""
        try:
            from knowledge_tank import KnowledgeTank
            self.tank = KnowledgeTank()
            logger.info("Knowledge Tank initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Knowledge Tank: {e}")
            raise
    
    async def store(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """Store in Knowledge Tank"""
        # Knowledge Tank is primarily for algorithms, not general memory
        # This is a simplified implementation
        logger.warning("Knowledge Tank is not ideal for general memory storage")
        return "stored"
    
    async def retrieve(self, query: str, top_k: int = 5) -> List[MemoryItem]:
        """Retrieve from Knowledge Tank"""
        results = self.tank.search(query, limit=top_k)
        
        return [
            MemoryItem(
                id=str(r.get("id", "")),
                content=r.get("description", ""),
                metadata=r
            )
            for r in results
        ]
    
    async def delete(self, memory_id: str) -> bool:
        """Delete from Knowledge Tank"""
        # Knowledge Tank doesn't support deletion easily
        return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Knowledge Tank statistics"""
        stats = self.tank.get_stats()
        return {
            "backend": "knowledge_tank",
            **stats
        }


class UnifiedMemory:
    """
    Unified memory system
    Provides common interface for different memory backends
    """
    
    def __init__(self, config: Optional[MemoryConfig] = None):
        if config is None:
            config = get_config().memory
        self.config = config
        self.backend: Optional[MemoryInterface] = None
        self._initialize_backend()
    
    def _initialize_backend(self):
        """Initialize the appropriate memory backend"""
        if self.config.backend == MemoryBackend.CHROMADB:
            self.backend = ChromaDBMemory(self.config)
        elif self.config.backend == MemoryBackend.KNOWLEDGE_TANK:
            self.backend = KnowledgeTankMemory(self.config)
        else:
            logger.warning(f"Unknown backend {self.config.backend}, using ChromaDB")
            self.config.backend = MemoryBackend.CHROMADB
            self.backend = ChromaDBMemory(self.config)
    
    async def store(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """Store memory"""
        return await self.backend.store(content, metadata)
    
    async def retrieve(self, query: str, top_k: int = 5) -> List[MemoryItem]:
        """Retrieve memories"""
        return await self.backend.retrieve(query, top_k)
    
    async def delete(self, memory_id: str) -> bool:
        """Delete memory"""
        return await self.backend.delete(memory_id)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        return await self.backend.get_stats()
    
    def switch_backend(self, backend: MemoryBackend, path: Optional[str] = None):
        """Switch to a different memory backend"""
        self.config.backend = backend
        if path:
            self.config.path = path
        self._initialize_backend()
        logger.info(f"Switched to {backend.value} backend")


# Factory function
def create_memory(config: Optional[MemoryConfig] = None) -> UnifiedMemory:
    """Create UnifiedMemory instance"""
    if config is None:
        config = get_config().memory
    return UnifiedMemory(config)
