"""
Ability Management System for GhostGoat
Handles extraction, caching, and application of reusable ability templates
"""
from __future__ import annotations

import logging
import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import re

logger = logging.getLogger("ghostgoat.intelligence.ability")

class AbilityType(Enum):
    """Types of abilities that can be abstracted"""
    DIVIDE_AND_CONQUER = "divide_and_conquer"
    DYNAMIC_PROGRAMMING = "dynamic_programming"
    MATHEMATICAL_OPTIMIZATION = "mathematical_optimization"
    RATE_BASED_TRANSFORMATION = "rate_based_transformation"
    FAULT_TOLERANT_QUERYING = "fault_tolerant_querying"
    ITERATIVE_REFINEMENT = "iterative_refinement"
    BOUNDARY_CONDITION_THINKING = "boundary_condition_thinking"
    ABSTRACTION_LAYER_RECOGNITION = "abstraction_layer_recognition"
    TRADE_OFF_ANALYSIS = "trade_off_analysis"

@dataclass
class AbilityTemplate:
    """Template for a reusable cognitive ability"""
    id: str
    name: str
    ability_type: AbilityType
    description: str
    parameters: Dict[str, Any]  # Parameter names and descriptions
    examples: List[str]  # Examples of problems this ability solves
    preconditions: List[str]  # Conditions when this ability is applicable
    postconditions: List[str]  # Expected outcomes after applying this ability
    complexity_impact: str  # How this affects time/space complexity
    domain_tags: List[str]  # Domains where this ability is useful (math, networking, etc.)
    confidence: float = 0.5  # Confidence in this ability's correctness (0-1)
    usage_count: int = 0  # How many times this ability has been used successfully
    last_used: Optional[str] = None  # ISO timestamp of last use
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['ability_type'] = self.ability_type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AbilityTemplate':
        """Create from dictionary"""
        data = data.copy()
        data['ability_type'] = AbilityType(data['ability_type'])
        return cls(**data)

