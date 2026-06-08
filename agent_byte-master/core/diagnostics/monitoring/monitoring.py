"""
Monitoring and Observability System
Tracks system performance, health, and metrics
"""

import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum
import json

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Metric types"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Metric:
    """Metric data point"""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheck:
    """Health check result"""
    component: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    metrics: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Collects and stores metrics"""
    
    def __init__(self, max_metrics: int = 10000):
        self.max_metrics = max_metrics
        self.metrics: List[Metric] = []
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.timers: Dict[str, List[float]] = defaultdict(list)
    
    def record(self, metric: Metric):
        """Record a metric"""
        self.metrics.append(metric)
        
        # Maintain max size
        if len(self.metrics) > self.max_metrics:
            self.metrics = self.metrics[-self.max_metrics:]
        
        # Update aggregated metrics
        if metric.metric_type == MetricType.COUNTER:
            self.counters[metric.name] += metric.value
        elif metric.metric_type == MetricType.GAUGE:
            self.gauges[metric.name] = metric.value
        elif metric.metric_type == MetricType.TIMER:
            self.timers[metric.name].append(metric.value)
            # Keep only last 1000 timer values
            if len(self.timers[metric.name]) > 1000:
                self.timers[metric.name] = self.timers[metric.name][-1000:]
    
    def increment(self, name: str, value: float = 1.0, tags: Dict[str, str] = None):
        """Increment a counter"""
        metric = Metric(
            name=name,
            value=value,
            metric_type=MetricType.COUNTER,
            tags=tags or {}
        )
        self.record(metric)
    
    def gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Set a gauge value"""
        metric = Metric(
            name=name,
            value=value,
            metric_type=MetricType.GAUGE,
            tags=tags or {}
        )
        self.record(metric)
    
    def timer(self, name: str, duration: float, tags: Dict[str, str] = None):
        """Record a timer value"""
        metric = Metric(
            name=name,
            value=duration,
            metric_type=MetricType.TIMER,
            tags=tags or {}
        )
        self.record(metric)
    
    def get_metrics(
        self,
        name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Metric]:
        """Get metrics with optional filtering"""
        metrics = self.metrics
        
        if name:
            metrics = [m for m in metrics if m.name == name]
        
        if start_time:
            metrics = [m for m in metrics if m.timestamp >= start_time]
        
        if end_time:
            metrics = [m for m in metrics if m.timestamp <= end_time]
        
        return metrics
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        return {
            "total_metrics": len(self.metrics),
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "timers": {
                name: {
                    "count": len(values),
                    "min": min(values) if values else 0,
                    "max": max(values) if values else 0,
                    "avg": sum(values) / len(values) if values else 0
                }
                for name, values in self.timers.items()
            }
        }


class HealthMonitor:
    """Monitors system health"""
    
    def __init__(self):
        self.health_checks: Dict[str, HealthCheck] = {}
        self.check_functions: Dict[str, callable] = {}
    
    def register_check(self, component: str, check_function: callable):
        """Register a health check function"""
        self.check_functions[component] = check_function
    
    async def check(self, component: str) -> HealthCheck:
        """Run health check for a component"""
        if component not in self.check_functions:
            return HealthCheck(
                component=component,
                status="unhealthy",
                message="No health check registered"
            )
        
        try:
            result = await self.check_functions[component]()
            
            if isinstance(result, HealthCheck):
                health = result
            elif isinstance(result, dict):
                health = HealthCheck(
                    component=component,
                    status=result.get("status", "unknown"),
                    message=result.get("message", ""),
                    metrics=result.get("metrics", {})
                )
            else:
                health = HealthCheck(
                    component=component,
                    status="healthy" if result else "unhealthy",
                    message="Check completed"
                )
            
            self.health_checks[component] = health
            return health
        
        except Exception as e:
            health = HealthCheck(
                component=component,
                status="unhealthy",
                message=f"Health check failed: {e}"
            )
            self.health_checks[component] = health
            return health
    
    async def check_all(self) -> Dict[str, HealthCheck]:
        """Run all health checks"""
        results = {}
        for component in self.check_functions:
            results[component] = await self.check(component)
        return results
    
    def get_status(self, component: Optional[str] = None) -> Dict[str, Any]:
        """Get health status"""
        if component:
            if component in self.health_checks:
                health = self.health_checks[component]
                return {
                    "component": health.component,
                    "status": health.status,
                    "message": health.message,
                    "timestamp": health.timestamp.isoformat(),
                    "metrics": health.metrics
                }
            else:
                return {"component": component, "status": "unknown"}
        else:
            return {
                component: {
                    "status": health.status,
                    "message": health.message,
                    "timestamp": health.timestamp.isoformat()
                }
                for component, health in self.health_checks.items()
            }


class PerformanceMonitor:
    """Monitors system performance"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.active_timers: Dict[str, float] = {}
    
    def start_timer(self, name: str, tags: Dict[str, str] = None):
        """Start a performance timer"""
        timer_id = f"{name}_{id(tags) if tags else time.time()}"
        self.active_timers[timer_id] = {
            "name": name,
            "start": time.time(),
            "tags": tags or {}
        }
        return timer_id
    
    def stop_timer(self, timer_id: str):
        """Stop a performance timer"""
        if timer_id in self.active_timers:
            timer_data = self.active_timers[timer_id]
            duration = time.time() - timer_data["start"]
            self.metrics.timer(timer_data["name"], duration, timer_data["tags"])
            del self.active_timers[timer_id]
            return duration
        return None
    
    def get_performance_summary(self, time_window: timedelta = timedelta(hours=1)) -> Dict[str, Any]:
        """Get performance summary for time window"""
        end_time = datetime.now()
        start_time = end_time - time_window
        
        metrics = self.metrics.get_metrics(start_time=start_time, end_time=end_time)
        
        # Group by name
        by_name = defaultdict(list)
        for metric in metrics:
            by_name[metric.name].append(metric.value)
        
        summary = {}
        for name, values in by_name.items():
            summary[name] = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values) if values else 0
            }
        
        return summary


class MonitoringSystem:
    """Unified monitoring system"""
    
    def __init__(self):
        self.metrics = MetricsCollector()
        self.health = HealthMonitor()
        self.performance = PerformanceMonitor(self.metrics)
        self.logger = logging.getLogger(__name__)
    
    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType,
        tags: Dict[str, str] = None
    ):
        """Record a metric"""
        metric = Metric(name=name, value=value, metric_type=metric_type, tags=tags or {})
        self.metrics.record(metric)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for monitoring dashboard"""
        return {
            "metrics": self.metrics.get_summary(),
            "health": self.health.get_status(),
            "performance": self.performance.get_performance_summary()
        }
    
    def export_metrics(self, format: str = "json") -> str:
        """Export metrics"""
        if format == "json":
            return json.dumps({
                "metrics": [asdict(m) for m in self.metrics.metrics[-1000:]],
                "summary": self.metrics.get_summary()
            }, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported format: {format}")


# Global monitoring instance
_monitoring: Optional[MonitoringSystem] = None


def get_monitoring() -> MonitoringSystem:
    """Get global monitoring instance"""
    global _monitoring
    if _monitoring is None:
        _monitoring = MonitoringSystem()
    return _monitoring
