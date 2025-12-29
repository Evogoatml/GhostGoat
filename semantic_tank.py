"""
Semantic Knowledge Tank with Vector Embeddings
Advanced algorithm retrieval using semantic similarity
"""

import numpy as np
from knowledge_tank import KnowledgeTank
from typing import List, Dict, Optional
import pickle
import os

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("⚠️  sentence-transformers not installed. Using basic search only.")
    print("   Install with: pip install sentence-transformers")

class SemanticKnowledgeTank:
    """Knowledge tank with semantic vector search"""
    
    def __init__(self, db_path: str = "/home/chewlo/GhostGoat/knowledge_tank.db",
                 embeddings_path: str = "/home/chewlo/GhostGoat/embeddings.pkl"):
        self.tank = KnowledgeTank(db_path)
        self.embeddings_path = embeddings_path
        self.model = None
        self.algorithm_embeddings = {}
        self.algorithm_index = {}
        
        if EMBEDDINGS_AVAILABLE:
            self._init_model()
            self._load_embeddings()
    
    def _init_model(self):
        """Initialize sentence transformer model"""
        print("Loading embedding model...")
        # Use lightweight model for mobile
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✓ Model loaded")
    
    def _load_embeddings(self):
        """Load pre-computed embeddings"""
        if os.path.exists(self.embeddings_path):
            print(f"Loading embeddings from {self.embeddings_path}")
            with open(self.embeddings_path, 'rb') as f:
                data = pickle.load(f)
                self.algorithm_embeddings = data['embeddings']
                self.algorithm_index = data['index']
            print(f"✓ Loaded {len(self.algorithm_embeddings)} embeddings")
    
    def build_embeddings(self, limit: Optional[int] = None):
        """Build embeddings for all algorithms"""
        if not EMBEDDINGS_AVAILABLE:
            print("❌ sentence-transformers not available")
            return
        
        print("Building algorithm embeddings...")
        
        # Get all algorithms
        stats = self.tank.get_stats()
        total = stats['total_algorithms']
        
        if limit:
            total = min(total, limit)
        
        # Get algorithms in batches
        import sqlite3
        conn = sqlite3.connect(self.tank.db_path)
        cursor = conn.cursor()
        
        if limit:
            cursor.execute('SELECT id, name, description, tags FROM algorithms LIMIT ?', (limit,))
        else:
            cursor.execute('SELECT id, name, description, tags FROM algorithms')
        
        algorithms = []
        texts = []
        
        for row in cursor.fetchall():
            algo_id = row[0]
            name = row[1]
            description = row[2] or ""
            tags = row[3] or ""
            
            # Combine for embedding
            text = f"{name} {description} {tags}"
            
            algorithms.append(algo_id)
            texts.append(text)
        
        conn.close()
        
        print(f"Computing embeddings for {len(texts)} algorithms...")
        
        # Compute embeddings in batches
        batch_size = 32
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            batch_embeddings = self.model.encode(batch)
            embeddings.extend(batch_embeddings)
            
            if (i + batch_size) % 320 == 0:
                print(f"  Processed {min(i+batch_size, len(texts))}/{len(texts)}")
        
        # Store embeddings
        self.algorithm_embeddings = {
            algo_id: emb for algo_id, emb in zip(algorithms, embeddings)
        }
        
        # Create ID to index mapping
        self.algorithm_index = {
            algo_id: i for i, algo_id in enumerate(algorithms)
        }
        
        # Save to disk
        with open(self.embeddings_path, 'wb') as f:
            pickle.dump({
                'embeddings': self.algorithm_embeddings,
                'index': self.algorithm_index
            }, f)
        
        print(f"✓ Built and saved {len(embeddings)} embeddings")
    
    def semantic_search(self, query: str, top_k: int = 10) -> List[Dict]:
        """Search using semantic similarity"""
        if not EMBEDDINGS_AVAILABLE or not self.algorithm_embeddings:
            print("⚠️  Falling back to keyword search")
            return self.tank.search(query, limit=top_k)
        
        # Encode query
        query_embedding = self.model.encode(query)
        
        # Compute similarities
        similarities = []
        for algo_id, emb in self.algorithm_embeddings.items():
            # Cosine similarity
            sim = np.dot(query_embedding, emb) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(emb)
            )
            similarities.append((algo_id, sim))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Get top results
        results = []
        for algo_id, score in similarities[:top_k]:
            algo = self.tank.get_by_id(algo_id)
            if algo:
                algo['similarity_score'] = float(score)
                results.append(algo)
        
        return results
    
    def hybrid_search(self, query: str, top_k: int = 10, 
                     semantic_weight: float = 0.7) -> List[Dict]:
        """Combine semantic and keyword search"""
        
        # Get semantic results
        semantic_results = self.semantic_search(query, top_k=top_k*2)
        
        # Get keyword results  
        keyword_results = self.tank.search(query, limit=top_k*2)
        
        # Merge and re-rank
        all_results = {}
        
        # Add semantic scores
        for i, result in enumerate(semantic_results):
            algo_id = result['id']
            semantic_score = result.get('similarity_score', 0)
            all_results[algo_id] = {
                'algo': result,
                'semantic_score': semantic_score,
                'keyword_score': 0,
                'rank': i
            }
        
        # Add keyword scores
        for i, result in enumerate(keyword_results):
            algo_id = result['id']
            keyword_score = 1.0 / (i + 1)  # Reciprocal rank
            
            if algo_id in all_results:
                all_results[algo_id]['keyword_score'] = keyword_score
            else:
                all_results[algo_id] = {
                    'algo': result,
                    'semantic_score': 0,
                    'keyword_score': keyword_score,
                    'rank': i
                }
        
        # Compute hybrid scores
        for algo_id, data in all_results.items():
            hybrid_score = (
                semantic_weight * data['semantic_score'] +
                (1 - semantic_weight) * data['keyword_score']
            )
            data['hybrid_score'] = hybrid_score
        
        # Sort by hybrid score
        ranked = sorted(all_results.values(), 
                       key=lambda x: x['hybrid_score'], 
                       reverse=True)
        
        return [r['algo'] for r in ranked[:top_k]]
    
    def find_similar_algorithms(self, algorithm_id: str, top_k: int = 5) -> List[Dict]:
        """Find algorithms similar to a given one"""
        if not EMBEDDINGS_AVAILABLE or algorithm_id not in self.algorithm_embeddings:
            return []
        
        target_emb = self.algorithm_embeddings[algorithm_id]
        
        similarities = []
        for algo_id, emb in self.algorithm_embeddings.items():
            if algo_id == algorithm_id:
                continue
            
            sim = np.dot(target_emb, emb) / (
                np.linalg.norm(target_emb) * np.linalg.norm(emb)
            )
            similarities.append((algo_id, sim))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for algo_id, score in similarities[:top_k]:
            algo = self.tank.get_by_id(algo_id)
            if algo:
                algo['similarity_score'] = float(score)
                results.append(algo)
        
        return results
    
    def smart_recommend(self, task_description: str, 
                       complexity: Optional[str] = None,
                       tags: Optional[List[str]] = None) -> List[Dict]:
        """Smart algorithm recommendation with filters"""
        
        # Get initial results
        results = self.hybrid_search(task_description, top_k=20)
        
        # Apply filters
        if complexity:
            results = [r for r in results if r.get('complexity') == complexity]
        
        if tags:
            results = [
                r for r in results 
                if any(tag in r.get('tags', []) for tag in tags)
            ]
        
        return results[:10]