class AbilityManager:
    """Manages the library of ability templates"""
    
    def __init__(self, intelligence_config):
        self.config = intelligence_config
        self.logger = logging.getLogger("ghostgoat.intelligence.ability.manager")
        self.abilities: Dict[str, AbilityTemplate] = {}
        self._load_abilities()
        
        # Initialize with core abilities if none exist
        if not self.abilities:
            self._initialize_core_abilities()
            self._save_abilities()
    
    def _load_abilities(self):
        """Load abilities from storage"""
        ability_file = Path(self.config.ability_library_path) / "abilities.json"
        try:
            if ability_file.exists():
                with open(ability_file, 'r') as f:
                    data = json.load(f)
                    for ability_data in data.get("abilities", []):
                        ability = AbilityTemplate.from_dict(ability_data)
                        self.abilities[ability.id] = ability
                self.logger.info(f"Loaded {len(self.abilities)} abilities from {ability_file}")
            else:
                self.logger.info(f"No ability file found at {ability_file}, will create new")
        except Exception as e:
            self.logger.error(f"Failed to load abilities: {e}")
            self.abilities = {}
    
    def _save_abilities(self):
        """Save abilities to storage"""
        try:
            ability_dir = Path(self.config.ability_library_path)
            ability_dir.mkdir(parents=True, exist_ok=True)
            ability_file = ability_dir / "abilities.json"
            
            data = {
                "abilities": [ability.to_dict() for ability in self.abilities.values()],
                "last_updated": str(Path(__file__).stat().st_mtime)
            }
            
            with open(ability_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info(f"Saved {len(self.abilities)} abilities to {ability_file}")
        except Exception as e:
            self.logger.error(f"Failed to save abilities: {e}")
    
    def _initialize_core_abilities(self):
        """Initialize with core abilities extracted from training data"""
        core_abilities = [
            AbilityTemplate(
                id="divide_and_conquer_search",
                name="Divide and Conquer Search",
                ability_type=AbilityType.DIVIDE_AND_CONQUER,
                description="Recursively partition problem space, eliminating halves based on comparison to find target in logarithmic time",
                parameters={
                    "partition_fn": "Function to split problem into two halves",
                    "comparison_fn": "Function to compare middle element with target",
                    "elimination_direction": "Which half to keep ('left', 'right', or 'both')",
                    "base_case_condition": "When to stop recursion (usually when size <= 1)"
                },
                examples=[
                    "Binary search in sorted array",
                    "Finding square root via binary search",
                    "Searching in rotated sorted array",
                    "Finding peak element in array"
                ],
                preconditions=[
                    "Problem space can be ordered or partitioned",
                    "Comparison operation provides directional information",
                    "Problem exhibits monotonicity or similar property enabling elimination"
                ],
                postconditions=[
                    "Target found or determined absent",
                    "Time complexity reduced from O(n) to O(log n)",
                    "Space complexity O(1) for iterative or O(log n) for recursive"
                ],
                complexity_impact="Reduces time complexity from linear to logarithmic",
                domain_tags=["search", "sorting", "optimization", "mathematics"],
                confidence=0.9
            ),
            AbilityTemplate(
                id="mathematical_optimization_sqrt",
                name="Square Root Optimization",
                ability_type=AbilityType.MATHEMATICAL_OPTIMIZATION,
                description="Use mathematical properties to reduce search space from O(n) to O(√n) by leveraging factor pairs or bounds",
                parameters={
                    "bound_function": "Function that provides optimization bound (e.g., sqrt(n))",
                    "check_function": "Function to test if a candidate satisfies conditions",
                    "iteration_direction": "Direction to iterate (ascending, descending, or both)"
                },
                examples=[
                    "Prime number testing (check divisors up to √n)",
                    "Finding factors of a number",
                    "Integer square root calculation",
                    "Checking perfect numbers"
                ],
                preconditions=[
                    "Problem has a mathematical property enabling bounds",
                    "Solution space exhibits symmetry or pairing",
                    "Upper bound can be computed efficiently"
                ],
                postconditions=[
                    "Time complexity reduced from O(n) to O(√n)",
                    "Correctness maintained through mathematical proof",
                    "Often enables early termination"
                ],
                complexity_impact="Reduces time complexity from linear to square root",
                domain_tags=["number_theory", "arithmetic", "factorization", "primes"],
                confidence=0.85
            ),
            AbilityTemplate(
                id="dynamic_programming_memoization",
                name="Dynamic Programming with Memoization",
                ability_type=AbilityType.DYNAMIC_PROGRAMMING,
                description="Solve problems by breaking into overlapping subproblems and caching results to avoid recomputation",
                parameters={
                    "state_representation": "How to represent subproblem state",
                    "recurrence_relation": "How to compute state from substates",
                    "base_cases": "Known solutions for smallest subproblems",
                    "cache_strategy": "How to store and retrieve computed states"
                },
                examples=[
                    "Fibonacci sequence calculation",
                    "Shortest path in grid (unique paths)",
                    "Knapsack problem",
                    "Longest common subsequence",
                    "Minimum coin change"
                ],
                preconditions=[
                    "Problem can be divided into subproblems",
                    "Subproblems overlap (same subproblems solved multiple times)",
                    "Optimal solution can be constructed from optimal sub-solutions",
                    "Subproblems have a finite, describable state space"
                ],
                postconditions=[
                    "Time complexity often reduced from exponential to polynomial",
                    "Space complexity proportional to number of unique states",
                    "Solution builds up from base cases"
                ],
                complexity_impact="Reduces time complexity by eliminating redundant computation",
                domain_tags=["sequences", "optimization", "combinatorics", "graph_algorithms"],
                confidence=0.9
            ),
            AbilityTemplate(
                id="rate_based_transformation",
                name="Rate-Based Transformation",
                ability_type=AbilityType.RATE_BASED_TRANSFORMATION,
                description="Convert between domains using an intermediate reference point or rate",
                parameters={
                    "rate_table": "Mapping from domain A to reference and reference to domain B",
                    "reference_point": "Common reference for conversion (e.g., USD for currency)",
                    "transformation_function": "Function to apply rate (usually multiplication/division)",
                    "inverse_available": "Whether inverse transformation is also available"
                },
                examples=[
                    "Currency conversion via USD as base",
                    "Unit conversion (metric to imperial via SI units)",
                    "Coordinate system transformations",
                    "Encoding/decoding via intermediate format"
                ],
                preconditions=[
                    "Conversion is transitive (A→B = A→RATE→B)",
                    "Reference point is stable or rates can be obtained",
                    "Transformation function is well-defined and invertible (or pseudo-invertible)"
                ],
                postconditions=[
                    "Conversion possible even without direct A→B rate",
                    "Enables chaining multiple conversions",
                    "Allows offline operation with cached rates"
                ],
                complexity_impact="Enables conversion with O(1) lookup after rate acquisition",
                domain_tags=["currency", "units", "coordinates", "encoding"],
                confidence=0.9
            ),
            AbilityTemplate(
                id="fault_tolerant_querying",
                name="Fault Tolerant Querying",
                ability_type=AbilityType.FAULT_TOLERANT_QUERYING,
                description="Design queries that degrade gracefully with structured fallback responses",
                parameters={
                    "primary_query": "The main query to execute",
                    "fallback_strategy": "What to do when primary fails (alternative, partial, default)",
                    "error_handling": "How to classify and respond to different error types",
                    "response_structure": "Consistent format for success and failure responses"
                },
                examples=[
                    "DNS lookup returning structured response with availability status",
                    "API calls with circuit breaker pattern",
                    "Database queries with cached fallbacks",
                    "Network requests with timeout and retry logic"
                ],
                preconditions=[
                    "Query can fail in identifiable ways",
                    "Some value can be provided even when primary goal fails",
                    "Callers can handle structured responses"
                ],
                postconditions=[
                    "System remains usable even when external services fail",
                    "Failures provide diagnostic information",
                    "User experience degrades gracefully rather than catastrophically"
                ],
                complexity_impact="Adds constant overhead for error handling but improves reliability",
                domain_tags=["networking", "apis", "databases", "external_services"],
                confidence=0.8
            ),
            AbilityTemplate(
                id="iterative_refinement_loop",
                name="Iterative Refinement Loop",
                ability_type=AbilityType.ITERATIVE_REFINEMENT,
                description="Progressively improve solution through feedback cycles and measurement",
                parameters={
                    "baseline_establishment": "How to establish initial solution or state",
                    "feedback_mechanism": "How to measure quality or identify issues",
                    "improvement_strategy": "How to modify solution based on feedback",
                    "termination_condition": "When to stop iterating (good enough, max iterations, convergence)"
                },
                examples=[
                    "Interactive currency converter with input validation",
                    "Auto-shutdown with configurable delay and confirmation",
                    "Optimization algorithms (gradient descent, hill climbing)",
                    "Debugging through hypothesis testing and fixing"
                ],
                preconditions=[
                    "Baseline solution can be established",
                    "Feedback can be gathered about solution quality",
                    "Improvements can be made based on feedback",
                    "Process can converge or reach acceptable state"
                ],
                postconditions=[
                    "Solution quality improves over iterations",
                    "Process terminates when goals met or no further improvement possible",
                    "Final solution better than initial baseline"
                ],
                complexity_impact="Adds iterative overhead but can dramatically improve solution quality",
                domain_tags=["optimization", "debugging", "tuning", "interactive_systems"],
                confidence=0.75
            )
        ]
        
        for ability in core_abilities:
            self.abilities[ability.id] = ability
        
        self.logger.info(f"Initialized {len(self.abilities)} core abilities")
    
    def extract_relevant_abilities(self, problem_description: str) -> List[AbilityTemplate]:
        """Extract abilities relevant to a problem description"""
        if not problem_description:
            return []
        
        problem_lower = problem_description.lower()
        relevant_abilities = []
        
        for ability in self.abilities.values():
            # Simple keyword matching - in production would use more sophisticated NLP
            relevance_score = 0.0
            
            # Check description keywords
            desc_words = set(ability.description.lower().split())
            problem_words = set(problem_lower.split())
            word_overlap = len(desc_words.intersection(problem_words))
            if word_overlap > 0:
                relevance_score += word_overlap * 0.1
            
            # Check example keywords
            for example in ability.examples:
                example_words = set(example.lower().split())
                example_overlap = len(example_words.intersection(problem_words))
                if example_overlap > 0:
                    relevance_score += example_overlap * 0.05
            
            # Check domain tags
            for tag in ability.domain_tags:
                if tag in problem_lower:
                    relevance_score += 0.2
            
            # Check precondition matches (simplified)
            for precondition in ability.preconditions:
                prec_words = set(precondition.lower().split())
                prec_overlap = len(prec_words.intersection(problem_words))
                if prec_overlap > 0:
                    relevance_score += prec_overlap * 0.05
            
            # Apply threshold
            if relevance_score >= self.config.pattern_recognition_threshold:
                # Boost confidence based on usage and success
                adjusted_confidence = min(0.99, ability.confidence + (ability.usage_count * 0.01))
                ability_copy = AbilityTemplate(
                    id=ability.id,
                    name=ability.name,
                    ability_type=ability.ability_type,
                    description=ability.description,
                    parameters=ability.parameters,
                    examples=ability.examples,
                    preconditions=ability.preconditions,
                    postconditions=ability.postconditions,
                    complexity_impact=ability.complexity_impact,
                    domain_tags=ability.domain_tags,
                    confidence=adjusted_confidence,
                    usage_count=ability.usage_count,
                    last_used=ability.last_used
                )
                relevant_abilities.append(ability_copy)
        
        # Sort by confidence and usage
        relevant_abilities.sort(key=lambda x: (x.confidence, x.usage_count), reverse=True)
        return relevant_abilities[:10]  # Return top 10
    
    def apply_ability(self, ability_id: str, problem_context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply an ability to a problem context"""
        if ability_id not in self.abilities:
            return {"error": f"Ability {ability_id} not found"}
        
        ability = self.abilities[ability_id]
        
        # Update usage statistics
        ability.usage_count += 1
        from datetime import datetime
        ability.last_used = datetime.now().isoformat()
        self._save_abilities()
        
        # In a full implementation, this would actually apply the ability
        # For now, return guidance on how to apply it
        return {
            "ability_applied": ability.name,
            "ability_id": ability_id,
            "guidance": f"Apply {ability.name} ability: {ability.description}",
            "parameters_needed": ability.parameters,
            "expected_outcome": ability.postconditions,
            "complexity_impact": ability.complexity_impact
        }
    
    def get_all_abilities(self) -> List[AbilityTemplate]:
        """Get all available abilities"""
        return list(self.abilities.values())
    
    def add_ability(self, ability: AbilityTemplate) -> bool:
        """Add a new ability to the library"""
        try:
            self.abilities[ability.id] = ability
            self._save_abilities()
            self.logger.info(f"Added ability: {ability.name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add ability {ability.name}: {e}")
            return False
    
    def update_ability_usage(self, ability_id: str, success: bool):
        """Update ability usage statistics based on outcome"""
        if ability_id in self.abilities:
            ability = self.abilities[ability_id]
            ability.usage_count += 1
            from datetime import datetime
            ability.last_used = datetime.now().isoformat()
            
            # Adjust confidence based on success
            if success:
                ability.confidence = min(0.99, ability.confidence + 0.02)
            else:
                ability.confidence = max(0.1, ability.confidence - 0.01)
            
            self._save_abilities()
            return True
        return False

# Global instance (will be initialized with config)
_ability_manager: Optional[AbilityManager] = None

def get_ability_manager() -> AbilityManager:
    """Get global ability manager instance"""
    global _ability_manager
    if _ability_manager is None:
        # This will be properly initialized in brain/system.py with config
        from core.unified_config import get_config
        config = get_config()
        _ability_manager = AbilityManager(config.intelligence)
    return _ability_manager