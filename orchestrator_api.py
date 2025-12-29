"""
GhostGoat LLM Orchestrator API
Unified REST API and Python interface for multi-agent orchestration
"""

import os
import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    logger.warning("Flask not installed. REST API endpoints will not be available.")

from llm_orchestrator import LLMOrchestrator, Task, AgentCapability

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app (if available)
if FLASK_AVAILABLE:
    app = Flask(__name__)
    CORS(app)
else:
    app = None

# Global orchestrator instance
_orchestrator: Optional[LLMOrchestrator] = None


def get_orchestrator() -> LLMOrchestrator:
    """Get or create orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = LLMOrchestrator(
            llm_provider=os.getenv("LLM_PROVIDER", "mock"),
            llm_model=os.getenv("LLM_MODEL", "gpt-4"),
            llm_api_key=os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        )
    return _orchestrator


class OrchestratorAPI:
    """
    Python API wrapper for LLM Orchestrator
    Provides synchronous and asynchronous interfaces
    """
    
    def __init__(self, **orchestrator_kwargs):
        self.orchestrator = LLMOrchestrator(**orchestrator_kwargs)
        self._loop = None
    
    def execute(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Synchronous execution"""
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        
        return self._loop.run_until_complete(
            self.orchestrator.orchestrate(query, context)
        )
    
    async def execute_async(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Asynchronous execution"""
        return await self.orchestrator.orchestrate(query, context)
    
    def batch_execute(self, queries: List[str], context: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Execute multiple queries"""
        results = []
        for query in queries:
            result = self.execute(query, context)
            results.append(result)
        return results
    
    async def batch_execute_async(self, queries: List[str], context: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Execute multiple queries asynchronously"""
        tasks = [self.orchestrator.orchestrate(query, context) for query in queries]
        return await asyncio.gather(*tasks)
    
    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        return self.orchestrator.get_status()
    
    def get_agents(self) -> List[Dict[str, Any]]:
        """Get agent profiles"""
        return [
            {
                "name": profile.name,
                "host": profile.host,
                "port": profile.port,
                "capabilities": [c.value for c in profile.capabilities],
                "status": profile.status,
                "current_tasks": profile.current_tasks,
                "performance": profile.performance_metrics
            }
            for profile in self.orchestrator.agent_profiles.values()
        ]
    
    def get_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get tasks, optionally filtered by status"""
        tasks = list(self.orchestrator.tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return [asdict(t) for t in tasks]
    
    def get_execution_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get execution history"""
        return self.orchestrator.execution_history[-limit:]


# REST API Endpoints

@app.route('/api/v1/orchestrate', methods=['POST'])
def api_orchestrate():
    """Orchestrate a query"""
    try:
        data = request.get_json()
        query = data.get('query')
        context = data.get('context')
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        orchestrator = get_orchestrator()
        result = asyncio.run(orchestrator.orchestrate(query, context))
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error in orchestrate endpoint: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/status', methods=['GET'])
def api_status():
    """Get orchestrator status"""
    try:
        orchestrator = get_orchestrator()
        return jsonify(orchestrator.get_status()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/agents', methods=['GET'])
def api_agents():
    """Get agent profiles"""
    try:
        orchestrator = get_orchestrator()
        agents = [
            {
                "name": profile.name,
                "host": profile.host,
                "port": profile.port,
                "capabilities": [c.value for c in profile.capabilities],
                "status": profile.status,
                "current_tasks": profile.current_tasks,
                "performance": profile.performance_metrics
            }
            for profile in orchestrator.agent_profiles.values()
        ]
        return jsonify({"agents": agents}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/tasks', methods=['GET'])
def api_tasks():
    """Get tasks"""
    try:
        orchestrator = get_orchestrator()
        status = request.args.get('status')
        
        tasks = list(orchestrator.tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        return jsonify({
            "tasks": [asdict(t) for t in tasks]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/history', methods=['GET'])
def api_history():
    """Get execution history"""
    try:
        orchestrator = get_orchestrator()
        limit = int(request.args.get('limit', 100))
        
        history = orchestrator.execution_history[-limit:]
        return jsonify({"history": history}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/health', methods=['GET'])
def api_health():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }), 200


if __name__ == "__main__":
    import os
    
    # Run Flask app
    port = int(os.getenv("ORCHESTRATOR_PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
