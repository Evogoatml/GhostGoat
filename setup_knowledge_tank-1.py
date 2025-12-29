#!/usr/bin/env python3
"""
GhostGoat Knowledge Tank Setup
Build complete backend information system from algorithm repository
"""

import os
import sys
from pathlib import Path

def check_dependencies():
    """Check if required packages are installed"""
    print("Checking dependencies...")
    
    required = {
        'paramiko': 'SSH connectivity',
        'sqlite3': 'Database (built-in)',
    }
    
    optional = {
        'sentence_transformers': 'Semantic search (optional but recommended)',
    }
    
    missing = []
    for package, desc in required.items():
        try:
            __import__(package)
            print(f"  ✓ {package} - {desc}")
        except ImportError:
            print(f"  ✗ {package} - {desc} MISSING")
            missing.append(package)
    
    print("\nOptional packages:")
    for package, desc in optional.items():
        try:
            __import__(package)
            print(f"  ✓ {package} - {desc}")
        except ImportError:
            print(f"  ⚠ {package} - {desc} (install for better search)")
    
    if missing:
        print(f"\n❌ Missing required packages: {', '.join(missing)}")
        print("Install with: pip install <package> --break-system-packages")
        return False
    
    return True

def setup_knowledge_tank(base_path: str, max_algorithms: int = None):
    """Build the knowledge tank"""
    print(f"\n=== Building Knowledge Tank ===")
    print(f"Base path: {base_path}")
    
    from knowledge_tank import AlgorithmScanner, KnowledgeTank
    
    # Step 1: Scan algorithms
    print("\nStep 1: Scanning algorithm repository...")
    scanner = AlgorithmScanner(base_path=f"{base_path}/algorithms")
    
    if not Path(f"{base_path}/algorithms").exists():
        print(f"❌ Algorithm directory not found: {base_path}/algorithms")
        return False
    
    algorithms = scanner.scan_directory(max_files=max_algorithms)
    
    if not algorithms:
        print("❌ No algorithms found!")
        return False
    
    print(f"✓ Scanned {len(algorithms)} algorithms")
    
    # Step 2: Build database
    print("\nStep 2: Building knowledge database...")
    tank = KnowledgeTank(db_path=f"{base_path}/knowledge_tank.db")
    tank.index_batch(algorithms)
    
    # Step 3: Show stats
    print("\nStep 3: Verifying database...")
    stats = tank.get_stats()
    print(f"✓ Database contains {stats['total_algorithms']} algorithms")
    
    print("\nTop 10 Categories:")
    for cat, count in sorted(stats['by_category'].items(), key=lambda x: -x[1])[:10]:
        print(f"  {cat}: {count}")
    
    return True

def build_semantic_layer(base_path: str, limit: int = None):
    """Build semantic search embeddings"""
    print(f"\n=== Building Semantic Search Layer ===")
    
    try:
        from semantic_tank import SemanticKnowledgeTank
        
        tank = SemanticKnowledgeTank(
            db_path=f"{base_path}/knowledge_tank.db",
            embeddings_path=f"{base_path}/embeddings.pkl"
        )
        
        tank.build_embeddings(limit=limit)
        print("✓ Semantic layer built successfully")
        return True
        
    except ImportError:
        print("⚠️  sentence-transformers not available")
        print("   Semantic search will not be available")
        print("   Install with: pip install sentence-transformers")
        return False

def test_system(base_path: str):
    """Test the knowledge tank system"""
    print(f"\n=== Testing Knowledge Tank ===")
    
    from knowledge_tank import KnowledgeTank
    
    tank = KnowledgeTank(db_path=f"{base_path}/knowledge_tank.db")
    
    # Test search
    print("\n1. Testing keyword search...")
    results = tank.search("encryption rsa", limit=3)
    print(f"   Found {len(results)} results for 'encryption rsa'")
    for r in results:
        print(f"     - {r['name']} ({r['category']})")
    
    # Test category retrieval
    print("\n2. Testing category retrieval...")
    results = tank.get_by_category("cryptography", limit=5)
    print(f"   Found {len(results)} cryptography algorithms")
    
    # Test semantic search if available
    try:
        from semantic_tank import SemanticKnowledgeTank
        
        print("\n3. Testing semantic search...")
        semantic = SemanticKnowledgeTank(
            db_path=f"{base_path}/knowledge_tank.db",
            embeddings_path=f"{base_path}/embeddings.pkl"
        )
        
        if semantic.algorithm_embeddings:
            results = semantic.semantic_search("find shortest path", top_k=3)
            print(f"   Found {len(results)} results for 'find shortest path'")
            for r in results:
                score = r.get('similarity_score', 0)
                print(f"     - {r['name']} (score: {score:.3f})")
        else:
            print("   ⚠️  Embeddings not built yet")
    except:
        print("   ⚠️  Semantic search not available")
    
    print("\n✓ All tests completed")

def main():
    """Main setup script"""
    print("╔═══════════════════════════════════════════╗")
    print("║   GhostGoat Knowledge Tank Setup         ║")
    print("║   Backend Information System              ║")
    print("╚═══════════════════════════════════════════╝\n")
    
    # Get base path
    if len(sys.argv) > 1:
        base_path = sys.argv[1]
    else:
        base_path = "/home/chewlo/GhostGoat"
    
    print(f"Using base path: {base_path}\n")
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Build knowledge tank
    print("\n" + "="*50)
    success = setup_knowledge_tank(base_path, max_algorithms=None)
    
    if not success:
        print("\n❌ Knowledge tank setup failed")
        sys.exit(1)
    
    # Build semantic layer
    print("\n" + "="*50)
    build_semantic = input("\nBuild semantic search layer? (recommended, takes time) [y/N]: ")
    
    if build_semantic.lower() == 'y':
        # Ask for limit
        limit_input = input("Limit algorithms for embeddings? (enter number or press Enter for all): ")
        limit = int(limit_input) if limit_input.strip() else None
        
        build_semantic_layer(base_path, limit=limit)
    
    # Test system
    print("\n" + "="*50)
    test_system(base_path)
    
    # Summary
    print("\n" + "="*50)
    print("\n🎉 Knowledge Tank Setup Complete!\n")
    print("Files created:")
    print(f"  • {base_path}/knowledge_tank.db - SQLite database")
    if build_semantic.lower() == 'y':
        print(f"  • {base_path}/embeddings.pkl - Semantic embeddings")
    
    print("\nNext steps:")
    print("  1. Test search: python semantic_tank.py search --query 'encryption'")
    print("  2. Explore categories: from knowledge_tank import KnowledgeTank")
    print("  3. Integrate with MoE: python smart_moe.py")
    print("\n✨ Your algorithm knowledge is now searchable!\n")

if __name__ == "__main__":
    main()
