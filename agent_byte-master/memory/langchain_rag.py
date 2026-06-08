#!/usr/bin/env python3
"""
Enhanced GraphRAG with LangChain patterns
- Document loading
- Text splitting  
- Embeddings (local)
- Vector index
- Graph storage
- RAG chain
"""

import os
import json
import logging
import hashlib
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field

import requests

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_EMBED = os.getenv("OLLAMA_EMBED", "nomic-embed-text")
OLLAMA_LLM = os.getenv("OLLAMA_LLM", "llama3.2")

PAYLOADS_DIR = Path('/home/popic/PayloadsAllTheThings')

@dataclass
class Document:
    page_content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def id(self) -> str:
        content_hash = hashlib.md5(self.page_content.encode()).hexdigest()[:8]
        return f"doc_{content_hash}"

@dataclass  
class Node:
    id: str
    embedding: List[float] = field(default_factory=list)
    document: Document = None
    entities: List[Dict] = field(default_factory=list)

class TextSplitter:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
    def split_text(self, text: str) -> List[str]:
        paragraphs = text.split('\n\n')
        chunks = []
        current = ""
        
        for para in paragraphs:
            if len(current) + len(para) > self.chunk_size and current:
                chunks.append(current.strip())
                current = para
            else:
                current += "\n\n" + para if current else para
                
        if current:
            chunks.append(current.strip())
            
        return [c for c in chunks if len(c) > 50]

class Embeddings:
    """Local embeddings using Ollama"""
    
    def __init__(self, model: str = OLLAMA_EMBED):
        self.model = model
        self.url = f"{OLLAMA_URL}/api/embeddings"
        
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            emb = self.embed_query(text)
            if emb:
                embeddings.append(emb)
        return embeddings
    
    def embed_query(self, text: str) -> Optional[List[float]]:
        try:
            response = requests.post(
                self.url,
                json={"model": self.model, "prompt": text},
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get('embedding')
        except Exception as e:
            logger.error(f"Embedding error: {e}")
        return None

class InMemoryVectorStore:
    def __init__(self, embedding: Embeddings):
        self.embedding = embedding
        self.nodes: List[Node] = []
        
    def add_documents(self, documents: List[Document]):
        texts = [doc.page_content for doc in documents]
        embeddings = self.embedding.embed_documents(texts)
        
        for doc, emb in zip(documents, embeddings):
            if emb:
                node = Node(
                    id=doc.id,
                    embedding=emb,
                    document=doc
                )
                self.nodes.append(node)
                
    def similarity_search(self, query: str, top_k: int = 5) -> List[Document]:
        query_emb = self.embedding.embed_query(query)
        if not query_emb:
            return []
            
        scores = []
        for node in self.nodes:
            if node.embedding:
                score = self._cosine_similarity(query_emb, node.embedding)
                scores.append((score, node))
                
        scores.sort(reverse=True)
        return [n.document for _, n in scores[:top_k]]
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = sum(x * x for x in a) ** 0.5
        mag_b = sum(x * x for x in b) ** 0.5
        return dot / (mag_a * mag_b) if mag_a * mag_b else 0

class InMemoryGraphStore:
    def __init__(self):
        self.entities: Dict[str, Dict] = {}
        self.relations: List[Dict] = []
        
    def add_entity(self, entity_type: str, entity_id: str, properties: Dict):
        key = f"{entity_type}:{entity_id}"
        self.entities[key] = {
            "type": entity_type,
            "id": entity_id,
            "properties": properties
        }
        
    def add_relation(self, from_id: str, to_id: str, relation_type: str, properties: Dict = None):
        self.relations.append({
            "from": from_id,
            "to": to_id,
            "type": relation_type,
            "properties": properties or {}
        })
        
    def get_entity(self, entity_type: str, entity_id: str) -> Optional[Dict]:
        key = f"{entity_type}:{entity_id}"
        return self.entities.get(key)
    
    def get_neighbors(self, entity_id: str, relation_type: str = None, depth: int = 2) -> List[Dict]:
        results = []
        visited = set()
        queue = [(entity_id, 0)]
        
        while queue:
            current, d = queue.pop(0)
            if current in visited or d > depth:
                continue
            visited.add(current)
            
            for rel in self.relations:
                if rel["from"] == current:
                    results.append(rel)
                    if rel["to"] not in visited:
                        queue.append((rel["to"], d + 1))
                        
        return results

class ChatOllama:
    """Ollama LLM wrapper"""
    
    def __init__(self, model: str = OLLAMA_LLM):
        self.model = model
        self.url = f"{OLLAMA_URL}/api/generate"
        
    def invoke(self, prompt: str, **kwargs) -> str:
        try:
            response = requests.post(
                self.url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", 0.7),
                        "top_p": kwargs.get("top_p", 0.9),
                    }
                },
                timeout=kwargs.get("timeout", 120)
            )
            if response.status_code == 200:
                return response.json().get('response', '')
        except Exception as e:
            logger.error(f"LLM invoke error: {e}")
        return ""
    
    def batch(self, prompts: List[str]) -> List[str]:
        return [self.invoke(p) for p in prompts]

