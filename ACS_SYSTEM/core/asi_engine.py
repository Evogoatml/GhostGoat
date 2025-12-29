import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import hashlib
from dataclasses import dataclass, asdict
import yaml

from core.metrics_collector import MetricsCollector
from core.anomaly_detector import AnomalyDetector
from core.self_modifier import SelfModifier
from optimizers import MemoryOptimizer, CodeOptimizer, DatabaseOptimizer
from security import CodeSigner, Sandbox, AuditLogger, RateLimiter


@dataclass
class SystemState:
    timestamp: str
    metrics: Dict[str, Any]
    anomalies: List[Dict]
    optimizations_applied: List[str]
    health_score: float


class ASIEngine:
    """
    Autonomous Self-Improving Engine
    Continuously monitors, diagnoses, and optimizes system performance
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
        
        # Core components
        self.metrics_collector = MetricsCollector(self.config)
        self.anomaly_detector = AnomalyDetector(self.config)
        self.self_modifier = SelfModifier(self.config)
        
        # Monitors
        self.system_monitor = SystemMonitor()
        self.process_monitor = ProcessMonitor()
        self.network_monitor = NetworkMonitor()
        self.chromadb_monitor = ChromaDBMonitor(self.config.get('chromadb_path'))
        
        # Optimizers
        self.memory_optimizer = MemoryOptimizer()
        self.code_optimizer = CodeOptimizer()
        self.database_optimizer = DatabaseOptimizer()
        
        # Security
        self.code_signer = CodeSigner(self.config['security']['signing_key'])
        self.sandbox = Sandbox(self.config['security'])
        self.audit_logger = AuditLogger(self.config['audit_log_path'])
        self.rate_limiter = RateLimiter(max_modifications_per_hour=10)
        
        # State
        self.state_history: List[SystemState] = []
        self.modification_count = 0
        self.running = False
        
    def _load_config(self, config_path: Optional[Path]) -> Dict:
        """Load configuration from YAML"""
        if config_path is None:
            config_path = Path(__file__).parent.parent / 'config' / 'default_config.yaml'
        
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _setup_logging(self) -> logging.Logger:
        """Configure logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('asi_engine.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger('ASIEngine')
    
    async def start(self):
        """Start autonomous monitoring and optimization loop"""
        self.logger.info("Starting ASI Engine...")
        self.running = True
        
        try:
            await asyncio.gather(
                self.monitoring_loop(),
                self.optimization_loop(),
                self.self_modification_loop(),
                self.health_check_loop()
            )
        except Exception as e:
            self.logger.error(f"Fatal error in ASI Engine: {e}")
            await self.emergency_shutdown()
    
    async def monitoring_loop(self):
        """Continuous system monitoring"""
        while self.running:
            try:
                metrics = await self.collect_comprehensive_metrics()
                anomalies = self.anomaly_detector.detect(metrics)
                
                if anomalies:
                    self.logger.warning(f"Detected {len(anomalies)} anomalies")
                    await self.handle_anomalies(anomalies, metrics)
                
                # Store state
                state = SystemState(
                    timestamp=datetime.now().isoformat(),
                    metrics=metrics,
                    anomalies=anomalies,
                    optimizations_applied=[],
                    health_score=self.calculate_health_score(metrics, anomalies)
                )
                self.state_history.append(state)
                
                # Trim history
                if len(self.state_history) > 10000:
                    self.state_history = self.state_history[-5000:]
                
                await asyncio.sleep(self.config['monitoring_interval'])
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def collect_comprehensive_metrics(self) -> Dict[str, Any]:
        """Gather metrics from all monitors"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'system': await self.system_monitor.collect(),
            'processes': await self.process_monitor.collect(),
            'network': await self.network_monitor.collect(),
            'chromadb': await self.chromadb_monitor.collect(),
        }
        
        return metrics
    
    async def optimization_loop(self):
        """Execute optimizations based on detected issues"""
        while self.running:
            try:
                if len(self.state_history) < 10:
                    await asyncio.sleep(10)
                    continue
                
                # Analyze recent states
                recent_states = self.state_history[-100:]
                optimization_candidates = self.identify_optimization_opportunities(recent_states)
                
                for candidate in optimization_candidates:
                    success = await self.execute_optimization(candidate)
                    if success:
                        self.logger.info(f"Successfully applied optimization: {candidate['type']}")
                
                await asyncio.sleep(self.config['optimization_interval'])
                
            except Exception as e:
                self.logger.error(f"Error in optimization loop: {e}")
                await asyncio.sleep(10)
    
    async def self_modification_loop(self):
        """Self-modifying code improvements"""
        while self.running:
            try:
                # Check rate limit
                if not self.rate_limiter.can_modify():
                    await asyncio.sleep(300)
                    continue
                
                # Analyze system behavior patterns
                if len(self.state_history) < 1000:
                    await asyncio.sleep(60)
                    continue
                
                patterns = self.analyze_behavior_patterns(self.state_history[-1000:])
                
                for pattern in patterns:
                    if pattern['confidence'] > 0.85:
                        modification = await self.generate_modification(pattern)
                        
                        if modification:
                            success = await self.apply_self_modification(modification)
                            if success:
                                self.modification_count += 1
                                self.logger.info(f"Applied self-modification #{self.modification_count}")
                
                await asyncio.sleep(self.config['self_modification_interval'])
                
            except Exception as e:
                self.logger.error(f"Error in self-modification loop: {e}")
                await asyncio.sleep(60)
    
    async def handle_anomalies(self, anomalies: List[Dict], metrics: Dict):
        """Handle detected anomalies"""
        for anomaly in anomalies:
            self.logger.warning(f"Handling anomaly: {anomaly['type']} - Severity: {anomaly['severity']}")
            
            if anomaly['severity'] == 'critical':
                await self.execute_immediate_action(anomaly, metrics)
            else:
                await self.queue_optimization(anomaly)
    
    async def execute_optimization(self, candidate: Dict) -> bool:
        """Execute a specific optimization"""
        opt_type = candidate['type']
        
        try:
            if opt_type == 'memory':
                return await self.memory_optimizer.optimize(candidate['params'])
            elif opt_type == 'code':
                return await self.code_optimizer.optimize(candidate['params'])
            elif opt_type == 'database':
                return await self.database_optimizer.optimize(candidate['params'])
            else:
                self.logger.warning(f"Unknown optimization type: {opt_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Optimization failed: {e}")
            return False
    
    async def apply_self_modification(self, modification: Dict) -> bool:
        """Apply self-modification with security checks"""
        try:
            # Security validation
            if not self.validate_modification_security(modification):
                self.logger.error("Modification failed security validation")
                return False
            
            # Sign the modification
            signature = self.code_signer.sign(modification['code'])
            modification['signature'] = signature
            
            # Execute in sandbox
            result = await self.sandbox.execute(modification)
            
            if result['success']:
                # Apply to production
                applied = await self.self_modifier.apply(modification)
                
                if applied:
                    # Audit log
                    self.audit_logger.log_modification(modification, result)
                    self.rate_limiter.record_modification()
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Self-modification failed: {e}")
            return False
    
    def validate_modification_security(self, modification: Dict) -> bool:
        """Validate modification against security policies"""
        # Check for dangerous operations
        dangerous_patterns = [
            'os.system', 'subprocess.call', 'eval(', 'exec(',
            '__import__', 'open(', 'rm -rf', 'DROP TABLE'
        ]
        
        code = modification.get('code', '')
        for pattern in dangerous_patterns:
            if pattern in code:
                self.logger.warning(f"Dangerous pattern detected: {pattern}")
                return False
        
        return True
    
    def identify_optimization_opportunities(self, states: List[SystemState]) -> List[Dict]:
        """Analyze states to find optimization opportunities"""
        opportunities = []
        
        # Memory patterns
        avg_memory = sum(s.metrics['system']['memory']['percent'] for s in states) / len(states)
        if avg_memory > 80:
            opportunities.append({
                'type': 'memory',
                'priority': 'high',
                'params': {'target_reduction': 20}
            })
        
        # ChromaDB issues
        chromadb_failures = sum(1 for s in states if not s.metrics['chromadb'].get('healthy', True))
        if chromadb_failures > len(states) * 0.1:
            opportunities.append({
                'type': 'database',
                'priority': 'critical',
                'params': {'component': 'chromadb', 'action': 'optimize_indices'}
            })
        
        return opportunities
    
    def analyze_behavior_patterns(self, states: List[SystemState]) -> List[Dict]:
        """Detect recurring patterns for self-modification"""
        patterns = []
        
        # Pattern: Recurring memory spikes
        memory_values = [s.metrics['system']['memory']['percent'] for s in states]
        if self.detect_periodic_spikes(memory_values):
            patterns.append({
                'type': 'periodic_memory_spike',
                'confidence': 0.9,
                'recommendation': 'add_periodic_gc'
            })
        
        return patterns
    
    def detect_periodic_spikes(self, values: List[float]) -> bool:
        """Detect periodic spikes in metric values"""
        import numpy as np
        
        if len(values) < 100:
            return False
        
        # Simple spike detection
        mean = np.mean(values)
        std = np.std(values)
        spikes = [v > mean + 2*std for v in values]
        
        return sum(spikes) > len(values) * 0.1
    
    async def generate_modification(self, pattern: Dict) -> Optional[Dict]:
        """Generate code modification based on detected pattern"""
        if pattern['type'] == 'periodic_memory_spike':
            return {
                'type': 'add_method',
                'target_class': 'ASIEngine',
                'method_name': 'periodic_gc_trigger',
                'code': '''
async def periodic_gc_trigger(self):
    """Auto-generated: Periodic garbage collection"""
    import gc
    while self.running:
        gc.collect()
        await asyncio.sleep(300)
''',
                'inject_into': 'start',
                'pattern': pattern
            }
        
        return None
    
    def calculate_health_score(self, metrics: Dict, anomalies: List[Dict]) -> float:
        """Calculate overall system health score (0-100)"""
        score = 100.0
        
        # Deduct for high resource usage
        memory_pct = metrics['system']['memory']['percent']
        if memory_pct > 80:
            score -= (memory_pct - 80) * 2
        
        # Deduct for anomalies
        score -= len(anomalies) * 5
        
        # Deduct for critical anomalies
        critical_count = sum(1 for a in anomalies if a['severity'] == 'critical')
        score -= critical_count * 15
        
        return max(0, min(100, score))
    
    async def health_check_loop(self):
        """Periodic health checks and self-healing"""
        while self.running:
            try:
                health = await self.perform_health_check()
                
                if health['score'] < 50:
                    self.logger.critical(f"Health score critical: {health['score']}")
                    await self.initiate_recovery()
                
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                await asyncio.sleep(30)
    
    async def perform_health_check(self) -> Dict:
        """Comprehensive health check"""
        return {
            'score': self.state_history[-1].health_score if self.state_history else 100,
            'components': {
                'monitors': await self.check_monitors_health(),
                'optimizers': await self.check_optimizers_health(),
                'security': await self.check_security_health()
            }
        }
    
    async def initiate_recovery(self):
        """Self-healing recovery procedures"""
        self.logger.info("Initiating recovery procedures...")
        
        # Clear caches
        await self.memory_optimizer.emergency_cleanup()
        
        # Reset problematic components
        if hasattr(self, 'chromadb_monitor'):
            await self.chromadb_monitor.reset()
        
        # Rollback recent modifications if necessary
        if self.modification_count > 0:
            await self.rollback_last_modification()
    
    async def rollback_last_modification(self):
        """Rollback the most recent self-modification"""
        self.logger.warning("Rolling back last modification...")
        result = await self.self_modifier.rollback()
        if result:
            self.modification_count -= 1
    
    async def emergency_shutdown(self):
        """Emergency shutdown procedures"""
        self.logger.critical("Executing emergency shutdown...")
        self.running = False
        
        # Save state
        self.save_state()
        
        # Cleanup
        await self.cleanup()
    
    def save_state(self):
        """Persist current state to disk"""
        state_file = Path('asi_state.json')
        with open(state_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'modification_count': self.modification_count,
                'recent_states': [asdict(s) for s in self.state_history[-100:]],
                'health_score': self.state_history[-1].health_score if self.state_history else 0
            }, f, indent=2)
    
    async def cleanup(self):
        """Cleanup resources"""
        self.logger.info("Cleaning up resources...")
        # Close connections, flush logs, etc.
        pass
    
    async def check_monitors_health(self) -> bool:
        """Check if all monitors are functioning"""
        return True  # Implement actual checks
    
    async def check_optimizers_health(self) -> bool:
        """Check if all optimizers are functioning"""
        return True  # Implement actual checks
    
    async def check_security_health(self) -> bool:
        """Check if security systems are functioning"""
        return True  # Implement actual checks
    
    async def execute_immediate_action(self, anomaly: Dict, metrics: Dict):
        """Execute immediate action for critical anomalies"""
        action = anomaly.get('action')
        
        if action == 'memory_emergency_cleanup':
            await self.memory_optimizer.emergency_cleanup()
        elif action == 'restart_chromadb':
            await self.chromadb_monitor.restart()
        elif action == 'kill_runaway_process':
            await self.process_monitor.kill_process(anomaly.get('pid'))
    
    async def queue_optimization(self, anomaly: Dict):
        """Queue optimization for non-critical anomalies"""
        # Implement optimization queue
        pass


async def main():
    """Entry point"""
    engine = ASIEngine()
    await engine.start()


if __name__ == "__main__":
    asyncio.run(main())
