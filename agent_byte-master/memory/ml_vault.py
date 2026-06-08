"""
ML/NLP Training Vault
Separate storage for machine learning datasets, models, and training resources
"""

import os
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib

@dataclass
class TrainingResource:
    """Metadata for ML/NLP training resource"""
    id: str
    name: str
    path: str
    resource_type: str  # dataset, model, notebook, script, config
    ml_task: str  # classification, regression, nlp, cv, etc.
    framework: Optional[str] = None  # tensorflow, pytorch, sklearn, etc.
    format: Optional[str] = None  # csv, json, pkl, h5, pt, etc.
    size: int = 0
    description: str = ""
    tags: List[str] = None
    requirements: List[str] = None
    dataset_info: Optional[Dict] = None  # rows, columns, classes, etc.
    model_info: Optional[Dict] = None  # architecture, params, etc.
    indexed_at: str = None
    
    def to_dict(self):
        data = asdict(self)
        # Convert lists/dicts to JSON strings
        if data['tags']:
            data['tags'] = json.dumps(data['tags'])
        if data['requirements']:
            data['requirements'] = json.dumps(data['requirements'])
        if data['dataset_info']:
            data['dataset_info'] = json.dumps(data['dataset_info'])
        if data['model_info']:
            data['model_info'] = json.dumps(data['model_info'])
        return data