# CLI for knowledge tank management
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Semantic Knowledge Tank')
    parser.add_argument('command', choices=['build', 'search', 'similar', 'stats'])
    parser.add_argument('--query', help='Search query')
    parser.add_argument('--algo-id', help='Algorithm ID for similarity search')
    parser.add_argument('--limit', type=int, default=10, help='Number of results')
    parser.add_argument('--build-limit', type=int, help='Limit algorithms for building')
    
    args = parser.parse_args()
    
    tank = SemanticKnowledgeTank()
    
    if args.command == 'build':
        tank.build_embeddings(limit=args.build_limit)
    
    elif args.command == 'search':
        if not args.query:
            print("Error: --query required")
        else:
            print(f"\n🔍 Semantic Search: '{args.query}'")
            results = tank.semantic_search(args.query, top_k=args.limit)
            
            for i, algo in enumerate(results, 1):
                score = algo.get('similarity_score', 0)
                print(f"{i}. {algo['name']} ({algo['category']}) - Score: {score:.3f}")
                print(f"   {algo['description'][:100]}...")
    
    elif args.command == 'similar':
        if not args.algo_id:
            print("Error: --algo-id required")
        else:
            print(f"\n🔗 Similar to algorithm: {args.algo_id}")
            results = tank.find_similar_algorithms(args.algo_id, top_k=args.limit)
            
            for i, algo in enumerate(results, 1):
                score = algo.get('similarity_score', 0)
                print(f"{i}. {algo['name']} - Score: {score:.3f}")
    
    elif args.command == 'stats':
        stats = tank.tank.get_stats()
        print(f"\nTotal Algorithms: {stats['total_algorithms']}")
        print(f"Embeddings Built: {len(tank.algorithm_embeddings)}")
        
        print("\nTop Categories:")
        for cat, count in sorted(stats['by_category'].items(), key=lambda x: -x[1])[:10]:
            print(f"  {cat}: {count}")