class RetrievalQAChain:
    """LangChain-style Retrieval QA Chain"""
    
    def __init__(
        self,
        llm: ChatOllama,
        retriever: InMemoryVectorStore,
        graph_store: InMemoryGraphStore = None
    ):
        self.llm = llm
        self.retriever = retriever
        self.graph_store = graph_store
        
    def get_context(self, query: str) -> str:
        docs = self.retriever.similarity_search(query, top_k=5)
        if not docs:
            return ""
            
        context = "=== RETRIEVED DOCUMENTS ===\n\n"
        for i, doc in enumerate(docs, 1):
            context += f"[Document {i}] ({doc.metadata.get('source', 'unknown')})\n"
            context += doc.page_content[:500] + "\n\n"
            
        if self.graph_store:
            query_entities = self._extract_entities(query)
            context += "\n=== KNOWLEDGE GRAPH ===\n\n"
            for entity in query_entities:
                neighbors = self.graph_store.get_neighbors(entity)
                for n in neighbors[:3]:
                    context += f"{n['from']} --[{n['type']}]--> {n['to']}\n"
                    
        return context
    
    def _extract_entities(self, text: str) -> List[str]:
        entities = []
        patterns = {
            'sql injection': 'vulnerability:sql-injection',
            'buffer overflow': 'vulnerability:buffer-overflow',
            'xss': 'vulnerability:xss',
            'rop': 'technique:rop',
            'privilege escalation': 'technique:privesc',
        }
        text_lower = text.lower()
        for pattern, entity in patterns.items():
            if pattern in text_lower:
                entities.append(entity)
        return entities
        
    def invoke(self, query: str) -> str:
        context = self.get_context(query)
        
        prompt = f"""You are a penetration testing expert. Use the context below to answer accurately.

Context:
{context}

Question: {query}

Answer:"""

        return self.llm.invoke(prompt)

def load_documents(directory: Path) -> List[Document]:
    documents = []
    
    for category in directory.iterdir():
        if not category.is_dir():
            continue
        if category.name.startswith('_') or category.name.startswith('.'):
            continue
            
        for md_file in category.glob('*.md'):
            try:
                content = md_file.read_text(encoding='utf-8', errors='ignore')
                if len(content) > 100:
                    doc = Document(
                        page_content=content[:3000],
                        metadata={
                            'source': str(md_file),
                            'category': category.name,
                            'file': md_file.stem
                        }
                    )
                    documents.append(doc)
            except Exception as e:
                logger.error(f"Error loading {md_file}: {e}")
                
    return documents

def run_demo():
    logger.info("Loading documents...")
    documents = load_documents(PAYLOADS_DIR)
    logger.info(f"Loaded {len(documents)} documents")
    
    logger.info("Creating embeddings...")
    embeddings = Embeddings()
    
    logger.info("Building vector store...")
    vector_store = InMemoryVectorStore(embeddings)
    vector_store.add_documents(documents)
    logger.info(f"Indexed {len(vector_store.nodes)} nodes")
    
    logger.info("Building graph store...")
    graph_store = InMemoryGraphStore()
    
    for doc in documents[:50]:
        content_lower = doc.page_content.lower()
        
        vuln_patterns = [
            ('sql injection', 'sql-injection', 'VULNERABILITY'),
            ('buffer overflow', 'buffer-overflow', 'VULNERABILITY'),
            ('xss', 'xss', 'VULNERABILITY'),
            ('command injection', 'command-injection', 'VULNERABILITY'),
        ]
        
        for pattern, eid, etype in vuln_patterns:
            if pattern in content_lower:
                graph_store.add_entity(etype, eid, {
                    'name': pattern,
                    'category': doc.metadata.get('category')
                })
                graph_store.add_relation(eid, doc.metadata.get('category', 'unknown'), 'BELONGS_TO')
                
    logger.info(f"Graph: {len(graph_store.entities)} entities, {len(graph_store.relations)} relations")
    
    logger.info("Initializing LLM...")
    llm = Chat Ollama()
    
    logger.info("Creating RAG chain...")
    rag_chain = RetrievalQAChain(llm, vector_store, graph_store)
    
    logger.info("\n=== TESTING RAG ===")
    test_questions = [
        "How does SQL injection work?",
        "Explain buffer overflow exploitation",
        "What is ROP chaining?",
    ]
    
    for q in test_questions:
        print(f"\n{'='*50}")
        print(f"Q: {q}")
        print(f"{'='*50}")
        
        answer = rag_chain.invoke(q)
        print(f"A: {answer[:800]}...")

if __name__ == '__main__':
    run_demo()