class MLScanner:
    """Scans and categorizes ML/NLP resources"""
    
    ML_TASKS = {
        'classification': ['classification', 'classifier', 'categorical'],
        'regression': ['regression', 'predict', 'continuous'],
        'clustering': ['cluster', 'kmeans', 'dbscan'],
        'nlp': ['nlp', 'text', 'language', 'sentiment', 'tokeniz', 'embedding'],
        'cv': ['image', 'vision', 'cnn', 'detection', 'segmentation'],
        'timeseries': ['time series', 'forecast', 'lstm', 'rnn'],
        'reinforcement': ['rl', 'reinforcement', 'agent', 'policy'],
        'generative': ['gan', 'vae', 'generative'],
    }
    
    FRAMEWORKS = {
        'tensorflow': ['.h5', '.pb', 'tensorflow', 'keras'],
        'pytorch': ['.pt', '.pth', 'torch', 'pytorch'],
        'sklearn': ['sklearn', 'scikit'],
        'xgboost': ['xgb', 'xgboost'],
        'huggingface': ['transformers', 'bert', 'gpt'],
    }
    
    RESOURCE_TYPES = {
        'dataset': ['.csv', '.json', '.parquet', '.txt', '.tsv'],
        'model': ['.h5', '.pt', '.pth', '.pkl', '.joblib', '.pb'],
        'notebook': ['.ipynb'],
        'script': ['.py'],
        'config': ['.yaml', '.yml', '.json', '.toml'],
    }
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
    
    def scan_file(self, filepath: Path) -> Optional[TrainingResource]:
        """Scan single ML/NLP resource"""
        try:
            relative_path = filepath.relative_to(self.base_path)
            
            # Generate ID
            resource_id = hashlib.md5(str(relative_path).encode()).hexdigest()[:12]
            
            # Detect resource type
            resource_type = self._detect_resource_type(filepath)
            
            # Detect ML task
            ml_task = self._detect_ml_task(filepath)
            
            # Detect framework
            framework = self._detect_framework(filepath)
            
            # Get file stats
            stat = filepath.stat()
            
            # Extract description
            description = self._extract_description(filepath)
            
            # Detect tags
            tags = self._detect_tags(filepath, description)
            
            # Extract requirements
            requirements = self._extract_requirements(filepath)
            
            # Get dataset/model info
            dataset_info = None
            model_info = None
            
            if resource_type == 'dataset':
                dataset_info = self._analyze_dataset(filepath)
            elif resource_type == 'model':
                model_info = self._analyze_model(filepath)
            
            return TrainingResource(
                id=resource_id,
                name=filepath.stem,
                path=str(relative_path),
                resource_type=resource_type,
                ml_task=ml_task,
                framework=framework,
                format=filepath.suffix,
                size=stat.st_size,
                description=description,
                tags=tags,
                requirements=requirements,
                dataset_info=dataset_info,
                model_info=model_info,
                indexed_at=datetime.now().isoformat()
            )
        except Exception as e:
            print(f"Error scanning {filepath}: {e}")
            return None
    
    def _detect_resource_type(self, filepath: Path) -> str:
        """Detect resource type from file"""
        ext = filepath.suffix.lower()
        
        for rtype, exts in self.RESOURCE_TYPES.items():
            if ext in exts:
                return rtype
        
        return 'other'
    
    def _detect_ml_task(self, filepath: Path) -> str:
        """Detect ML task from filename and content"""
        text = str(filepath).lower()
        
        # Read first part of file if text
        if filepath.suffix in ['.py', '.ipynb', '.txt']:
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    text += " " + f.read(2000).lower()
            except:
                pass
        
        for task, keywords in self.ML_TASKS.items():
            if any(kw in text for kw in keywords):
                return task
        
        return 'general'
    
    def _detect_framework(self, filepath: Path) -> Optional[str]:
        """Detect ML framework"""
        text = str(filepath).lower()
        
        if filepath.suffix == '.py':
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(1000).lower()
                    text += " " + content
            except:
                pass
        
        for framework, indicators in self.FRAMEWORKS.items():
            if any(ind in text for ind in indicators):
                return framework
        
        return None
    
    def _extract_description(self, filepath: Path) -> str:
        """Extract description from file"""
        if filepath.suffix in ['.py', '.ipynb']:
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(3000)
                    
                    # Try docstring
                    import re
                    match = re.search(r'"""(.*?)"""', content, re.DOTALL)
                    if match:
                        return match.group(1).strip()[:500]
                    
                    # Try markdown cell in notebook
                    if filepath.suffix == '.ipynb':
                        data = json.loads(content) if content else {}
                        cells = data.get('cells', [])
                        for cell in cells[:3]:
                            if cell.get('cell_type') == 'markdown':
                                source = ''.join(cell.get('source', []))
                                if source:
                                    return source[:500]
            except:
                pass
        
        return filepath.stem.replace('_', ' ').title()
    
    def _detect_tags(self, filepath: Path, description: str) -> List[str]:
        """Detect tags"""
        tags = set()
        text = (str(filepath) + " " + description).lower()
        
        # Add ML task tags
        for task, keywords in self.ML_TASKS.items():
            if any(kw in text for kw in keywords):
                tags.add(task)
        
        # Add framework tags
        for framework, indicators in self.FRAMEWORKS.items():
            if any(ind in text for ind in indicators):
                tags.add(framework)
        
        # Add common ML tags
        ml_terms = ['supervised', 'unsupervised', 'deep_learning', 'neural_network',
                    'preprocessing', 'feature_engineering', 'evaluation']
        for term in ml_terms:
            if term.replace('_', ' ') in text or term in text:
                tags.add(term)
        
        return list(tags)
    
    def _extract_requirements(self, filepath: Path) -> List[str]:
        """Extract Python dependencies"""
        if filepath.suffix != '.py':
            return []
        
        deps = set()
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('import ') or line.startswith('from '):
                        import re
                        match = re.match(r'(?:from|import)\s+([a-zA-Z0-9_]+)', line)
                        if match:
                            module = match.group(1)
                            if module not in ['os', 'sys', 'time', 'json', 're']:
                                deps.add(module)
        except:
            pass
        
        return list(deps)
    
    def _analyze_dataset(self, filepath: Path) -> Optional[Dict]:
        """Analyze dataset file"""
        info = {}
        
        try:
            if filepath.suffix == '.csv':
                import csv
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.reader(f)
                    headers = next(reader)
                    row_count = sum(1 for _ in reader)
                    
                    info['columns'] = len(headers)
                    info['rows'] = row_count
                    info['headers'] = headers[:10]  # First 10 columns
            
            elif filepath.suffix == '.json':
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        info['rows'] = len(data)
                        if data:
                            info['keys'] = list(data[0].keys())[:10]
                    elif isinstance(data, dict):
                        info['keys'] = list(data.keys())[:10]
        except:
            pass
        
        return info if info else None
    
    def _analyze_model(self, filepath: Path) -> Optional[Dict]:
        """Analyze model file"""
        info = {}
        info['format'] = filepath.suffix
        
        # Try to get model size
        try:
            size_mb = filepath.stat().st_size / (1024 * 1024)
            info['size_mb'] = round(size_mb, 2)
        except:
            pass
        
        return info if info else None
    
    def scan_directory(self, max_files: Optional[int] = None) -> List[TrainingResource]:
        """Scan ML/NLP directory"""
        resources = []
        count = 0
        
        print(f"Scanning ML/NLP resources in {self.base_path}...")
        
        for root, dirs, files in os.walk(self.base_path):
            # Skip common non-ML directories
            dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'node_modules', '.ipynb_checkpoints']]
            
            for filename in files:
                if filename.startswith('.'):
                    continue
                
                filepath = Path(root) / filename
                
                resource = self.scan_file(filepath)
                if resource:
                    resources.append(resource)
                    count += 1
                    
                    if count % 50 == 0:
                        print(f"  Indexed {count} resources...")
                    
                    if max_files and count >= max_files:
                        print(f"Reached max files limit: {max_files}")
                        return resources
        
        print(f"✓ Scanned {count} ML/NLP resources")
        return resources

