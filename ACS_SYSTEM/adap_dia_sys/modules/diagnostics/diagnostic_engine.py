"""
Core Diagnostics Engine for Nexus ASI
Handles real-time system monitoring and metrics collection
"""

import asyncio
import psutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass, asdict
import json

from asi.core.metrics_collector import MetricsCollector
from asi.core.anomaly_detector import AnomalyDetector
from asi.core.optimization_executor import OptimizationExecutor
from asi.security.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """System metrics snapshot"""
    timestamp: str
    cpu_percent: List[float]
    cpu_freq: Dict[str, float]
    load_avg: List[float]
    memory_virtual: Dict[str, Any]
    memory_swap: Dict[str, Any]
    disk_usage: Dict[str, Dict[str, Any]]
    network_io: Dict[str, Any]
    process_count: int
    nexus_metrics: Dict[str, Any]


@dataclass
class Anomaly:
    """Detected anomaly"""
    id: str
    timestamp: str
    type: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    value: Any
    threshold: Any
    action: str
    metadata: Dict[str, Any]


class DiagnosticsEngine:
    """
    Main diagnostics engine that orchestrates:
    - Metrics collection
    - Anomaly detection
    - Optimization execution
    """
    
    def __init__(
        self,
        nexus_root: Path,
        config: Dict[str, Any],
        audit_logger: Optional[AuditLogger] = None
    ):
        self.nexus_root = Path(nexus_root)
        self.config = config
        self.audit_logger = audit_logger or AuditLogger()
        
        # Initialize components
        self.metrics_collector = MetricsCollector(nexus_root, config)
        self.anomaly_detector = AnomalyDetector(config)
        self.optimization_executor = OptimizationExecutor(nexus_root, config)
        
        # State
        self.running = False
        self.metrics_history: List[SystemMetrics] = []
        self.anomaly_history: List[Anomaly] = []
        self.max_history_size = config.get('max_history_size', 10000)
        
        # Statistics
        self.stats = {
            'total_scans': 0,
            'total_anomalies': 0,
            'total_optimizations': 0,
            'start_time': None,
            'last_scan': None
        }
        
        logger.info(f"DiagnosticsEngine initialized for {nexus_root}")
    
    async def start(self):
        """Start the diagnostics engine"""
        if self.running:
            logger.warning("DiagnosticsEngine already running")
            return
        
        self.running = True
        self.stats['start_time'] = datetime.now().isoformat()
        
        logger.info("Starting DiagnosticsEngine...")
        await self.audit_logger.log_event(
            event_type="engine_start",
            message="Diagnostics engine started",
            metadata={"config": self.config}
        )
        
        # Start background tasks
        asyncio.create_task(self._monitoring_loop())
        asyncio.create_task(self._cleanup_loop())
        
        logger.info("DiagnosticsEngine started successfully")
    
    async def stop(self):
        """Stop the diagnostics engine"""
        if not self.running:
            return
        
        logger.info("Stopping DiagnosticsEngine...")
        self.running = False
        
        await self.audit_logger.log_event(
            event_type="engine_stop",
            message="Diagnostics engine stopped",
            metadata={"stats": self.stats}
        )
        
        logger.info("DiagnosticsEngine stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        scan_interval = self.config.get('system', {}).get('scan_interval', 10)
        
        while self.running:
            try:
                # Collect metrics
                metrics = await self.collect_metrics()
                self.metrics_history.append(metrics)
                
                # Detect anomalies
                anomalies = await self.detect_anomalies(metrics)
                
                if anomalies:
                    logger.warning(f"Detected {len(anomalies)} anomalies")
                    self.anomaly_history.extend(anomalies)
                    
                    # Execute optimizations
                    await self.execute_optimizations(anomalies)
                
                # Update stats
                self.stats['total_scans'] += 1
                self.stats['last_scan'] = datetime.now().isoformat()
                
                # Trim history if needed
                self._trim_history()
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                await self.audit_logger.log_event(
                    event_type="monitoring_error",
                    message=f"Monitoring loop error: {str(e)}",
                    severity="error"
                )
            
            await asyncio.sleep(scan_interval)
    
    async def collect_metrics(self) -> SystemMetrics:
        """Collect system metrics"""
        try:
            metrics = await self.metrics_collector.collect_all()
            return metrics
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            raise
    
    async def detect_anomalies(self, metrics: SystemMetrics) -> List[Anomaly]:
        """Detect anomalies in current metrics"""
        try:
            anomalies = await self.anomaly_detector.detect(
                metrics,
                self.metrics_history
            )
            
            if anomalies:
                self.stats['total_anomalies'] += len(anomalies)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return []
    
    async def execute_optimizations(self, anomalies: List[Anomaly]):
        """Execute optimizations for detected anomalies"""
        for anomaly in anomalies:
            try:
                logger.info(f"Executing optimization for anomaly: {anomaly.type}")
                
                result = await self.optimization_executor.execute(anomaly)
                
                if result['success']:
                    self.stats['total_optimizations'] += 1
                    logger.info(f"Optimization successful: {anomaly.action}")
                else:
                    logger.warning(f"Optimization failed: {result.get('error')}")
                
                # Log to audit
                await self.audit_logger.log_event(
                    event_type="optimization_executed",
                    message=f"Executed {anomaly.action}",
                    metadata={
                        'anomaly': asdict(anomaly),
                        'result': result
                    }
                )
                
            except Exception as e:
                logger.error(f"Error executing optimization for {anomaly.type}: {e}")
    
    def _trim_history(self):
        """Trim history to max size"""
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history = self.metrics_history[-self.max_history_size:]
        
        if len(self.anomaly_history) > self.max_history_size:
            self.anomaly_history = self.anomaly_history[-self.max_history_size:]
    
    async def _cleanup_loop(self):
        """Periodic cleanup of old data"""
        cleanup_interval = 3600  # 1 hour
        
        while self.running:
            await asyncio.sleep(cleanup_interval)
            
            try:
                # Remove metrics older than retention period
                retention_hours = self.config.get('retention_hours', 168)  # 7 days
                cutoff = datetime.now() - timedelta(hours=retention_hours)
                
                self.metrics_history = [
                    m for m in self.metrics_history
                    if datetime.fromisoformat(m.timestamp) > cutoff
                ]
                
                logger.info(f"Cleanup: retained {len(self.metrics_history)} metrics")
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """Get most recent metrics"""
        if self.metrics_history:
            return self.metrics_history[-1]
        return None
    
    def get_recent_anomalies(self, hours: int = 24) -> List[Anomaly]:
        """Get anomalies from last N hours"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        return [
            a for a in self.anomaly_history
            if datetime.fromisoformat(a.timestamp) > cutoff
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics"""
        return {
            **self.stats,
            'metrics_history_size': len(self.metrics_history),
            'anomaly_history_size': len(self.anomaly_history),
            'uptime_seconds': self._calculate_uptime()
        }
    
    def _calculate_uptime(self) -> Optional[float]:
        """Calculate engine uptime in seconds"""
        if self.stats['start_time']:
            start = datetime.fromisoformat(self.stats['start_time'])
            return (datetime.now() - start).total_seconds()
        return None
    
    async def trigger_manual_optimization(self, optimization_type: str) -> Dict[str, Any]:
        """Manually trigger an optimization"""
        logger.info(f"Manual optimization triggered: {optimization_type}")
        
        # Create synthetic anomaly for manual optimization
        anomaly = Anomaly(
            id=f"manual_{int(time.time())}",
            timestamp=datetime.now().isoformat(),
            type="manual_trigger",
            severity="medium",
            value=None,
            threshold=None,
            action=optimization_type,
            metadata={"manual": True}
        )
        
        result = await self.optimization_executor.execute(anomaly)
        
        await self.audit_logger.log_event(
            event_type="manual_optimization",
            message=f"Manual optimization: {optimization_type}",
            metadata={'result': result}
        )
        
        return result
    
    def export_metrics(self, format: str = 'json', hours: int = 24) -> str:
        """Export metrics in specified format"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        recent_metrics = [
            asdict(m) for m in self.metrics_history
            if datetime.fromisoformat(m.timestamp) > cutoff
        ]
        
        if format == 'json':
            return json.dumps(recent_metrics, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")
