"""
Unified API Gateway
Provides single entry point for all systems
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from unified_config import UnifiedConfig, get_config
from unified_integration import UnifiedIntegrationLayer, SystemType, get_integration_layer
from monitoring import get_monitoring
from multi_llm import create_llm
from unified_memory import create_memory

logger = logging.getLogger(__name__)

try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    logger.warning("Flask not available, REST API disabled")

if FLASK_AVAILABLE:
    app = Flask(__name__)
    CORS(app)
else:
    app = None


class UnifiedAPIGateway:
    """
    Unified API Gateway
    Provides single entry point for all agent systems
    """
    
    def __init__(self, config: Optional[UnifiedConfig] = None):
        self.config = config or get_config()
        self.integration = get_integration_layer(self.config)
        self.monitoring = get_monitoring()
        self.llm = create_llm(self.config.llm)
        self.memory = create_memory(self.config.memory)
        self.initialized = False
    
    async def initialize(self):
        """Initialize the gateway"""
        if not self.initialized:
            await self.integration.initialize()
            self.initialized = True
            logger.info("Unified API Gateway initialized")
    
    async def execute_task(
        self,
        description: str,
        system: Optional[str] = None,
        priority: int = 5,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a task"""
        timer_id = self.monitoring.performance.start_timer("task_execution", {"system": system or "auto"})
        
        try:
            system_type = None
            if system:
                try:
                    system_type = SystemType(system)
                except ValueError:
                    return {
                        "success": False,
                        "error": f"Unknown system: {system}"
                    }
            
            result = await self.integration.execute_with_routing(description, system_type)
            
            self.monitoring.performance.stop_timer(timer_id)
            self.monitoring.metrics.increment("tasks_executed", tags={"system": system or "auto"})
            
            return {
                "success": result.success,
                "task_id": result.task_id,
                "output": result.output,
                "error": result.error,
                "execution_time": result.execution_time,
                "metadata": result.metadata
            }
        except Exception as e:
            self.monitoring.performance.stop_timer(timer_id)
            self.monitoring.metrics.increment("tasks_failed", tags={"system": system or "auto"})
            logger.error(f"Task execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_status(self) -> Dict[str, Any]:
        """Get system status"""
        status = await self.integration.get_all_status()
        health = await self.monitoring.health.check_all()
        
        return {
            "systems": status,
            "health": {k: {
                "status": v.status,
                "message": v.message
            } for k, v in health.items()},
            "metrics": self.monitoring.metrics.get_summary(),
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_metrics(self, time_window: Optional[int] = None) -> Dict[str, Any]:
        """Get metrics"""
        return self.monitoring.get_dashboard_data()
    
    async def store_memory(self, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Store memory"""
        memory_id = await self.memory.store(content, metadata)
        return {
            "success": True,
            "memory_id": memory_id
        }
    
    async def retrieve_memory(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """Retrieve memory"""
        items = await self.memory.retrieve(query, top_k)
        return {
            "success": True,
            "items": [
                {
                    "id": item.id,
                    "content": item.content,
                    "metadata": item.metadata,
                    "timestamp": item.timestamp
                }
                for item in items
            ]
        }


# Global gateway instance
_gateway: Optional[UnifiedAPIGateway] = None


def get_gateway(config: Optional[UnifiedConfig] = None) -> UnifiedAPIGateway:
    """Get global gateway instance"""
    global _gateway
    if _gateway is None:
        _gateway = UnifiedAPIGateway(config)
    return _gateway


# REST API Endpoints (if Flask available)
if FLASK_AVAILABLE and app:
    
    @app.route('/api/v1/execute', methods=['POST'])
    async def api_execute():
        """Execute a task"""
        try:
            data = request.get_json()
            description = data.get('description')
            system = data.get('system')
            priority = data.get('priority', 5)
            parameters = data.get('parameters')
            
            if not description:
                return jsonify({"error": "description is required"}), 400
            
            gateway = get_gateway()
            await gateway.initialize()
            result = await gateway.execute_task(description, system, priority, parameters)
            
            return jsonify(result), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/v1/status', methods=['GET'])
    async def api_status():
        """Get system status"""
        try:
            gateway = get_gateway()
            await gateway.initialize()
            status = await gateway.get_status()
            return jsonify(status), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/v1/metrics', methods=['GET'])
    async def api_metrics():
        """Get metrics"""
        try:
            gateway = get_gateway()
            metrics = await gateway.get_metrics()
            return jsonify(metrics), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/v1/memory/store', methods=['POST'])
    async def api_store_memory():
        """Store memory"""
        try:
            data = request.get_json()
            content = data.get('content')
            metadata = data.get('metadata')
            
            if not content:
                return jsonify({"error": "content is required"}), 400
            
            gateway = get_gateway()
            result = await gateway.store_memory(content, metadata)
            return jsonify(result), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/v1/memory/retrieve', methods=['POST'])
    async def api_retrieve_memory():
        """Retrieve memory"""
        try:
            data = request.get_json()
            query = data.get('query')
            top_k = data.get('top_k', 5)
            
            if not query:
                return jsonify({"error": "query is required"}), 400
            
            gateway = get_gateway()
            result = await gateway.retrieve_memory(query, top_k)
            return jsonify(result), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/v1/health', methods=['GET'])
    async def api_health():
        """Health check"""
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat()
        }), 200


if __name__ == "__main__" and FLASK_AVAILABLE:
    import os
    
    gateway = get_gateway()
    asyncio.run(gateway.initialize())
    
    port = int(os.getenv("API_PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
