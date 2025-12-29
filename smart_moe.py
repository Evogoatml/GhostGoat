"""
MoE Knowledge Tank Integration
Agents query the knowledge base instead of using hardcoded paths
"""

from knowledge_tank import KnowledgeTank
from typing import List, Dict, Optional
import re

# Optional MoE system import
try:
    from moe_system import GhostGoatMoE, ExpertDomain
    HAS_MOE_SYSTEM = True
except ImportError:
    HAS_MOE_SYSTEM = False
    # Create stub classes
    class ExpertDomain:
        CRYPTOGRAPHY = "cryptography"
        MACHINE_LEARNING = "machine_learning"
        GRAPHS = "graphs"
        GENERAL = "general"
    
    class GhostGoatMoE:
        def __init__(self, base_path):
            self.base_path = base_path
            self.experts = {}
        
        def initialize_experts(self):
            pass
        
        def run_task(self, description, algorithm_path, params=None, domain=None):
            return {'success': False, 'error': 'MoE system not available'}
        
        def get_stats(self):
            return {}
        
        def shutdown(self):
            pass

class SmartMoE(GhostGoatMoE):
    """MoE system with Knowledge Tank integration"""
    
    def __init__(self, base_path="/home/chewlo/GhostGoat"):
        super().__init__(base_path)
        try:
            self.knowledge = KnowledgeTank()
            print("✓ Knowledge Tank connected")
        except Exception as e:
            print(f"⚠️  Knowledge Tank initialization failed: {e}")
            self.knowledge = None
    
    def find_algorithm(self, query: str, category: Optional[str] = None) -> Optional[Dict]:
        """Find best matching algorithm from knowledge tank"""
        if not self.knowledge:
            return None
        results = self.knowledge.search(query, category=category, limit=5)
        
        if not results:
            return None
        
        # Return top result
        return results[0]
    
    def run_natural_task(self, natural_language_query: str, params: Optional[Dict] = None) -> Dict:
        """
        Execute algorithm using natural language query
        Example: "encrypt data with RSA"
        """
        print(f"\n🔍 Searching for: {natural_language_query}")
        
        # Detect domain from query
        domain = self._detect_domain_from_query(natural_language_query)
        
        # Find matching algorithm
        algo = self.find_algorithm(natural_language_query, category=domain)
        
        if not algo:
            return {
                'success': False,
                'error': f"No algorithm found for: {natural_language_query}"
            }
        
        print(f"✓ Found: {algo['name']} ({algo['category']})")
        print(f"  Path: {algo['path']}")
        
        # Execute it
        domain = None
        if HAS_MOE_SYSTEM:
            try:
                # Try to map category to ExpertDomain enum
                category_upper = algo['category'].upper()
                if hasattr(ExpertDomain, category_upper):
                    domain = getattr(ExpertDomain, category_upper)
            except:
                pass
        
        result = self.run_task(
            description=natural_language_query,
            algorithm_path=f"algorithms/{algo['path']}",
            params=params or {},
            domain=domain
        )
        
        result['algorithm_used'] = algo
        return result
    
    def _detect_domain_from_query(self, query: str) -> Optional[str]:
        """Detect algorithm category from natural language"""
        query_lower = query.lower()
        
        keywords = {
            'cryptography': ['encrypt', 'decrypt', 'cipher', 'rsa', 'aes', 'crypto'],
            'graphs': ['graph', 'path', 'dijkstra', 'traverse', 'bfs', 'dfs'],
            'machine_learning': ['train', 'model', 'predict', 'classify', 'ml'],
            'sorting': ['sort', 'order', 'arrange'],
            'mathematics': ['calculate', 'compute', 'prime', 'factorial'],
            'hashing': ['hash', 'md5', 'sha'],
        }
        
        for category, kws in keywords.items():
            if any(kw in query_lower for kw in kws):
                return category
        
        return None
    
    def suggest_algorithms(self, task_description: str, limit: int = 5) -> List[Dict]:
        """Get algorithm suggestions for a task"""
        if not self.knowledge:
            return []
        results = self.knowledge.search(task_description, limit=limit)
        
        print(f"\n💡 Suggestions for '{task_description}':")
        for i, algo in enumerate(results, 1):
            print(f"{i}. {algo['name']} ({algo['category']})")
            print(f"   {algo['description'][:100]}...")
        
        return results
    
    def get_category_algorithms(self, category: str) -> List[Dict]:
        """Get all algorithms in a category"""
        if not self.knowledge:
            return []
        return self.knowledge.get_by_category(category)
    
    def batch_natural_tasks(self, queries: List[str]) -> List[Dict]:
        """Execute multiple natural language tasks"""
        results = []
        
        for query in queries:
            result = self.run_natural_task(query)
            results.append(result)
        
        return results

