"""
Self-Directed Learning System for GhostGoat
Enables the system to learn from experience and improve over time
"""
from __future__ import annotations

import logging
import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
import re

logger = logging.getLogger("ghostgoat.intelligence.learning")


@dataclass
class LearningEpisode:
    """Represents a single learning interaction"""
    timestamp: str
    user_message: str
    agent_response: str
    user_feedback: Optional[float] = None  # -1 to 1 rating
    success: bool = True
    abilities_used: List[str] = None
    knowledge_frames_accessed: List[str] = None
    pattern_matches: List[str] = None
    improvement_metrics: Dict[str, float] = None
    
    def __post_init__(self):
        if self.abilities_used is None:
            self.abilities_used = []
        if self.knowledge_frames_accessed is None:
            self.knowledge_frames_accessed = []
        if self.pattern_matches is None:
            self.pattern_matches = []
        if self.improvement_metrics is None:
            self.improvement_metrics = {}


@dataclass
class ImprovementRule:
    """A learned rule for system improvement"""
    rule_id: str
    trigger_pattern: str  # Pattern that triggers this rule
    action: str  # What to do when triggered
    expected_outcome: str  # Expected positive outcome
    success_rate: float = 0.0  # How often this rule succeeds
    confidence: float = 0.5  # Confidence in the rule (0-1)
    last_applied: Optional[str] = None
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class SelfDirectedLearner:
    """
    Enables GhostGoat to learn from interactions and improve over time.
    Tracks successes and failures to identify improvement opportunities.
    """
    
    def __init__(self, intelligence_config):
        self.config = intelligence_config
        self.logger = logging.getLogger("ghostgoat.intelligence.learning.learner")
        self.learning_history: List[LearningEpisode] = []
        self.improvement_rules: Dict[str, ImprovementRule] = {}
        self.performance_metrics = {
            "total_interactions": 0,
            "successful_interactions": 0,
            "average_response_rating": 0.5,
            "abilities_used_count": {},
            "knowledge_accessed_count": {},
            "learning_rate": 0.01
        }
        self._load_learning_data()
    
    def _load_learning_data(self):
        """Load learning history and rules from storage"""
        try:
            learning_file = Path(self.config.ability_library_path) / "learning_data.json"
            if learning_file.exists():
                with open(learning_file, 'r') as f:
                    data = json.load(f)
                    # Load episodes
                    for ep_data in data.get("episodes", []):
                        episode = LearningEpisode(**ep_data)
                        self.learning_history.append(episode)
                    # Load improvement rules
                    for rule_data in data.get("improvement_rules", {}).values():
                        rule = ImprovementRule(**rule_data)
                        self.improvement_rules[rule.rule_id] = rule
                    # Load metrics
                    if "performance_metrics" in data:
                        self.performance_metrics.update(data["performance_metrics"])
                self.logger.info(f"Loaded {len(self.learning_history)} learning episodes")
        except Exception as e:
            self.logger.warning(f"Could not load learning data: {e}")
    
    def _save_learning_data(self):
        """Save learning history and rules to storage"""
        try:
            learning_dir = Path(self.config.ability_library_path)
            learning_dir.mkdir(parents=True, exist_ok=True)
            learning_file = learning_dir / "learning_data.json"
            
            data = {
                "episodes": [self._episode_to_dict(ep) for ep in self.learning_history],
                "improvement_rules": {
                    rid: self._rule_to_dict(rule) 
                    for rid, rule in self.improvement_rules.items()
                },
                "performance_metrics": self.performance_metrics,
                "last_updated": datetime.now().isoformat()
            }
            
            with open(learning_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to save learning data: {e}")
    
    def _episode_to_dict(self, episode: LearningEpisode) -> Dict[str, Any]:
        """Convert episode to dictionary"""
        return {
            "timestamp": episode.timestamp,
            "user_message": episode.user_message,
            "agent_response": episode.agent_response,
            "user_feedback": episode.user_feedback,
            "success": episode.success,
            "abilities_used": episode.abilities_used,
            "knowledge_frames_accessed": episode.knowledge_frames_accessed,
            "pattern_matches": episode.pattern_matches,
            "improvement_metrics": episode.improvement_metrics
        }
    
    def _rule_to_dict(self, rule: ImprovementRule) -> Dict[str, Any]:
        """Convert rule to dictionary"""
        return asdict(rule)
    
    def record_experience(
        self,
        user_message: str,
        agent_response: str,
        abilities_used: List[str] = None,
        knowledge_frames: List[str] = None,
        patterns: List[str] = None,
        success: bool = True
    ):
        """Record a learning experience from an interaction"""
        abilities_used = abilities_used or []
        knowledge_frames = knowledge_frames or []
        patterns = patterns or []
        
        episode = LearningEpisode(
            timestamp=datetime.now().isoformat(),
            user_message=user_message,
            agent_response=agent_response,
            abilities_used=abilities_used,
            knowledge_frames_accessed=knowledge_frames,
            pattern_matches=patterns,
            success=success
        )
        
        self.learning_history.append(episode)
        
        # Update metrics
        self.performance_metrics["total_interactions"] += 1
        if success:
            self.performance_metrics["successful_interactions"] += 1
        
        for ability in abilities_used:
            self.performance_metrics["abilities_used_count"][ability] = (
                self.performance_metrics["abilities_used_count"].get(ability, 0) + 1
            )
        
        for frame in knowledge_frames:
            self.performance_metrics["knowledge_accessed_count"][frame] = (
                self.performance_metrics["knowledge_accessed_count"].get(frame, 0) + 1
            )
        
        self._save_learning_data()
    
    def analyze_performance_gaps(self) -> List[Dict[str, Any]]:
        """Analyze learning history to find improvement opportunities"""
        gaps = []
        
        for episode in self.learning_history:
            if not episode.success:
                # Analyze what went wrong
                gap = {
                    "episode_timestamp": episode.timestamp,
                    "problem_message": episode.user_message,
                    "reason": self._analyze_failure(episode),
                    "suggested_improvement": self._suggest_improvement(episode)
                }
                gaps.append(gap)
        
        return gaps
    
    def _analyze_failure(self, episode: LearningEpisode) -> str:
        """Analyze why an episode failed"""
        if not episode.pattern_matches:
            return "No pattern matches - the problem may not fit known patterns"
        
        if not episode.abilities_used:
            return "No ability was applied - need to match patterns to abilities"
        
        return f"Applied ability {episode.abilities_used} but result was not successful"
    
    def _suggest_improvement(self, episode: LearningEpisode) -> str:
        """Suggest improvements based on failure analysis"""
        if not episode.pattern_matches:
            return "Improve pattern recognition by expanding keyword definitions"
        
        if not episode.abilities_used:
            return "Connect recognized patterns to ability templates"
        
        return "Refine ability parameters or try alternative abilities for this problem type"
    
    def generate_improvement_rules(self) -> List[ImprovementRule]:
        """Generate new improvement rules from learning history"""
        rules = []
        
        for i, episode in enumerate(self.learning_history):
            if episode.success and i > 0:
                prev_episode = self.learning_history[i-1]
                
                if prev_episode.success != episode.success:
                    # Success changed from previous episode
                    rule_id = f"improvement_rule_{len(self.improvement_rules) + len(rules)}"
                    
                    rule = ImprovementRule(
                        rule_id=rule_id,
                        trigger_pattern=prev_episode.pattern_matches[0] if prev_episode.pattern_matches else "unknown",
                        action=f"Use ability {episode.abilities_used[0] if episode.abilities_used else 'best_matching'}",
                        expected_outcome="Improved response quality",
                        success_rate=1.0,
                        confidence=0.5
                    )
                    rules.append(rule)
        
        self.improvement_rules.update({r.rule_id: r for r in rules})
        return rules
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """Get overall learning statistics"""
        total = self.performance_metrics.get("total_interactions", 0)
        successful = self.performance_metrics.get("successful_interactions", 0)
        
        return {
            "total_interactions": total,
            "successful_interactions": successful,
            "success_rate": successful / total if total > 0 else 0,
            "learning_history_length": len(self.learning_history),
            "improvement_rules_count": len(self.improvement_rules),
            "top_abilities_used": sorted(
                self.performance_metrics.get("abilities_used_count", {}).items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
            "top_knowledge_accessed": sorted(
                self.performance_metrics.get("knowledge_accessed_count", {}).items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }
    
    def adapt_ability_for_problem(
        self, 
        ability: Any,  # AbilityTemplate
        problem_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Adapt an ability template for a specific problem context.
        This is where dynamic, context-aware behavior comes from.
        """
        adapted_params = {}
        
        for param_name, param_desc in ability.parameters.items():
            # Use pattern recognition and context to determine parameter values
            adapted_params[param_name] = self._determine_parameter_value(
                param_name, param_desc, problem_context
            )
        
        return {
            "ability_id": ability.id,
            "adapted_parameters": adapted_params,
            "context_notes": self._generate_context_notes(ability, problem_context)
        }
    
    def _determine_parameter_value(
        self, 
        param_name: str, 
        param_desc: str,
        context: Dict[str, Any]
    ) -> Any:
        """Determine parameter value based on context"""
        # This is a simplified version - in production would use ML/rules
        param_lower = param_name.lower()
        context_str = str(context).lower()
        
        if "partition" in param_lower and "half" in param_desc.lower():
            if "sorted" in context_str:
                return "binary_split"
            return "equal_split"
        
        if "comparison" in param_lower:
            return "direct_compare"
        
        if "base_case" in param_lower or "base_case" in param_desc.lower():
            return "size <= 1"
        
        if "cache_strategy" in param_lower:
            return "dictionary"
        
        return None
    
    def _generate_context_notes(
        self, 
        ability: Any, 
        context: Dict[str, Any]
    ) -> List[str]:
        """Generate notes about how ability applies to this context"""
        notes = []
        
        for tag in ability.domain_tags:
            if tag in str(context).lower():
                notes.append(f"Domain tag '{tag}' matches problem context")
        
        for example in ability.examples[:2]:  # Check first 2 examples
            if any(word in str(context).lower() for word in example.lower().split()):
                notes.append(f"Example '{example}' is similar to current problem")
        
        if not notes:
            notes.append("Applied based on general pattern matching")
        
        return notes

# Global instance
_self_directed_learner: Optional[SelfDirectedLearner] = None

def get_self_directed_learner() -> SelfDirectedLearner:
    """Get global self-directed learner instance"""
    global _self_directed_learner
    if _self_directed_learner is None:
        from core.unified_config import get_config
        config = get_config()
        _self_directed_learner = SelfDirectedLearner(config.intelligence)
    return _self_directed_learner