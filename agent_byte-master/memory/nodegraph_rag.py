"""
NodeGraphRAG - Unified Semantic Vector + Knowledge Graph System
Combines: NeuroGraph (networkx) + Semantic Vectors (sentence_transformers) + RAG
"""

import os
import json
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

# Optional imports with fallbacks
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except Exception:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except Exception:
    nx = None
    NETWORKX_AVAILABLE = False

try:
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False


class NodeGraphRAG:
    """
    Unified Node Graph RAG with Semantic Vector Search
    
    Architecture:
    - Nodes: agents, tasks, concepts, algorithms, memory fragments
    - Edges: relationships (depends_on, similar_to, implements, etc.)
    - Vectors: semantic embeddings for each node
    - Retrieval: hybrid graph + vector search
    """
    
    def __init__(self, 
                 embedding_model: str = "all-MiniLM-L6-v2",
                 db_path: str = None):
        
        self.db_path = Path(db_path) if db_path else Path(__file__).parent / "vector_db" / "nodegraph.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize graph
        if NETWORKX_AVAILABLE:
            self.graph = nx.MultiDiGraph()
        else:
            self.graph = {"nodes": {}, "edges": []}  # Fallback dict-based
        
        # Initialize embedding model
        self.embedding_model_name = embedding_model
        self.model = None
        self.embeddings = {}  # node_id -> embedding vector
        
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.model = SentenceTransformer(embedding_model)
            except Exception as e:
                print(f"Warning: Could not load embedding model: {e}")
        
        # Load existing state
        self._load()
    
    def _load(self):
        """Load graph and embeddings from disk."""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r') as f:
                    data = json.load(f)
                
                # Load graph
                if NETWORKX_AVAILABLE and 'graph' in data:
                    self.graph = nx.node_link_graph(data['graph'])
                
                # Load embeddings
                if 'embeddings' in data:
                    self.embeddings = {
                        k: np.array(v) for k, v in data['embeddings'].items()
                    }
                
                print(f"Loaded NodeGraphRAG: {self.count_nodes()} nodes, {self.count_edges()} edges")
            except Exception as e:
                print(f"Warning: Could not load state: {e}")
    
    def save(self):
        """Save graph and embeddings to disk."""
        try:
            data = {}
            
            # Save graph
            if NETWORKX_AVAILABLE:
                data['graph'] = nx.node_link_data(self.graph)
            
            # Save embeddings
            data['embeddings'] = {
                k: v.tolist() for k, v in self.embeddings.items()
            }
            
            with open(self.db_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save state: {e}")
    
    # ---- Node Management ----
    
    def add_node(self, 
                 node_id: str, 
                 kind: str, 
                 text: str = "", 
                 metadata: Dict[str, Any] = None) -> str:
        """
        Add a node with semantic embedding.
        
        Args:
            node_id: Unique identifier
            kind: Node type (agent, task, algorithm, concept, memory)
            text: Text to embed for semantic search
            metadata: Additional properties
        """
        props = metadata or {}
        props['kind'] = kind
        props['text'] = text
        
        if NETWORKX_AVAILABLE:
            self.graph.add_node(node_id, **props)
        else:
            self.graph["nodes"][node_id] = props
        
        # Generate embedding
        if self.model and text:
            try:
                embedding = self.model.encode(text)
                self.embeddings[node_id] = embedding
            except Exception as e:
                print(f"Warning: Could not embed node {node_id}: {e}")
        
        return node_id
    
    def get_node(self, node_id: str) -> Optional[Dict]:
        """Get node data."""
        if NETWORKX_AVAILABLE:
            return self.graph.nodes.get(node_id)
        return self.graph["nodes"].get(node_id)
    
    def update_node(self, node_id: str, **kwargs):
        """Update node properties."""
        if NETWORKX_AVAILABLE:
            if node_id in self.graph.nodes:
                for k, v in kwargs.items():
                    self.graph.nodes[node_id][k] = v
        elif node_id in self.graph["nodes"]:
            self.graph["nodes"][node_id].update(kwargs)
    
    # ---- Edge Management ----
    
    def add_edge(self, 
                 src: str, 
                 dst: str, 
                 relation: str, 
                 metadata: Dict[str, Any] = None):
        """Add a relationship edge between nodes."""
        props = metadata or {}
        props['relation'] = relation
        
        if NETWORKX_AVAILABLE:
            self.graph.add_edge(src, dst, **props)
        else:
            self.graph["edges"].append({"src": src, "dst": dst, **props})
    
    def get_neighbors(self, node_id: str, relation: Optional[str] = None) -> List[str]:
        """Get neighboring node IDs."""
        if NETWORKX_AVAILABLE:
            neighbors = []
            for nbr in self.graph.successors(node_id):
                if relation:
                    edges = self.graph.get_edge_data(node_id, nbr)
                    if any(d.get('relation') == relation for d in edges.values()):
                        neighbors.append(nbr)
                else:
                    neighbors.append(nbr)
            return neighbors
        else:
            return [e['dst'] for e in self.graph["edges"] 
                    if e['src'] == node_id and (not relation or e.get('relation') == relation)]
    
    # ---- Semantic Search ----
    
    def semantic_search(self, 
                       query: str, 
                       top_k: int = 10,
                       kind_filter: Optional[List[str]] = None) -> List[Tuple[str, float, Dict]]:
        """
        Search nodes by semantic similarity.
        
        Returns:
            List of (node_id, similarity_score, node_data) tuples
        """
        if not self.model or not self.embeddings:
            return self._keyword_search(query, top_k)
        
        # Encode query
        query_vec = self.model.encode(query)
        
        # Compute similarities
        similarities = []
        for node_id, node_emb in self.embeddings.items():
            node_data = self.get_node(node_id)
            
            # Filter by kind
            if kind_filter and node_data and node_data.get('kind') not in kind_filter:
                continue
            
            # Cosine similarity
            if SKLEARN_AVAILABLE:
                sim = cosine_similarity([query_vec], [node_emb])[0][0]
            else:
                sim = np.dot(query_vec, node_emb) / (np.linalg.norm(query_vec) * np.linalg.norm(node_emb))
            
            similarities.append((node_id, float(sim), node_data))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def _keyword_search(self, query: str, top_k: int = 10) -> List[Tuple[str, float, Dict]]:
        """Fallback keyword search."""
        query_lower = query.lower()
        results = []
        
        nodes = self.graph.nodes if NETWORKX_AVAILABLE else self.graph["nodes"].items()
        
        for node_id, data in (nodes if NETWORKX_AVAILABLE else self.graph["nodes"].items()):
            text = data.get('text', '').lower()
            if query_lower in text:
                results.append((node_id, 1.0, data))
        
        return results[:top_k]
    
    # ---- Hybrid Search (Graph + Vector) ----
    
    def hybrid_search(self, 
                     query: str, 
                     top_k: int = 10,
                     semantic_weight: float = 0.7,
                     expand_graph: bool = True) -> List[Tuple[str, float, Dict]]:
        """
        Hybrid search combining semantic similarity and graph structure.
        
        Args:
            query: Search query
            top_k: Number of results
            semantic_weight: Weight for semantic score (0-1)
            expand_graph: Whether to expand results via graph traversal
        """
        # Get semantic results
        semantic_results = self.semantic_search(query, top_k=top_k * 2)
        semantic_scores = {nid: score for nid, score, _ in semantic_results}
        
        # Get graph-based results (neighbors of semantic matches)
        graph_scores = {}
        if expand_graph:
            for nid, score, _ in semantic_results:
                neighbors = self.get_neighbors(nid)
                for neighbor in neighbors:
                    graph_scores[neighbor] = graph_scores.get(neighbor, 0) + 0.5
        
        # Combine scores
        all_nodes = set(list(semantic_scores.keys()) + list(graph_scores.keys()))
        combined = []
        
        for nid in all_nodes:
            sem_score = semantic_scores.get(nid, 0)
            graph_score = graph_scores.get(nid, 0)
            combined_score = semantic_weight * sem_score + (1 - semantic_weight) * graph_score
            
            node_data = self.get_node(nid)
            combined.append((nid, combined_score, node_data))
        
        combined.sort(key=lambda x: x[1], reverse=True)
        return combined[:top_k]
    
    # ---- Graph Context ----
    
    def get_context(self, 
                   node_id: str, 
                   radius: int = 2,
                   kinds: Optional[List[str]] = None) -> List[Tuple[str, Dict]]:
        """Get neighborhood context around a node."""
        if not NETWORKX_AVAILABLE:
            return [(node_id, self.get_node(node_id))]
        
        try:
            paths = nx.single_source_shortest_path_length(self.graph, node_id, cutoff=radius)
            result = []
            for n in paths:
                node_data = self.get_node(n)
                if not kinds or (node_data and node_data.get('kind') in kinds):
                    result.append((n, node_data))
            return result
        except Exception:
            return [(node_id, self.get_node(node_id))]
    
    # ---- Bulk Operations ----
    
    def index_algorithms(self, algorithms_dir: str):
        """Index all algorithms from a directory."""
        algo_path = Path(algorithms_dir)
        
        if not algo_path.exists():
            print(f"Directory not found: {algorithms_dir}")
            return
        
        print(f"Indexing algorithms from {algorithms_dir}...")
        count = 0
        
        for py_file in algo_path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract docstring or first comment as description
                lines = content.split('\n')[:50]
                description = ' '.join(
                    line.strip().lstrip('#').strip() 
                    for line in lines 
                    if line.strip().startswith('#')
                ) or f"Algorithm: {py_file.stem}"
                
                node_id = f"algo_{py_file.stem}"
                self.add_node(
                    node_id=node_id,
                    kind='algorithm',
                    text=f"{py_file.stem} {description}",
                    metadata={'path': str(py_file), 'description': description}
                )
                count += 1
            except Exception as e:
                print(f"Error indexing {py_file}: {e}")
        
        print(f"Indexed {count} algorithms")
        self.save()
    
    # ---- Stats ----
    
    def count_nodes(self) -> int:
        if NETWORKX_AVAILABLE:
            return self.graph.number_of_nodes()
        return len(self.graph.get("nodes", {}))
    
    def count_edges(self) -> int:
        if NETWORKX_AVAILABLE:
            return self.graph.number_of_edges()
        return len(self.graph.get("edges", []))
    
    def health_check(self) -> Dict[str, Any]:
        """Check health of the NodeGraphRAG system."""
        return {
            "nodes": self.count_nodes(),
            "edges": self.count_edges(),
            "embeddings": len(self.embeddings),
            "model": self.embedding_model_name if self.model else None,
            "ok": self.count_nodes() > 0
        }


# ---- CLI ----
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='NodeGraphRAG - Semantic Vector + Knowledge Graph')
    parser.add_argument('command', choices=['search', 'hybrid', 'index', 'stats', 'context'])
    parser.add_argument('--query', help='Search query')
    parser.add_argument('--node', help='Node ID for context')
    parser.add_argument('--dir', help='Directory to index')
    parser.add_argument('--top-k', type=int, default=10)
    
    args = parser.parse_args()
    
    rag = NodeGraphRAG()
    
    if args.command == 'search':
        if not args.query:
            print("Error: --query required")
        else:
            print(f"\n🔍 Semantic Search: '{args.query}'")
            results = rag.semantic_search(args.query, top_k=args.top_k)
            for i, (nid, score, data) in enumerate(results, 1):
                print(f"{i}. [{data.get('kind', '?')}] {nid} - Score: {score:.3f}")
                print(f"   {data.get('text', '')[:100]}...")
    
    elif args.command == 'hybrid':
        if not args.query:
            print("Error: --query required")
        else:
            print(f"\n🔍 Hybrid Search: '{args.query}'")
            results = rag.hybrid_search(args.query, top_k=args.top_k)
            for i, (nid, score, data) in enumerate(results, 1):
                print(f"{i}. [{data.get('kind', '?')}] {nid} - Score: {score:.3f}")
    
    elif args.command == 'index':
        if not args.dir:
            print("Error: --dir required")
        else:
            rag.index_algorithms(args.dir)
    
    elif args.command == 'stats':
        stats = rag.health_check()
        print(f"\nNodeGraphRAG Stats:")
        for k, v in stats.items():
            print(f"  {k}: {v}")
    
    elif args.command == 'context':
        if not args.node:
            print("Error: --node required")
        else:
            print(f"\nContext for node: {args.node}")
            context = rag.get_context(args.node)
            for nid, data in context:
                print(f"  - {nid} [{data.get('kind', '?')}]")