class MLVault:
    """Backend storage for ML/NLP training resources"""
    
    def __init__(self, db_path: str = "/home/chewlo/GhostGoat/ml_vault.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ml_resources (
                id TEXT PRIMARY KEY,
                name TEXT,
                path TEXT UNIQUE,
                resource_type TEXT,
                ml_task TEXT,
                framework TEXT,
                format TEXT,
                size INTEGER,
                description TEXT,
                tags TEXT,
                requirements TEXT,
                dataset_info TEXT,
                model_info TEXT,
                indexed_at TEXT
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_resource_type ON ml_resources(resource_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ml_task ON ml_resources(ml_task)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_framework ON ml_resources(framework)')
        
        # Full-text search
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS ml_resources_fts 
            USING fts5(name, description, tags, content=ml_resources)
        ''')
        
        conn.commit()
        conn.close()
        print(f"✓ ML Vault initialized: {self.db_path}")
    
    def index_resource(self, resource: TrainingResource):
        """Add resource to vault"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        data = resource.to_dict()
        
        cursor.execute('''
            INSERT OR REPLACE INTO ml_resources VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['id'], data['name'], data['path'], data['resource_type'],
            data['ml_task'], data['framework'], data['format'], data['size'],
            data['description'], data['tags'], data['requirements'],
            data['dataset_info'], data['model_info'], data['indexed_at']
        ))
        
        # Update FTS
        cursor.execute('''
            INSERT OR REPLACE INTO ml_resources_fts(rowid, name, description, tags)
            SELECT rowid, name, description, tags FROM ml_resources WHERE id = ?
        ''', (data['id'],))
        
        conn.commit()
        conn.close()
    
    def index_batch(self, resources: List[TrainingResource]):
        """Bulk index resources"""
        print(f"Indexing {len(resources)} ML/NLP resources...")
        
        for i, resource in enumerate(resources):
            self.index_resource(resource)
            if (i + 1) % 100 == 0:
                print(f"  Indexed {i + 1}/{len(resources)}")
        
        print(f"✓ Indexed {len(resources)} resources")
    
    def search(self, query: str, resource_type: Optional[str] = None,
               ml_task: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Search ML resources"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build query
        sql = '''
            SELECT r.* FROM ml_resources r
            JOIN ml_resources_fts fts ON r.rowid = fts.rowid
            WHERE fts MATCH ?
        '''
        params = [query]
        
        if resource_type:
            sql += ' AND r.resource_type = ?'
            params.append(resource_type)
        
        if ml_task:
            sql += ' AND r.ml_task = ?'
            params.append(ml_task)
        
        sql += ' LIMIT ?'
        params.append(limit)
        
        cursor.execute(sql, params)
        
        results = []
        for row in cursor.fetchall():
            results.append(self._row_to_dict(row))
        
        conn.close()
        return results
    
    def get_by_type(self, resource_type: str, limit: int = 100) -> List[Dict]:
        """Get all resources of a type"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM ml_resources WHERE resource_type = ? LIMIT ?
        ''', (resource_type, limit))
        
        results = [self._row_to_dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_by_task(self, ml_task: str, limit: int = 100) -> List[Dict]:
        """Get all resources for an ML task"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM ml_resources WHERE ml_task = ? LIMIT ?
        ''', (ml_task, limit))
        
        results = [self._row_to_dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_stats(self) -> Dict:
        """Get vault statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM ml_resources')
        total = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT resource_type, COUNT(*) 
            FROM ml_resources 
            GROUP BY resource_type
        ''')
        by_type = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute('''
            SELECT ml_task, COUNT(*) 
            FROM ml_resources 
            GROUP BY ml_task 
            ORDER BY COUNT(*) DESC
        ''')
        by_task = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute('''
            SELECT framework, COUNT(*) 
            FROM ml_resources 
            WHERE framework IS NOT NULL
            GROUP BY framework
        ''')
        by_framework = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            'total_resources': total,
            'by_type': by_type,
            'by_task': by_task,
            'by_framework': by_framework
        }
    
    def _row_to_dict(self, row) -> Dict:
        """Convert DB row to dictionary"""
        return {
            'id': row[0],
            'name': row[1],
            'path': row[2],
            'resource_type': row[3],
            'ml_task': row[4],
            'framework': row[5],
            'format': row[6],
            'size': row[7],
            'description': row[8],
            'tags': json.loads(row[9]) if row[9] else [],
            'requirements': json.loads(row[10]) if row[10] else [],
            'dataset_info': json.loads(row[11]) if row[11] else None,
            'model_info': json.loads(row[12]) if row[12] else None
        }

# Build ML Vault
if __name__ == "__main__":
    print("=== Building ML/NLP Training Vault ===\n")
    
    # Scan ML resources
    scanner = MLScanner("/home/chewlo/GhostGoat/algorithms/machine_learning")
    resources = scanner.scan_directory()
    
    # Index into vault
    vault = MLVault()
    vault.index_batch(resources)
    
    # Show stats
    print("\n=== ML Vault Stats ===")
    stats = vault.get_stats()
    print(f"Total Resources: {stats['total_resources']}")
    print("\nBy Type:", stats['by_type'])
    print("\nBy Task:", stats['by_task'])
    print("\nBy Framework:", stats['by_framework'])
    
    # Test search
    print("\n=== Testing Search ===")
    results = vault.search("classification")
    print(f"Found {len(results)} classification resources")
    
    print("\n✓ ML Vault ready!")
