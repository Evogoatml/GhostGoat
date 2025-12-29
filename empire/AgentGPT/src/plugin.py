"""
ADAP Integration System - Plugin Generator
Generates ADAP-compatible plugin wrappers for algorithms
"""

import os
import ast
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import textwrap
from datetime import datetime

class PluginGenerator:
    """Generate ADAP plugin wrappers for algorithms"""
    
    def __init__(self, config: dict):
        self.config = config
        self.plugins_config = config['plugins']
        self.storage = config['storage']
        
        # Load template if specified
        self.template = self._load_template()
    
    def generate_plugin(self, algo_name: str, category: str, 
                       algo_path: str, functions: List[Dict], 
                       classes: List[Dict]) -> str:
        """Generate a plugin wrapper for an algorithm"""
        # Create plugin directory
        plugin_dir = Path(self.storage['plugins_path']) / category
        plugin_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate plugin code
        plugin_code = self._generate_plugin_code(
            algo_name, category, algo_path, functions, classes
        )
        
        # Validate generated code
        if self.plugins_config['validate_imports']:
            if not self._validate_plugin_code(plugin_code):
                raise ValueError(f"Generated plugin code for {algo_name} failed validation")
        
        # Save plugin
        plugin_filename = f"adap_{algo_name}_plugin.py"
        plugin_path = plugin_dir / plugin_filename
        
        with open(plugin_path, 'w') as f:
            f.write(plugin_code)
        
        # Generate tests if enabled
        if self.plugins_config['add_tests']:
            test_code = self._generate_test_code(algo_name, category)
            test_path = plugin_dir / f"test_{plugin_filename}"
            
            with open(test_path, 'w') as f:
                f.write(test_code)
        
        return str(plugin_path)
    
    def _load_template(self) -> str:
        """Load plugin template"""
        template_path = self.plugins_config.get('template_path')
        
        if template_path and os.path.exists(template_path):
            with open(template_path, 'r') as f:
                return f.read()
        
        # Default template
        return '''"""
ADAP Plugin: {name}
Category: {category}
Generated: {timestamp}
"""

import sys
import os
import json
import importlib.util
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
import functools
import time

# Plugin metadata
PLUGIN_INFO = {{
    "name": "{name}",
    "category": "{category}",
    "version": "1.0.0",
    "algorithm_path": "{algo_path}",
    "generated_at": "{timestamp}",
    "capabilities": {capabilities}
}}

class {plugin_class}:
    """ADAP Plugin wrapper for {name}"""
    
    # Plugin interface constants
    PLUGIN_TYPE = "{category}"
    PLUGIN_NAME = "{name}"
    PLUGIN_VERSION = "1.0.0"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize plugin with optional configuration"""
        self.config = config or {{}}
        self.algorithm_module = None
        self._cache = {{}}
        self._performance_metrics = {{}}
        
        # Load the algorithm module
        self._load_algorithm()
        
        # Discover available operations
        self.operations = self._discover_operations()
    
    def _load_algorithm(self):
        """Dynamically load the algorithm module"""
        algo_path = Path("{algo_path}")
        
        if not algo_path.exists():
            raise FileNotFoundError(f"Algorithm file not found: {{algo_path}}")
        
        # Load module
        spec = importlib.util.spec_from_file_location("{name}", str(algo_path))
        self.algorithm_module = importlib.util.module_from_spec(spec)
        
        # Add parent directory to sys.path if needed
        parent_dir = str(algo_path.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        spec.loader.exec_module(self.algorithm_module)
    
    def _discover_operations(self) -> Dict[str, Callable]:
        """Discover available operations in the algorithm module"""
        operations = {{}}
        
        # Functions
        {function_discovery}
        
        # Classes
        {class_discovery}
        
        return operations
    
    def execute(self, operation: str, *args, **kwargs) -> Any:
        """Execute a specific operation"""
        if operation not in self.operations:
            available = ", ".join(self.operations.keys())
            raise ValueError(f"Unknown operation '{{operation}}'. Available: {{available}}")
        
        # Performance tracking
        start_time = time.time()
        
        try:
            # Check cache if enabled
            cache_key = self._get_cache_key(operation, args, kwargs)
            if self.config.get('use_cache') and cache_key in self._cache:
                return self._cache[cache_key]
            
            # Execute operation
            result = self.operations[operation](*args, **kwargs)
            
            # Cache result if enabled
            if self.config.get('use_cache'):
                self._cache[cache_key] = result
            
            return result
            
        finally:
            # Track performance
            elapsed = time.time() - start_time
            self._track_performance(operation, elapsed)
    
    def validate_input(self, operation: str, *args, **kwargs) -> bool:
        """Validate input for an operation"""
        # Add operation-specific validation
        validators = {{
            {validators}
        }}
        
        if operation in validators:
            return validators[operation](*args, **kwargs)
        
        return True  # Default: accept all inputs
    
    def get_info(self) -> Dict[str, Any]:
        """Get plugin information"""
        info = PLUGIN_INFO.copy()
        info.update({{
            "operations": list(self.operations.keys()),
            "performance": self._performance_metrics,
            "cache_size": len(self._cache)
        }})
        return info
    
    def benchmark(self, test_data: List[Any], operation: str = None) -> Dict[str, float]:
        """Benchmark plugin performance"""
        results = {{}}
        
        operations_to_test = [operation] if operation else list(self.operations.keys())
        
        for op in operations_to_test:
            if op not in self.operations:
                continue
            
            times = []
            errors = 0
            
            for data in test_data:
                try:
                    start = time.time()
                    if isinstance(data, dict):
                        self.execute(op, **data)
                    elif isinstance(data, (list, tuple)):
                        self.execute(op, *data)
                    else:
                        self.execute(op, data)
                    times.append(time.time() - start)
                except Exception:
                    errors += 1
            
            if times:
                results[op] = {{
                    'avg_time': sum(times) / len(times),
                    'min_time': min(times),
                    'max_time': max(times),
                    'total_runs': len(test_data),
                    'errors': errors
                }}
        
        return results
    
    def reset_cache(self):
        """Clear the cache"""
        self._cache.clear()
    
    def _get_cache_key(self, operation: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key for operation"""
        key_data = {{
            'op': operation,
            'args': args,
            'kwargs': kwargs
        }}
        return json.dumps(key_data, sort_keys=True)
    
    def _track_performance(self, operation: str, elapsed: float):
        """Track performance metrics"""
        if operation not in self._performance_metrics:
            self._performance_metrics[operation] = {{
                'count': 0,
                'total_time': 0,
                'avg_time': 0,
                'min_time': float('inf'),
                'max_time': 0
            }}
        
        metrics = self._performance_metrics[operation]
        metrics['count'] += 1
        metrics['total_time'] += elapsed
        metrics['avg_time'] = metrics['total_time'] / metrics['count']
        metrics['min_time'] = min(metrics['min_time'], elapsed)
        metrics['max_time'] = max(metrics['max_time'], elapsed)

# Plugin registration
def register():
    """Register plugin with ADAP system"""
    return {plugin_class}()

# Main guard for testing
if __name__ == "__main__":
    # Test plugin
    plugin = {plugin_class}()
    
    print(f"Plugin: {{plugin.PLUGIN_NAME}}")
    print(f"Category: {{plugin.PLUGIN_TYPE}}")
    print(f"Operations: {{list(plugin.operations.keys())}}")
    
    # Example usage
    {example_usage}
'''
    
    def _generate_plugin_code(self, algo_name: str, category: str, 
                             algo_path: str, functions: List[Dict], 
                             classes: List[Dict]) -> str:
        """Generate plugin code from template"""
        # Generate plugin class name
        plugin_class = f"ADAP{algo_name.title().replace('_', '')}Plugin"
        
        # Generate capabilities list
        capabilities = []
        for func in functions:
            capabilities.append(func['name'])
        for cls in classes:
            capabilities.append(cls['name'])
        
        # Generate function discovery code
        function_discovery = self._generate_function_discovery(functions)
        
        # Generate class discovery code
        class_discovery = self._generate_class_discovery(classes)
        
        # Generate validators
        validators = self._generate_validators(functions, classes)
        
        # Generate example usage
        example_usage = self._generate_example_usage(functions, classes)
        
        # Fill template
        code = self.template.format(
            name=algo_name,
            category=category,
            algo_path=algo_path,
            plugin_class=plugin_class,
            timestamp=datetime.now().isoformat(),
            capabilities=json.dumps(capabilities),
            function_discovery=function_discovery,
            class_discovery=class_discovery,
            validators=validators,
            example_usage=example_usage
        )
        
        return code
    
    def _generate_function_discovery(self, functions: List[Dict]) -> str:
        """Generate code to discover functions"""
        if not functions:
            return "# No functions to discover"
        
        lines = []
        for func in functions:
            name = func['name']
            lines.append(f"if hasattr(self.algorithm_module, '{name}'):")
            lines.append(f"    operations['{name}'] = getattr(self.algorithm_module, '{name}')")
        
        return '\n        '.join(lines)
    
    def _generate_class_discovery(self, classes: List[Dict]) -> str:
        """Generate code to discover classes"""
        if not classes:
            return "# No classes to discover"
        
        lines = []
        for cls in classes:
            name = cls['name']
            lines.append(f"if hasattr(self.algorithm_module, '{name}'):")
            lines.append(f"    cls = getattr(self.algorithm_module, '{name}')")
            lines.append(f"    operations['{name}'] = cls")
            
            # Add methods
            for method in cls.get('methods', []):
                if method['name'] not in ['__init__', '__str__', '__repr__']:
                    lines.append(f"    # Method: {method['name']}")
        
        return '\n        '.join(lines)
    
    def _generate_validators(self, functions: List[Dict], classes: List[Dict]) -> str:
        """Generate input validators"""
        validators = []
        
        # Function validators
        for func in functions:
            name = func['name']
            args = func.get('args', [])
            
            if 'array' in name or 'list' in name:
                validators.append(f'"{name}": lambda *args, **kwargs: isinstance(args[0] if args else kwargs.get("data"), (list, tuple))')
            elif 'graph' in name:
                validators.append(f'"{name}": lambda *args, **kwargs: isinstance(args[0] if args else kwargs.get("graph"), dict)')
        
        if not validators:
            return '"default": lambda *args, **kwargs: True'
        
        return ',\n            '.join(validators)
    
    def _generate_example_usage(self, functions: List[Dict], classes: List[Dict]) -> str:
        """Generate example usage code"""
        examples = []
        
        if functions:
            func = functions[0]
            name = func['name']
            
            if 'sort' in name:
                examples.append(f'# Example: {name}')
                examples.append('test_data = [3, 1, 4, 1, 5, 9, 2, 6]')
                examples.append(f'result = plugin.execute("{name}", test_data)')
                examples.append('print(f"Result: {result}")')
            elif 'search' in name:
                examples.append(f'# Example: {name}')
                examples.append('test_data = [1, 2, 3, 4, 5]')
                examples.append('target = 3')
                examples.append(f'result = plugin.execute("{name}", test_data, target)')
                examples.append('print(f"Result: {result}")')
            else:
                examples.append('# Add your test code here')
                examples.append('pass')
        else:
            examples.append('# No operations found for testing')
            examples.append('pass')
        
        return '\n    '.join(examples)
    
    def _generate_test_code(self, algo_name: str, category: str) -> str:
        """Generate test code for plugin"""
        test_template = '''"""
Tests for ADAP {name} Plugin
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from adap_{name}_plugin import {plugin_class}, register

class Test{plugin_class}(unittest.TestCase):
    """Test cases for {name} plugin"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.plugin = register()
    
    def test_plugin_info(self):
        """Test plugin information"""
        info = self.plugin.get_info()
        self.assertEqual(info['name'], '{name}')
        self.assertEqual(info['category'], '{category}')
        self.assertIn('operations', info)
    
    def test_operations_discovery(self):
        """Test that operations are discovered"""
        self.assertGreater(len(self.plugin.operations), 0)
        print(f"Discovered operations: {{list(self.plugin.operations.keys())}}")
    
    def test_execute_invalid_operation(self):
        """Test executing invalid operation"""
        with self.assertRaises(ValueError):
            self.plugin.execute('invalid_operation')
    
    # Add more specific tests based on the algorithm
    
if __name__ == '__main__':
    unittest.main()
'''
        
        plugin_class = f"ADAP{algo_name.title().replace('_', '')}Plugin"
        
        return test_template.format(
            name=algo_name,
            category=category,
            plugin_class=plugin_class
        )
    
    def _validate_plugin_code(self, code: str) -> bool:
        """Validate plugin code"""
        try:
            # Parse code to check syntax
            ast.parse(code)
            
            # Check for forbidden imports if security is enabled
            if self.config['security']['enable_sandboxing']:
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name in self.config['security']['forbidden_imports']:
                                return False
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and node.module in self.config['security']['forbidden_imports']:
                            return False
            
            return True
            
        except SyntaxError:
            return False
