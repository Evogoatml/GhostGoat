import psutil
import asyncio
from typing import Dict, Any, List
from datetime import datetime
import json
from pathlib import Path


class MetricsCollector:
    """Unified metrics collection interface"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.cache = {}
        self.cache_ttl = config.get('cache_ttl', 5)
        
    async def collect_all(self) -> Dict[str, Any]:
        """Collect all system metrics"""
        return {
            'timestamp': datetime.now().isoformat(),
            'system': await self.collect_system_metrics(),
            'processes': await self.collect_process_metrics(),
            'network': await self.collect_network_metrics(),
            'disk': await self.collect_disk_metrics(),
            'custom': await self.collect_custom_metrics()
        }
    
    async def collect_system_metrics(self) -> Dict[str, Any]:
        """System-level metrics"""
        cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
        
        return {
            'cpu': {
                'percent': cpu_percent,
                'avg': sum(cpu_percent) / len(cpu_percent),
                'count': psutil.cpu_count(),
                'freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {},
                'load_avg': psutil.getloadavg()
            },
            'memory': {
                'virtual': psutil.virtual_memory()._asdict(),
                'swap': psutil.swap_memory()._asdict(),
                'percent': psutil.virtual_memory().percent
            },
            'temperature': await self.get_temperature()
        }
    
    async def collect_process_metrics(self) -> Dict[str, Any]:
        """Process-level metrics"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
            try:
                pinfo = proc.info
                if pinfo['cpu_percent'] > 1 or pinfo['memory_percent'] > 1:
                    processes.append(pinfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return {
            'count': len(psutil.pids()),
            'top_cpu': sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:10],
            'top_memory': sorted(processes, key=lambda x: x['memory_percent'], reverse=True)[:10]
        }
    
    async def collect_network_metrics(self) -> Dict[str, Any]:
        """Network metrics"""
        net_io = psutil.net_io_counters()
        connections = psutil.net_connections()
        
        return {
            'io': net_io._asdict(),
            'connections': {
                'established': len([c for c in connections if c.status == 'ESTABLISHED']),
                'listen': len([c for c in connections if c.status == 'LISTEN']),
                'total': len(connections)
            }
        }
    
    async def collect_disk_metrics(self) -> Dict[str, Any]:
        """Disk usage metrics"""
        disk_usage = {}
        
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_usage[partition.mountpoint] = usage._asdict()
            except PermissionError:
                pass
        
        return disk_usage
    
    async def collect_custom_metrics(self) -> Dict[str, Any]:
        """Custom application metrics"""
        return {
            'uptime': self.get_uptime(),
            'timestamp': datetime.now().isoformat()
        }
    
    async def get_temperature(self) -> Dict[str, float]:
        """Get system temperature (Android/Termux specific)"""
        try:
            temps = psutil.sensors_temperatures()
            return {name: temp.current for name, temp_list in temps.items() for temp in temp_list}
        except:
            return {}
    
    def get_uptime(self) -> float:
        """Get system uptime in seconds"""
        return psutil.boot_time()
