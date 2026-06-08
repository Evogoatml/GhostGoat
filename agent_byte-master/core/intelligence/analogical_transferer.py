"""
Analogical Transfer System for GhostGoat
Enables transfer of abilities and knowledge between different problem domains
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import re

logger = logging.getLogger("ghostgoat.intelligence.analogical")


@dataclass
class TransferResult:
    """Result of an analogical transfer operation"""
    source_domain: str
    target_domain: str
    transferred_ability_id: str
    adaptation_notes: str
    transfer_strength: float  # 0-1 confidence in transfer validity
    mapped_parameters: Dict[str, str]  # source param -> target param mapping


class AnalogicalTransferer:
    """
    Enables transfer of abilities between problem domains.
    Maps known problem patterns to new domains using analogical reasoning.
    """
    
    def __init__(self, intelligence_config):
        self.config = intelligence_config
        self.logger = logging.getLogger("ghostgoat.intelligence.analogical.transferer")
        
        # Define domain mappings for analogical transfer
        self.domain_mappings = self._initialize_domain_mappings()
    
    def _initialize_domain_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Initialize domain-to-domain transfer mappings"""
        return {
            "number_theory": {
                "target_domains": ["cryptography", "optimization", "security"],
                "transfer_strength": 0.8,
                "key_concepts": ["prime_factoring", "modular_arithmetic", "logarithmic_complexity"]
            },
            "currency": {
                "target_domains": ["unit_conversion", "finance", "market_analysis"],
                "transfer_strength": 0.9,
                "key_concepts": ["rate_tables", "offline_mode", "multi_step_conversion"]
            },
            "searching": {
                "target_domains": ["optimization", "database_queries", "decision_making"],
                "transfer_strength": 0.85,
                "key_concepts": ["divide_and_conquer", "space_reduction", "monotonicity"]
            },
            "networking": {
                "target_domains": ["distributed_systems", "microservices", "cloud_computing"],
                "transfer_strength": 0.75,
                "key_concepts": ["fault_tolerance", "retry_logic", "timeout_handling"]
            }
        }
    
    def transfer_abilities(
        self,
        source_abilities: List[Any],
        source_frames: List[Any],
        patterns: List[Any],
        target_problem: str
    ) -> List[TransferResult]:
        """
        Transfer abilities from known domains to a target problem.
        
        Args:
            source_abilities: Extracted abilities relevant to the problem
            source_frames: Knowledge frames relevant to the problem
            patterns: Recognized patterns in the problem
            target_problem: Description of the target problem domain
        
        Returns:
            List of transfer results with adaptation guidance
        """
        if not target_problem:
            return []
        
        transfers = []
        target_lower = target_problem.lower()
        
        for frame in source_frames:
            # Find domains that match the frame's domain
            frame_domain = frame.get("domain", "")
            mapping = self.domain_mappings.get(frame_domain, {})
            
            if mapping:
                target_domains = mapping.get("target_domains", [])
                for target_domain in target_domains:
                    # Check if target problem mentions any target domain keywords
                    if target_domain.lower().replace("_", " ") in target_lower:
                        transfer_strength = mapping.get("transfer_strength", 0.7)
                        
                        # Adapt the frame for the new domain
                        adapted_frame = self._adapt_frame_for_domain(
                            frame, target_domain, target_problem
                        )
                        
                        transfers.append(TransferResult(
                            source_domain=frame_domain,
                            target_domain=target_domain,
                            transferred_ability_id=adapted_frame.get("id", frame.get("id", "unknown")),
                            adaptation_notes=adapted_frame.get("content", ""),
                            transfer_strength=transfer_strength,
                            mapped_parameters={
                                "original_problem": target_problem,
                                "transferred_concept": frame.get("name", ""),
                                "adaptation_factor": str(transfer_strength)
                            }
                        ))
        
        return transfers
    
    def _adapt_frame_for_domain(
        self, 
        frame: Dict[str, Any], 
        target_domain: str,
        target_problem: str
    ) -> Dict[str, Any]:
        """Adapt a knowledge frame for a target domain"""
        adapted = frame.copy()
        
        # Add domain-specific adaptation markers
        adapted["original_domain"] = frame.get("domain")
        adapted["adapted_for"] = target_domain
        adapted["adaptation_timestamp"] = self._get_timestamp()
        
        # Modify content to reflect domain adaptation
        original_content = frame.get("content", "")
        
        # Add domain-specific modifiers if applicable
        domain_modifiers = {
            "cryptography": "In cryptography, this concept is applied to secure key generation and encryption algorithms.",
            "optimization": "This optimization technique is commonly used in algorithmic problem-solving.",
            "unit_conversion": "This conversion methodology applies to various unit systems beyond currency.",
            "distributed_systems": "This principle extends to distributed fault tolerance in microservice architectures."
        }
        
        if target_domain in domain_modifiers:
            adapted["content"] = f"{original_content}\n\nDomain Application ({target_domain}): {domain_modifiers[target_domain]}"
        
        return adapted
    
    def find_analogous_problems(
        self, 
        current_problem: str,
        known_solutions: List[Dict[str, Any]],
        threshold: float = 0.5
    ) -> List[Tuple[str, float, str]]:
        """
        Find previously solved problems that are analogous to the current one.
        Each result contains (problem_description, similarity_score, solution_hint).
        """
        analogous = []
        current_lower = current_problem.lower()
        
        for solution in known_solutions:
            problem_desc = solution.get("problem", "")
            problem_lower = problem_desc.lower()
            
            # Simple similarity via keyword overlap
            current_words = set(re.findall(r'\w+', current_lower))
            problem_words = set(re.findall(r'\w+', problem_lower))
            
            if current_words and problem_words:
                intersection = current_words.intersection(problem_words)
                similarity = len(intersection) / min(len(current_words), len(problem_words))
                
                if similarity >= threshold:
                    hint = solution.get("solution_hint", "Refer to similar pattern")
                    analogous.append((problem_desc, similarity, hint))
        
        analogous.sort(key=lambda x: x[1], reverse=True)
        return analogous[:5]
    
    def create_cross_domain_insight(
        self, 
        source_concept: str, 
        target_domain: str
    ) -> Dict[str, Any]:
        """
        Generate an insight by transferring a concept from one domain to another.
        """
        insights = {
            "number_theory_to_optimization": (
                "Just as prime factorization decomposes a number into fundamental components, "
                "decompose optimization problems into subproblems that can be solved independently "
                "and combined for the optimal solution."
            ),
            "networking_to_distributed_systems": (
                "DNS resolution principles apply to service discovery: "
                "just as DNS uses hierarchical servers to resolve domain names, "
                "service mesh architectures use registries and health checks to locate services."
            ),
            "currency_to_data_transform": (
                "Currency conversion patterns apply to data transformation: "
                "use intermediate canonical forms (like USD in finance) to enable flexible "
                "conversions between different data formats."
            ),
            "search_to_decision_making": (
                "Binary search principles apply to decision trees: "
                "divide the solution space by half with each decision, "
                "targeting the region most likely to contain optimal solutions."
            )
        }
        
        key = f"{source_concept.lower().replace(' ', '_')}_to_{target_domain.lower().replace(' ', '_')}"
        
        if key in insights:
            return {
                "source_concept": source_concept,
                "target_domain": target_domain,
                "insight": insights[key],
                "transfer_type": "concept_mapping"
            }
        
        return {
            "source_concept": source_concept,
            "target_domain": target_domain,
            "insight": f"Consider applying principles from {source_concept} to {target_domain} "
                      f"by identifying structural similarities in problem decomposition.",
            "transfer_type": "general_analogical"
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.now().isoformat()

# Global instance
_analogical_transferer: Optional[AnalogicalTransferer] = None

def get_analogical_transferer() -> AnalogicalTransferer:
    """Get global analogical transferer instance"""
    global _analogical_transferer
    if _analogical_transferer is None:
        from core.unified_config import get_config
        config = get_config()
        _analogical_transferer = AnalogicalTransferer(config.intelligence)
    return _analogical_transferer