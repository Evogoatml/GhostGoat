"""Learning System - Experience Memory and Self-Improvement"""
import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict
import hashlib
from config import config
from rag_system import rag_system

logger = logging.getLogger(__name__)

class LearningSystem:
    def __init__(self):
        self.memory_path = config.learning.memory_path
        self.experiences_file = os.path.join(self.memory_path, "experiences.jsonl")
        self.patterns_file = os.path.join(self.memory_path, "patterns.json")
        self.playbook_file = os.path.join(self.memory_path, "playbook.json")
        
        # Load existing data
        self.experiences = self._load_experiences()
        self.patterns = self._load_patterns()
        self.playbook = self._load_playbook()
        
        logger.info(f"Learning system initialized with {len(self.experiences)} experiences")
    
    def _load_experiences(self) -> List[Dict[str, Any]]:
        """Load all experiences from JSONL file"""
        experiences = []
        if os.path.exists(self.experiences_file):
            with open(self.experiences_file, 'r') as f:
                for line in f:
                    try:
                        experiences.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return experiences
    
    def _load_patterns(self) -> Dict[str, Any]:
        """Load recognized patterns"""
        if os.path.exists(self.patterns_file):
            with open(self.patterns_file, 'r') as f:
                return json.load(f)
        return {"task_patterns": {}, "failure_patterns": {}}
    
    def _load_playbook(self) -> Dict[str, Any]:
        """Load strategy playbook"""
        if os.path.exists(self.playbook_file):
            with open(self.playbook_file, 'r') as f:
                return json.load(f)
        return {"strategies": {}, "capabilities": []}
    
    def _save_experience(self, experience: Dict[str, Any]):
        """Append experience to JSONL file"""
        with open(self.experiences_file, 'a') as f:
            f.write(json.dumps(experience) + '\n')
        self.experiences.append(experience)
    
    def _save_patterns(self):
        """Save patterns to file"""
        with open(self.patterns_file, 'w') as f:
            json.dump(self.patterns, f, indent=2)
    
    def _save_playbook(self):
        """Save playbook to file"""
        with open(self.playbook_file, 'w') as f:
            json.dump(self.playbook, f, indent=2)
    
    def store_experience(self, 
                        task_type: str,
                        query: str,
                        strategy: List[Dict[str, Any]],
                        success: bool,
                        execution_time: float,
                        context: Optional[str] = None,
                        failure_reason: Optional[str] = None) -> str:
        """
        Store a learning experience
        Returns experience ID
        """
        experience_id = hashlib.md5(f"{task_type}{datetime.now().isoformat()}".encode()).hexdigest()
        
        experience = {
            "id": experience_id,
            "task_type": task_type,
            "query": query,
            "strategy": strategy,
            "success": success,
            "execution_time": execution_time,
            "context": context,
            "failure_reason": failure_reason,
            "timestamp": datetime.now().isoformat(),
            "confidence_score": self._calculate_confidence(strategy, success)
        }
        
        self._save_experience(experience)
        
        # Auto-learn if enabled
        if config.learning.auto_learn:
            self._update_patterns(experience)
            if success:
                self._update_playbook(experience)
                # Add to RAG for semantic retrieval
                rag_system.add_text(
                    f"Task: {query}\nStrategy: {json.dumps(strategy)}\nOutcome: Success",
                    metadata={"type": "experience", "task_type": task_type, "experience_id": experience_id}
                )
        
        logger.info(f"Stored experience {experience_id}: {task_type} - {'success' if success else 'failure'}")
        return experience_id
    
    def _calculate_confidence(self, strategy: List[Dict[str, Any]], success: bool) -> float:
        """Calculate confidence score based on strategy complexity and outcome"""
        base_score = 0.8 if success else 0.2
        complexity_factor = min(len(strategy) / 10.0, 0.2)  # More steps = lower confidence
        return max(0.0, min(1.0, base_score - complexity_factor))
    
    def _update_patterns(self, experience: Dict[str, Any]):
        """Update pattern recognition from experience"""
        task_type = experience["task_type"]
        
        if task_type not in self.patterns["task_patterns"]:
            self.patterns["task_patterns"][task_type] = {
                "count": 0,
                "success_rate": 0.0,
                "common_actions": [],
                "avg_execution_time": 0.0
            }
        
        pattern = self.patterns["task_patterns"][task_type]
        pattern["count"] += 1
        
        # Update success rate
        total_successes = sum(1 for exp in self.experiences 
                            if exp["task_type"] == task_type and exp["success"])
        pattern["success_rate"] = total_successes / pattern["count"]
        
        # Update common actions
        for action in experience["strategy"]:
            action_type = action.get("action_type", "unknown")
            if action_type not in pattern["common_actions"]:
                pattern["common_actions"].append(action_type)
        
        # Update average execution time
        total_time = sum(exp["execution_time"] for exp in self.experiences 
                        if exp["task_type"] == task_type)
        pattern["avg_execution_time"] = total_time / pattern["count"]
        
        # Track failure patterns
        if not experience["success"] and experience.get("failure_reason"):
            failure_key = f"{task_type}:{experience['failure_reason']}"
            if failure_key not in self.patterns["failure_patterns"]:
                self.patterns["failure_patterns"][failure_key] = 0
            self.patterns["failure_patterns"][failure_key] += 1
        
        self._save_patterns()
    
    def _update_playbook(self, experience: Dict[str, Any]):
        """Add successful strategies to playbook"""
        task_type = experience["task_type"]
        confidence = experience["confidence_score"]
        
        if confidence >= config.learning.confidence_threshold:
            if task_type not in self.playbook["strategies"]:
                self.playbook["strategies"][task_type] = []
            
            # Add strategy if it's novel or better than existing
            strategy_hash = hashlib.md5(json.dumps(experience["strategy"], sort_keys=True).encode()).hexdigest()
            
            existing = [s for s in self.playbook["strategies"][task_type] if s["hash"] == strategy_hash]
            if not existing:
                self.playbook["strategies"][task_type].append({
                    "hash": strategy_hash,
                    "strategy": experience["strategy"],
                    "confidence": confidence,
                    "execution_time": experience["execution_time"],
                    "query_example": experience["query"]
                })
                
                # Keep only top 5 strategies per task type
                self.playbook["strategies"][task_type] = sorted(
                    self.playbook["strategies"][task_type],
                    key=lambda x: x["confidence"],
                    reverse=True
                )[:5]
        
        self._save_playbook()
    
    def get_relevant_experiences(self, query: str, task_type: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Get relevant past experiences using semantic search"""
        # Use RAG for semantic retrieval
        rag_results = rag_system.search(query, n_results=limit, filter_metadata={"type": "experience"})
        
        # Also get by task type if specified
        relevant = []
        if task_type:
            relevant = [exp for exp in self.experiences 
                       if exp["task_type"] == task_type and exp["success"]][-limit:]
        
        # Combine and deduplicate
        combined = relevant + [json.loads(r["text"].split("Strategy: ")[1].split("\nOutcome:")[0]) 
                              for r in rag_results if r not in relevant]
        
        return combined[:limit]
    
    def get_best_strategy(self, task_type: str) -> Optional[Dict[str, Any]]:
        """Get the best known strategy for a task type"""
        if task_type in self.playbook["strategies"]:
            strategies = self.playbook["strategies"][task_type]
            if strategies:
                return strategies[0]  # Already sorted by confidence
        return None
    
    def get_pattern_insights(self, task_type: str) -> Dict[str, Any]:
        """Get insights about a task type from patterns"""
        if task_type in self.patterns["task_patterns"]:
            return self.patterns["task_patterns"][task_type]
        return {}
    
    def reflect_on_task(self, 
                       query: str,
                       history: List[Dict[str, Any]],
                       outcome: str,
                       success: bool) -> Dict[str, Any]:
        """
        Reflect on completed task to generate learnings
        This is called by the ReAct engine after task completion
        """
        reflection = {
            "query": query,
            "outcome": outcome,
            "success": success,
            "lessons": [],
            "improvements": []
        }
        
        # Analyze what went well
        if success:
            reflection["lessons"].append("Task completed successfully")
            
            # Check if we found a new efficient approach
            if len(history) < 5:
                reflection["lessons"].append("Efficient solution with minimal steps")
            
            # Check for novel action combinations
            action_sequence = [action.get("action_type", "") for action in history]
            if self._is_novel_sequence(action_sequence):
                reflection["lessons"].append(f"Novel action sequence discovered: {' -> '.join(action_sequence)}")
        else:
            # Analyze failures
            reflection["lessons"].append("Task failed - analyzing failure mode")
            
            # Common failure patterns
            if any("timeout" in str(action).lower() for action in history):
                reflection["improvements"].append("Consider breaking long operations into smaller chunks")
            
            if any("error" in str(action).lower() for action in history):
                reflection["improvements"].append("Add error handling and validation")
        
        return reflection
    
    def _is_novel_sequence(self, sequence: List[str]) -> bool:
        """Check if action sequence is novel"""
        sequence_str = "->".join(sequence)
        for exp in self.experiences:
            exp_sequence = "->".join([a.get("action_type", "") for a in exp["strategy"]])
            if exp_sequence == sequence_str:
                return False
        return True
    
    def register_capability(self, capability: str, description: str):
        """Register a new capability that the system has learned"""
        capability_entry = {
            "name": capability,
            "description": description,
            "registered_at": datetime.now().isoformat()
        }
        
        if capability not in [c["name"] for c in self.playbook["capabilities"]]:
            self.playbook["capabilities"].append(capability_entry)
            self._save_playbook()
            logger.info(f"Registered new capability: {capability}")
    
    def get_capabilities(self) -> List[Dict[str, Any]]:
        """Get list of registered capabilities"""
        return self.playbook["capabilities"]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get learning system statistics"""
        total = len(self.experiences)
        successful = sum(1 for exp in self.experiences if exp["success"])
        
        return {
            "total_experiences": total,
            "successful_experiences": successful,
            "success_rate": successful / total if total > 0 else 0,
            "unique_task_types": len(self.patterns["task_patterns"]),
            "strategies_in_playbook": sum(len(v) for v in self.playbook["strategies"].values()),
            "registered_capabilities": len(self.playbook["capabilities"])
        }

learning_system = LearningSystem()
