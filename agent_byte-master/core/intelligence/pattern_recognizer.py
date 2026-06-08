"""
Pattern Recognition System for GhostGoat
Identifies algorithmic patterns in problem descriptions and maps to ability templates
"""
from __future__ import annotations

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger("ghostgoat.intelligence.pattern")

@dataclass
class RecognizedPattern:
    """Represents a recognized algorithmic pattern"""
    pattern_id: str
    name: str
    description: str
    confidence: float
    parameters: Dict[str, Any]
    applicable_ability_ids: List[str]
    evidence: str  # What text/keywords triggered this recognition

class PatternRecognizer:
    """
    Recognizes algorithmic and problem-solving patterns from problem descriptions.
    Maps text descriptions to known ability templates.
    """
    
    def __init__(self, intelligence_config):
        self.config = intelligence_config
        self.logger = logging.getLogger("ghostgoat.intelligence.pattern.recognizer")
        
        # Pattern definitions with keywords, examples, and mappings to abilities
        self.patterns = self._initialize_patterns()
    
    def _initialize_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize pattern definitions"""
        return {
            "search_in_sorted": {
                "name": "Search in Sorted Data",
                "description": "Finding an element in a sorted collection",
                "keywords": [
                    "search", "find", "lookup", "sorted", "ordered", 
                    "position", "locate", "element", "array", "list",
                    "binary", "logarithmic", "O(log n)"
                ],
                "indicator_phrases": [
                    "find X in sorted",
                    "search for element",
                    "locate position",
                    "efficient search",
                    "sorted array",
                    "ordered collection"
                ],
                "applicable_abilities": ["divide_and_conquer_search"],
                "complexity_pattern": r"O\(log\s+n\)"
            },
            "prime_testing": {
                "name": "Prime Number Testing",
                "description": "Testing if a number is prime or finding primes",
                "keywords": [
                    "prime", "primes", "primality", "prime number",
                    "is prime", "find primes", "prime factorization",
                    "sieve", "Miller-Rabin", "composite"
                ],
                "indicator_phrases": [
                    "check if prime",
                    "find all primes",
                    "primality test",
                    "is it a prime",
                    "prime number",
                    "factorization"
                ],
                "applicable_abilities": ["mathematical_optimization_sqrt"],
                "complexity_pattern": r"O\(\s*√n\s*\)"
            },
            "dynamic_problem": {
                "name": "Dynamic Programming Problem",
                "description": "Problems with overlapping subproblems and optimal substructure",
                "keywords": [
                    "dynamic programming", "DP", "memoization", "overlapping",
                    "subproblems", "optimal substructure", "recurrence",
                    "tabulation", "top-down", "bottom-up", "cache",
                    "Fibonacci", "knapsack", "longest", "shortest"
                ],
                "indicator_phrases": [
                    "optimal solution",
                    "minimum number of",
                    "maximum number of",
                    "count number of ways",
                    "find length of",
                    "compute recursively"
                ],
                "applicable_abilities": ["dynamic_programming_memoization"],
                "complexity_pattern": r"O\(n\s+times\s+something\)"
            },
            "currency_conversion": {
                "name": "Currency/Unit Conversion",
                "description": "Converting between different currencies or units",
                "keywords": [
                    "convert", "conversion", "currency", "exchange",
                    "rate", "USD", "EUR", "unit", "metric", "imperial",
                    "transform", "change units", "multiply", "divide"
                ],
                "indicator_phrases": [
                    "convert X to Y",
                    "exchange rate",
                    "how many Y in X",
                    "currency conversion",
                    "unit conversion",
                    "transform units"
                ],
                "applicable_abilities": ["rate_based_transformation"],
                "complexity_pattern": r"O\(1\)"
            },
            "network_operation": {
                "name": "Network Operation with Error Handling",
                "description": "Network calls requiring fault tolerance",
                "keywords": [
                    "network", "DNS", "API", "HTTP", "request",
                    "resolve", "domain", "IP", "port", "socket",
                    "timeout", "retry", "connection", "failure"
                ],
                "indicator_phrases": [
                    "resolve domain",
                    "check availability",
                    "query DNS",
                    "api call",
                    "handle network",
                    "internet connection"
                ],
                "applicable_abilities": ["fault_tolerant_querying"],
                "complexity_pattern": r"O\(network\s+latency\)"
            },
            "iterative_improvement": {
                "name": "Iterative Improvement Process",
                "description": "Progressively improving a solution through iterations",
                "keywords": [
                    "iterate", "refine", "improve", "optimize",
                    "loop", "converge", "convergence", "gradient",
                    "hill climbing", "simulated annealing", "evolutionary",
                    "adjust", "tune", "calibrate"
                ],
                "indicator_phrases": [
                    "try again",
                    "improve solution",
                    "iteratively refine",
                    "converge to solution",
                    "gradient descent",
                    "optimization"
                ],
                "applicable_abilities": ["iterative_refinement_loop"],
                "complexity_pattern": r"O\(iterations\s+times\s+cost\)"
            },
            "boundary_analysis": {
                "name": "Boundary Condition Analysis",
                "description": "Identifying and handling edge cases and boundary conditions",
                "keywords": [
                    "boundary", "edge case", "corner case", "extreme",
                    "empty", "null", "zero", "maximum", "minimum",
                    "overflow", "underflow", "special case", "degenerate"
                ],
                "indicator_phrases": [
                    "what happens when",
                    "edge case",
                    "boundary condition",
                    "special case",
                    "handle empty input",
                    "when n is very large"
                ],
                "applicable_abilities": ["boundary_condition_thinking"],
                "complexity_pattern": r"\bedge\b|\bboundary\b|\bcorner\b"
            }
        }
    
    def recognize_patterns(self, problem_description: str) -> List[RecognizedPattern]:
        """
        Recognize patterns in a problem description.
        Returns list of recognized patterns with confidence scores.
        """
        if not problem_description:
            return []
        
        recognized = []
        desc_lower = problem_description.lower()
        
        for pattern_id, pattern_def in self.patterns.items():
            confidence = self._calculate_pattern_confidence(
                desc_lower, pattern_def
            )
            
            if confidence >= self.config.pattern_recognition_threshold:
                # Extract evidence (matched keywords/phrases)
                evidence = self._extract_evidence(desc_lower, pattern_def)
                
                # Map applicable abilities
                applicable_abilities = pattern_def["applicable_abilities"]
                
                recognized.append(RecognizedPattern(
                    pattern_id=pattern_id,
                    name=pattern_def["name"],
                    description=pattern_def["description"],
                    confidence=confidence,
                    parameters={
                        "description": pattern_def["description"],
                        "keywords": evidence,
                        "applicable_abilities": applicable_abilities
                    },
                    applicable_ability_ids=applicable_abilities,
                    evidence=evidence
                ))
        
        # Sort by confidence
        recognized.sort(key=lambda x: x.confidence, reverse=True)
        return recognized[:5]  # Return top 5 patterns
    
    def _calculate_pattern_confidence(
        self,
        description: str,
        pattern: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for pattern match"""
        score = 0.0

        # Check keyword matches
        keyword_hits = 0
        total_keywords = len(pattern.get("keywords", []))
        if total_keywords > 0:
            for keyword in pattern["keywords"]:
                if keyword.lower() in description:
                    keyword_hits += 1
            # Normalize: each keyword hit contributes equally, capped at 1.0
            score += min(1.0, keyword_hits / max(1, total_keywords // 2)) * 0.5

        # Check indicator phrase matches
        phrase_hits = 0
        total_phrases = len(pattern.get("indicator_phrases", []))
        if total_phrases > 0:
            for phrase in pattern["indicator_phrases"]:
                if phrase.lower() in description:
                    phrase_hits += 1
            score += (phrase_hits / max(total_phrases, 1)) * 0.5
        
        # Check complexity pattern match
        if pattern.get("complexity_pattern"):
            if re.search(pattern["complexity_pattern"], description):
                score += 0.2
        
        return min(score, 0.99)
    
    def _extract_evidence(self, description: str, pattern: Dict[str, Any]) -> str:
        """Extract evidence keywords/phrases that triggered the pattern"""
        evidence_words = []
        
        for keyword in pattern.get("keywords", []):
            if keyword.lower() in description:
                evidence_words.append(keyword)
        
        for phrase in pattern.get("indicator_phrases", []):
            if phrase.lower() in description:
                evidence_words.append(phrase)
        
        return ", ".join(set(evidence_words)[:10]) if evidence_words else "general match"
    
    def get_recommended_abilities(
        self, 
        problem_description: str
    ) -> List[Tuple[str, float]]:
        """
        Get ability IDs recommended for a problem, with confidence scores.
        Returns list of (ability_id, confidence) tuples.
        """
        patterns = self.recognize_patterns(problem_description)
        
        ability_scores = {}
        for pattern in patterns:
            for ability_id in pattern.applicable_ability_ids:
                # Accumulate confidence across patterns
                if ability_id not in ability_scores:
                    ability_scores[ability_id] = 0.0
                ability_scores[ability_id] += pattern.confidence
        
        # Normalize and return sorted
        if not ability_scores:
            return []
        
        max_score = max(ability_scores.values())
        if max_score > 0:
            normalized = {aid: score/max_score for aid, score in ability_scores.items()}
        else:
            normalized = ability_scores
        
        return sorted(normalized.items(), key=lambda x: x[1], reverse=True)
    
    def add_pattern(self, pattern: Dict[str, Any]) -> bool:
        """Add a new pattern definition"""
        try:
            pattern_id = pattern.get("pattern_id", pattern["name"].lower().replace(" ", "_"))
            self.patterns[pattern_id] = pattern
            self.logger.info(f"Added pattern: {pattern_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add pattern: {e}")
            return False

# Global instance
_pattern_recognizer: Optional[PatternRecognizer] = None

def get_pattern_recognizer() -> PatternRecognizer:
    """Get global pattern recognizer instance"""
    global _pattern_recognizer
    if _pattern_recognizer is None:
        from core.unified_config import get_config
        config = get_config()
        _pattern_recognizer = PatternRecognizer(config.intelligence)
    return _pattern_recognizer