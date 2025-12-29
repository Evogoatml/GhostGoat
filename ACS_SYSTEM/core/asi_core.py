import psutil
import subprocess
import ast
import inspect
from pathlib import Path
from typing import Dict, List, Any
import json
from datetime import datetime
import hashlib

class SelfModifyingDiagnostics:
    def __init__(self, nexus_root: Path):
        self.root = nexus_root
        self.metrics_db = {}
        self.optimization_history = []
        self.critical_thresholds = {
            'memory_percent': 85,
            'cpu_percent': 90,
            'disk_percent': 95,
            'process_count': 300
        }
        self.modification_rules = self.load_rules()
        
    def continuous_diagnostic_loop(self):
        """Real-time system monitoring with adaptive thresholds"""
        while True:
            metrics = self.collect_system_metrics()
            anomalies = self.detect_anomalies(metrics)
            
            if anomalies:
                self.execute_optimizations(anomalies)
                self.adapt_thresholds(metrics)
                self.modify_diagnostic_rules(anomalies)
            
            self.store_metrics(metrics)
            time.sleep(10)
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """Comprehensive system telemetry"""
        return {
            'timestamp': datetime.now().isoformat(),
            'cpu': {
                'percent': psutil.cpu_percent(interval=1, percpu=True),
                'freq': psutil.cpu_freq()._asdict(),
                'load_avg': psutil.getloadavg()
            },
            'memory': {
                'virtual': psutil.virtual_memory()._asdict(),
                'swap': psutil.swap_memory()._asdict()
            },
            'disk': {
                path: psutil.disk_usage(path)._asdict() 
                for path in ['/data', '/storage/emulated/0']
            },
            'network': psutil.net_io_counters()._asdict(),
            'processes': len(psutil.pids()),
            'nexus_specific': self.nexus_metrics()
        }
    
    def nexus_metrics(self) -> Dict[str, Any]:
        """Nexus EVO specific telemetry"""
        return {
            'chromadb_status': self.check_chromadb_health(),
            'alo_loop_count': self.get_alo_iterations(),
            'active_agents': self.count_active_agents(),
            'algorithm_cache_size': self.get_cache_metrics(),
            'last_error_count': self.scan_recent_errors()
        }
    
    def detect_anomalies(self, metrics: Dict) -> List[Dict]:
        """ML-based anomaly detection with adaptive learning"""
        anomalies = []
        
        # Static threshold checks
        if metrics['memory']['virtual']['percent'] > self.critical_thresholds['memory_percent']:
            anomalies.append({
                'type': 'memory_critical',
                'severity': 'high',
                'value': metrics['memory']['virtual']['percent'],
                'action': 'memory_cleanup'
            })
        
        # Pattern-based detection
        if self.is_memory_leak_pattern():
            anomalies.append({
                'type': 'memory_leak',
                'severity': 'critical',
                'action': 'restart_leaking_processes'
            })
        
        # ChromaDB specific
        if not metrics['nexus_specific']['chromadb_status']:
            anomalies.append({
                'type': 'chromadb_failure',
                'severity': 'critical',
                'action': 'reinitialize_chromadb'
            })
        
        return anomalies
    
    def execute_optimizations(self, anomalies: List[Dict]):
        """Self-executing optimization routines"""
        for anomaly in anomalies:
            action = anomaly['action']
            
            if action == 'memory_cleanup':
                self.optimize_memory()
            elif action == 'restart_leaking_processes':
                self.restart_processes_by_memory_pattern()
            elif action == 'reinitialize_chromadb':
                self.safe_chromadb_restart()
            elif action == 'optimize_codebase':
                self.auto_refactor_hotspots()
            
            self.log_optimization(anomaly, action)
    
    def optimize_memory(self):
        """Aggressive memory optimization"""
        # Clear Python caches
        import gc
        gc.collect()
        
        # Clear Nexus caches
        cache_dirs = [
            self.root / "__pycache__",
            self.root / ".chromadb",
            self.root / "logs" / "old"
        ]
        
        for cache_dir in cache_dirs:
            if cache_dir.exists():
                subprocess.run(['find', str(cache_dir), '-type', 'f', '-mtime', '+7', '-delete'])
        
        # Kill idle processes
        for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
            if proc.info['memory_percent'] > 10 and self.is_idle_process(proc):
                proc.kill()
    
    def modify_diagnostic_rules(self, anomalies: List[Dict]):
        """Self-modifying rule engine - rewrites own detection logic"""
        new_rule = self.generate_rule_from_anomalies(anomalies)
        
        if new_rule:
            # Inject new detection method into own class
            self.inject_detection_method(new_rule)
            
            # Persist rule changes
            self.save_modified_rules()
    
    def generate_rule_from_anomalies(self, anomalies: List[Dict]) -> Dict:
        """AI-generated detection rules based on patterns"""
        if len(anomalies) >= 3 and all(a['type'] == 'memory_critical' for a in anomalies):
            return {
                'name': f'memory_pattern_{datetime.now().timestamp()}',
                'condition': 'metrics["memory"]["virtual"]["percent"] > adaptive_threshold',
                'action': 'optimize_memory',
                'adaptive_threshold': self.calculate_adaptive_threshold(anomalies)
            }
        return None
    
    def inject_detection_method(self, rule: Dict):
        """Runtime code injection - modifies own detection capabilities"""
        method_code = f"""
def {rule['name']}(self, metrics):
    adaptive_threshold = {rule['adaptive_threshold']}
    if {rule['condition']}:
        return {{
            'type': '{rule['name']}',
            'severity': 'medium',
            'action': '{rule['action']}'
        }}
    return None
"""
        
        # Compile and inject
        exec_globals = {'self': self}
        exec(method_code, exec_globals)
        
        # Bind to instance
        setattr(self, rule['name'], exec_globals[rule['name']].__get__(self))
        
        # Register in detection pipeline
        self.modification_rules.append(rule['name'])
    
    def auto_refactor_hotspots(self):
        """Self-optimizing code refactoring"""
        # Profile code execution
        hotspots = self.profile_nexus_execution()
        
        for hotspot in hotspots:
            if hotspot['time_percent'] > 20:
                optimized_code = self.optimize_code_block(hotspot)
                self.apply_code_modification(hotspot['file'], optimized_code)
    
    def optimize_code_block(self, hotspot: Dict) -> str:
        """AST-based code optimization"""
        with open(hotspot['file'], 'r') as f:
            tree = ast.parse(f.read())
        
        # Apply optimization patterns
        optimizer = CodeOptimizer()
        optimized_tree = optimizer.visit(tree)
        
        return ast.unparse(optimized_tree)


class CodeOptimizer(ast.NodeTransformer):
    """AST transformer for runtime optimization"""
    
    def visit_For(self, node):
        """Convert inefficient loops to comprehensions"""
        if self.is_simple_append_loop(node):
            return self.convert_to_comprehension(node)
        return node
    
    def visit_FunctionDef(self, node):
        """Add memoization to pure functions"""
        if self.is_pure_function(node):
            return self.add_memoization(node)
        return node


class AdaptiveThresholdLearning:
    """ML-based threshold adaptation"""
    
    def __init__(self):
        self.history = []
        self.model = None
    
    def learn_optimal_thresholds(self, metrics_history: List[Dict]) -> Dict:
        """Adjust thresholds based on system behavior patterns"""
        import numpy as np
        
        # Simple statistical learning
        memory_values = [m['memory']['virtual']['percent'] for m in metrics_history]
        
        return {
            'memory_percent': np.percentile(memory_values, 95),
            'adaptive': True
        }