class KnowledgeExplorer:
    """Interactive knowledge tank exploration"""
    
    def __init__(self, tank: KnowledgeTank):
        self.tank = tank
    
    def explore_category(self, category: str):
        """Explore algorithms in a category"""
        algorithms = self.tank.get_by_category(category, limit=50)
        
        print(f"\n📁 {category.upper()} Algorithms ({len(algorithms)} total):")
        
        # Group by subcategory
        by_subcat = {}
        for algo in algorithms:
            subcat = algo['subcategory']
            if subcat not in by_subcat:
                by_subcat[subcat] = []
            by_subcat[subcat].append(algo)
        
        for subcat, algos in sorted(by_subcat.items()):
            print(f"\n  {subcat}:")
            for algo in algos[:10]:  # Show first 10
                print(f"    • {algo['name']}")
    
    def find_related(self, algorithm_name: str) -> List[Dict]:
        """Find algorithms related to a given one"""
        # Search by algorithm name
        results = self.tank.search(algorithm_name, limit=10)
        
        if not results:
            print(f"No results for: {algorithm_name}")
            return []
        
        print(f"\n🔗 Related to '{algorithm_name}':")
        for algo in results:
            tags_str = ', '.join(algo['tags'][:3])
            print(f"  • {algo['name']} ({tags_str})")
        
        return results
    
    def show_stats(self):
        """Show knowledge tank statistics"""
        stats = self.tank.get_stats()
        
        print("\n📊 Knowledge Tank Statistics")
        print(f"Total Algorithms: {stats['total_algorithms']}")
        
        print("\nTop Categories:")
        for cat, count in sorted(stats['by_category'].items(), key=lambda x: -x[1])[:15]:
            bar = '█' * (count // 100)
            print(f"  {cat:25} {count:5} {bar}")
        
        print("\nFile Types:")
        for ft, count in stats['by_file_type'].items():
            print(f"  {ft}: {count}")

# Example usage
if __name__ == "__main__":
    print("=== Smart MoE with Knowledge Tank ===\n")
    
    # Initialize
    moe = SmartMoE()
    moe.initialize_experts()
    
    # Natural language queries
    print("\n1. Natural Language Execution:")
    
    result = moe.run_natural_task("encrypt message with RSA")
    print(f"Result: {result.get('success')}")
    
    result = moe.run_natural_task("find shortest path in graph")
    print(f"Result: {result.get('success')}")
    
    result = moe.run_natural_task("calculate fibonacci sequence")
    print(f"Result: {result.get('success')}")
    
    # Get suggestions
    print("\n2. Algorithm Suggestions:")
    suggestions = moe.suggest_algorithms("sort a list of numbers")
    
    # Explore knowledge
    print("\n3. Knowledge Exploration:")
    explorer = KnowledgeExplorer(moe.knowledge)
    explorer.explore_category("cryptography")
    explorer.show_stats()
    
    # Batch execution
    print("\n4. Batch Natural Tasks:")
    tasks = [
        "hash data with SHA1",
        "binary search in array",
        "calculate GCD of two numbers"
    ]
    results = moe.batch_natural_tasks(tasks)
    
    for i, result in enumerate(results):
        status = "✓" if result.get('success') else "✗"
        print(f"{status} Task {i+1}: {result.get('algorithm_used', {}).get('name', 'N/A')}")
    
    # Stats
    moe.get_stats()
    moe.shutdown()
