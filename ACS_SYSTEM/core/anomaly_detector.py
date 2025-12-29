import numpy as np
from typing import Dict, List, Any
from collections import deque
from datetime import datetime, timedelta


class AnomalyDetector:
    """Detect anomalies in system metrics"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.thresholds = config.get('thresholds', {})
        self.history = deque(maxlen=1000)
        self.baseline = {}
        self.learning_period = 100
        
    def detect(self, metrics: Dict[str, Any]) -> List[Dict]:
        """Detect anomalies in current metrics"""
        anomalies = []
        
        # Store in history
        self.history.append(metrics)
        
        # Update baseline
        if len(self.history) >= self.learning_period:
            self.update_baseline()
        
        # Static threshold checks
        anomalies.extend(self.check_static_thresholds(metrics))
        
        # Statistical anomalies
        if len(self.history) >= self.learning_period:
            anomalies.extend(self.check_statistical_anomalies(metrics))
        
        # Pattern-based detection
        anomalies.extend(self.check_patterns())
        
        return anomalies
    
    def check_static_thresholds(self, metrics: Dict) -> List[Dict]:
        """Check against configured thresholds"""
        anomalies = []
        
        # Memory threshold
        mem_percent = metrics['system']['memory']['percent']
        if mem_percent > self.thresholds.get('memory_critical', 90):
            anomalies.append({
                'type': 'memory_critical',
                'severity': 'critical',
                'value': mem_percent,
                'threshold': self.thresholds.get('memory_critical'),
                'action': 'memory_emergency_cleanup',
                'timestamp': metrics['timestamp']
            })
        elif mem_percent > self.thresholds.get('memory_warning', 80):
            anomalies.append({
                'type': 'memory_warning',
                'severity': 'warning',
                'value': mem_percent,
                'threshold': self.thresholds.get('memory_warning'),
                'action': 'memory_optimization',
                'timestamp': metrics['timestamp']
            })
        
        # CPU threshold
        cpu_avg = metrics['system']['cpu']['avg']
        if cpu_avg > self.thresholds.get('cpu_critical', 95):
            anomalies.append({
                'type': 'cpu_critical',
                'severity': 'critical',
                'value': cpu_avg,
                'action': 'identify_cpu_hog',
                'timestamp': metrics['timestamp']
            })
        
        # Disk threshold
        for mount, usage in metrics.get('disk', {}).items():
            if usage['percent'] > self.thresholds.get('disk_critical', 95):
                anomalies.append({
                    'type': 'disk_critical',
                    'severity': 'critical',
                    'mount': mount,
                    'value': usage['percent'],
                    'action': 'disk_cleanup',
                    'timestamp': metrics['timestamp']
                })
        
        return anomalies
    
    def check_statistical_anomalies(self, metrics: Dict) -> List[Dict]:
        """Detect statistical anomalies using baseline"""
        anomalies = []
        
        # Memory deviation
        current_mem = metrics['system']['memory']['percent']
        if 'memory_mean' in self.baseline:
            z_score = abs(current_mem - self.baseline['memory_mean']) / (self.baseline['memory_std'] + 1e-6)
            if z_score > 3:
                anomalies.append({
                    'type': 'memory_statistical_anomaly',
                    'severity': 'medium',
                    'value': current_mem,
                    'z_score': z_score,
                    'action': 'investigate_memory',
                    'timestamp': metrics['timestamp']
                })
        
        return anomalies
    
    def check_patterns(self) -> List[Dict]:
        """Detect problematic patterns in history"""
        anomalies = []
        
        if len(self.history) < 50:
            return anomalies
        
        # Memory leak detection
        if self.detect_memory_leak():
            anomalies.append({
                'type': 'memory_leak_pattern',
                'severity': 'high',
                'action': 'identify_leaking_process',
                'timestamp': datetime.now().isoformat()
            })
        
        # CPU thrashing detection
        if self.detect_cpu_thrashing():
            anomalies.append({
                'type': 'cpu_thrashing',
                'severity': 'high',
                'action': 'analyze_process_scheduling',
                'timestamp': datetime.now().isoformat()
            })
        
        return anomalies
    
    def detect_memory_leak(self) -> bool:
        """Detect memory leak pattern"""
        recent = list(self.history)[-50:]
        memory_values = [m['system']['memory']['percent'] for m in recent]
        
        # Check for consistent upward trend
        if len(memory_values) < 20:
            return False
        
        # Simple linear regression
        x = np.arange(len(memory_values))
        y = np.array(memory_values)
        
        slope = np.polyfit(x, y, 1)[0]
        
        # If memory is consistently increasing
        return slope > 0.5
    
    def detect_cpu_thrashing(self) -> bool:
        """Detect CPU thrashing pattern"""
        recent = list(self.history)[-30:]
        cpu_values = [m['system']['cpu']['avg'] for m in recent]
        
        # High variance + high average = thrashing
        if len(cpu_values) < 10:
            return False
        
        avg = np.mean(cpu_values)
        std = np.std(cpu_values)
        
        return avg > 70 and std > 20
    
    def update_baseline(self):
        """Update statistical baseline from history"""
        memory_values = [m['system']['memory']['percent'] for m in self.history]
        cpu_values = [m['system']['cpu']['avg'] for m in self.history]
        
        self.baseline = {
            'memory_mean': np.mean(memory_values),
            'memory_std': np.std(memory_values),
            'memory_p95': np.percentile(memory_values, 95),
            'cpu_mean': np.mean(cpu_values),
            'cpu_std': np.std(cpu_values),
            'cpu_p95': np.percentile(cpu_values, 95)
        }
