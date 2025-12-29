"""
ADAP Integration System - System Monitor
Monitors system performance and health metrics
"""

import os
import psutil
import time
from datetime import datetime
from typing import Dict, Any
import json
from prometheus_client import Counter, Histogram, Gauge, Summary

class SystemMonitor:
    """Monitor system performance and integration metrics"""
    
    def __init__(self, config: dict):
        self.config = config
        self.monitoring_config = config['monitoring']
        
        # Initialize Prometheus metrics
        self.metrics = self._init_metrics()
        
        # Performance history
        self.performance_history = []
        self.max_history_size = 1000
    
    def _init_metrics(self) -> Dict[str, Any]:
        """Initialize Prometheus metrics"""
        return {
            # Counters
            'repos_cloned': Counter('adap_repos_cloned_total', 'Total repositories cloned'),
            'algorithms_discovered': Counter('adap_algorithms_discovered_total', 'Total algorithms discovered'),
            'algorithms_integrated': Counter('adap_algorithms_integrated_total', 'Total algorithms integrated'),
            'plugins_generated': Counter('adap_plugins_generated_total', 'Total plugins generated'),
            'errors': Counter('adap_errors_total', 'Total errors', ['error_type']),
            
            # Gauges
            'active_jobs': Gauge('adap_active_jobs', 'Number of active integration jobs'),
            'cpu_usage': Gauge('adap_cpu_usage_percent', 'CPU usage percentage'),
            'memory_usage': Gauge('adap_memory_usage_percent', 'Memory usage percentage'),
            'disk_usage': Gauge('adap_disk_usage_percent', 'Disk usage percentage'),
            
            # Histograms
            'clone_duration': Histogram('adap_clone_duration_seconds', 'Repository clone duration'),
            'analysis_duration': Histogram('adap_analysis_duration_seconds', 'Analysis duration'),
            'integration_duration': Histogram('adap_integration_duration_seconds', 'Integration duration'),
            
            # Summary
            'algorithm_complexity': Summary('adap_algorithm_complexity', 'Algorithm complexity scores')
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Process metrics
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info()
        
        # Network metrics (if available)
        net_io = psutil.net_io_counters()
        
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'system': {
                'cpu_percent': cpu_percent,
                'cpu_count': psutil.cpu_count(),
                'memory': {
                    'percent': memory.percent,
                    'used': memory.used,
                    'available': memory.available,
                    'total': memory.total
                },
                'disk': {
                    'percent': disk.percent,
                    'used': disk.used,
                    'free': disk.free,
                    'total': disk.total
                },
                'network': {
                    'bytes_sent': net_io.bytes_sent,
                    'bytes_recv': net_io.bytes_recv,
                    'packets_sent': net_io.packets_sent,
                    'packets_recv': net_io.packets_recv
                }
            },
            'process': {
                'memory_rss': process_memory.rss,
                'memory_vms': process_memory.vms,
                'cpu_percent': process.cpu_percent(),
                'num_threads': process.num_threads(),
                'open_files': len(process.open_files())
            }
        }
        
        # Update Prometheus metrics
        self.metrics['cpu_usage'].set(cpu_percent)
        self.metrics['memory_usage'].set(memory.percent)
        self.metrics['disk_usage'].set(disk.percent)
        
        # Store in history
        self._update_history(metrics)
        
        return metrics
    
    def record_job_start(self, job_id: int):
        """Record job start"""
        self.metrics['active_jobs'].inc()
    
    def record_job_complete(self, job_id: int, algorithms_found: int, 
                           algorithms_integrated: int, duration: float):
        """Record job completion"""
        self.metrics['active_jobs'].dec()
        self.metrics['algorithms_discovered'].inc(algorithms_found)
        self.metrics['algorithms_integrated'].inc(algorithms_integrated)
        self.metrics['integration_duration'].observe(duration)
    
    def record_clone_duration(self, duration: float):
        """Record repository clone duration"""
        self.metrics['repos_cloned'].inc()
        self.metrics['clone_duration'].observe(duration)
    
    def record_analysis_duration(self, duration: float):
        """Record analysis duration"""
        self.metrics['analysis_duration'].observe(duration)
    
    def record_plugin_generation(self):
        """Record plugin generation"""
        self.metrics['plugins_generated'].inc()
    
    def record_error(self, error_type: str):
        """Record error occurrence"""
        self.metrics['errors'].labels(error_type=error_type).inc()
    
    def record_algorithm_complexity(self, complexity: float):
        """Record algorithm complexity"""
        self.metrics['algorithm_complexity'].observe(complexity)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        if not self.performance_history:
            return {}
        
        # Calculate averages over history
        cpu_values = [m['system']['cpu_percent'] for m in self.performance_history]
        memory_values = [m['system']['memory']['percent'] for m in self.performance_history]
        
        return {
            'cpu': {
                'current': cpu_values[-1] if cpu_values else 0,
                'average': sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                'max': max(cpu_values) if cpu_values else 0,
                'min': min(cpu_values) if cpu_values else 0
            },
            'memory': {
                'current': memory_values[-1] if memory_values else 0,
                'average': sum(memory_values) / len(memory_values) if memory_values else 0,
                'max': max(memory_values) if memory_values else 0,
                'min': min(memory_values) if memory_values else 0
            },
            'history_size': len(self.performance_history)
        }
    
    def check_health(self) -> Dict[str, Any]:
        """Check system health"""
        metrics = self.get_metrics()
        
        health = {
            'status': 'healthy',
            'checks': {
                'cpu': 'ok',
                'memory': 'ok',
                'disk': 'ok'
            },
            'warnings': []
        }
        
        # Check CPU
        if metrics['system']['cpu_percent'] > 80:
            health['checks']['cpu'] = 'warning'
            health['warnings'].append('High CPU usage')
        elif metrics['system']['cpu_percent'] > 90:
            health['checks']['cpu'] = 'critical'
            health['status'] = 'degraded'
        
        # Check memory
        if metrics['system']['memory']['percent'] > 80:
            health['checks']['memory'] = 'warning'
            health['warnings'].append('High memory usage')
        elif metrics['system']['memory']['percent'] > 90:
            health['checks']['memory'] = 'critical'
            health['status'] = 'unhealthy'
        
        # Check disk
        if metrics['system']['disk']['percent'] > 80:
            health['checks']['disk'] = 'warning'
            health['warnings'].append('Low disk space')
        elif metrics['system']['disk']['percent'] > 90:
            health['checks']['disk'] = 'critical'
            health['status'] = 'unhealthy'
        
        return health
    
    def _update_history(self, metrics: Dict[str, Any]):
        """Update performance history"""
        self.performance_history.append(metrics)
        
        # Trim history if too large
        if len(self.performance_history) > self.max_history_size:
            self.performance_history = self.performance_history[-self.max_history_size:]
    
    def export_metrics(self, filepath: str):
        """Export metrics to file"""
        data = {
            'current_metrics': self.get_metrics(),
            'performance_summary': self.get_performance_summary(),
            'health_check': self.check_health()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
