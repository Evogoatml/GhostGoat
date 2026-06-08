"""
Knowledge Frame Management System for GhostGoat
Handles storage, retrieval, and semantic search of knowledge frames
"""
from __future__ import annotations

import logging
import json
import os
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field, asdict
import re

logger = logging.getLogger("ghostgoat.intelligence.knowledge")


@dataclass
class KnowledgeFrame:
    """Semantic frame for structured knowledge representation"""
    id: str
    name: str
    description: str
    domain: str  # e.g., "number_theory", "currency", "networking"
    category: str  # e.g., "concept", "algorithm", "reference"
    content: str  # Main content/body of the knowledge
    tags: List[str] = field(default_factory=list)
    relationships: List[str] = field(default_factory=list)
    confidence: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KnowledgeFrame':
        """Create from dictionary"""
        return cls(**data)
    
    def matches_query(self, query: str, threshold: float = 0.3) -> Tuple[bool, float]:
        """
        Check if this frame matches a query based on keyword and semantic overlap.
        Returns (matches, score).
        """
        query_lower = query.lower()
        score = 0.0
        
        # Check name match
        if self.name.lower() in query_lower:
            score += 0.4
        
        # Check domain match
        if self.domain.lower() in query_lower:
            score += 0.3
        
        # Check tags match
        for tag in self.tags:
            if tag.lower() in query_lower:
                score += 0.1
        
        # Check content keyword match
        content_words = set(self.content.lower().split())
        query_words = set(query_lower.split())
        if content_words:
            overlap = len(content_words.intersection(query_words))
            score += overlap * 0.2 / len(content_words)
        
        return score >= threshold, min(score, 1.0)


class KnowledgeFrameManager:
    """Manages the knowledge frame repository"""
    
    def __init__(self, intelligence_config):
        self.config = intelligence_config
        self.logger = logging.getLogger("ghostgoat.intelligence.knowledge.manager")
        self.frames: Dict[str, KnowledgeFrame] = {}
        self._load_frames()
        
        # Initialize with core knowledge if none exist
        if not self.frames:
            self._initialize_core_knowledge()
            self._save_frames()
    
    def _load_frames(self):
        """Load knowledge frames from storage"""
        frame_file = Path(self.config.knowledge_frame_path) / "knowledge_frames.json"
        try:
            if frame_file.exists():
                with open(frame_file, 'r') as f:
                    data = json.load(f)
                    for frame_data in data.get("frames", []):
                        frame = KnowledgeFrame.from_dict(frame_data)
                        self.frames[frame.id] = frame
                self.logger.info(f"Loaded {len(self.frames)} knowledge frames from {frame_file}")
            else:
                self.logger.info(f"No knowledge frame file found at {frame_file}, will create new")
        except Exception as e:
            self.logger.error(f"Failed to load knowledge frames: {e}")
            self.frames = {}
    
    def _save_frames(self):
        """Save knowledge frames to storage"""
        try:
            frame_dir = Path(self.config.knowledge_frame_path)
            frame_dir.mkdir(parents=True, exist_ok=True)
            frame_file = frame_dir / "knowledge_frames.json"
            
            data = {
                "frames": [frame.to_dict() for frame in self.frames.values()],
                "last_updated": str(Path(__file__).stat().st_mtime)
            }
            
            with open(frame_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info(f"Saved {len(self.frames)} knowledge frames to {frame_file}")
        except Exception as e:
            self.logger.error(f"Failed to save knowledge frames: {e}")
    
    def _initialize_core_knowledge(self):
        """Initialize with core knowledge from training data analysis"""
        core_knowledge = [
            KnowledgeFrame(
                id="prime_numbers",
                name="Prime Numbers",
                description="Prime numbers and their properties for testing and factorization",
                domain="number_theory",
                category="concept",
                content=(
                    "A prime number is a natural number greater than 1 that has no positive divisors other than 1 and itself. "
                    "The first few primes are 2, 3, 5, 7, 11, 13, 17, 19, 23, 29. "
                    "For primality testing, it's sufficient to test divisors up to the square root of n. "
                    "For n < 10^9, trial division is efficient. For larger numbers, probabilistic tests like Miller-Rabin are preferred. "
                    "Common optimizations include checking divisibility by 2 first, then only odd numbers."
                ),
                tags=["math", "number_theory", "algorithms", "primality", "factorization"],
                relationships=["composite_numbers", "euler_totient", "prime_factoring", "greatest_common_divisor"],
                confidence=0.95,
                metadata={"source": "framework/check_prime.py", "algorithms": ["trial_division", "sieve_of_eratosthenes", "miller_rabin"]}
            ),
            KnowledgeFrame(
                id="fibonacci_sequences",
                name="Fibonacci Sequence",
                description="Fibonacci sequence implementations and applications",
                domain="number_theory",
                category="algorithm",
                content=(
                    "The Fibonacci sequence is defined as F(n) = F(n-1) + F(n-2) with F(0)=0, F(1)=1. "
                    "Multiple implementation approaches exist: "
                    "Iterative O(n) time, O(1) space; Recursive O(2^n) time without memoization; "
                    "Dynamic programming O(n) time and space with memoization; "
                    "Matrix exponentiation O(log n) time. "
                    "The golden ratio φ = (1+√5)/2 approximates F(n+1)/F(n). "
                    "Applications include algorithm design, nature modeling, search algorithms (Fibonacci search)."
                ),
                tags=["math", "sequences", "algorithms", "dynamic_programming", "recursion"],
                relationships=["golden_ratio", "lucas_numbers", "matrix_exponentiation"],
                confidence=0.9,
                metadata={"source": "framework/fibonacci.py", "time_complexities": {"iterative": "O(n)", "recursive": "O(2^n)", "dp": "O(n)", "matrix": "O(log n)"}}
            ),
            KnowledgeFrame(
                id="binary_search",
                name="Binary Search Algorithm",
                description="Binary search for sorted data search and optimization problems",
                domain="algorithms",
                category="algorithm",
                content=(
                    "Binary search operates on sorted data to find a target value in O(log n) time. "
                    "Key principle: compare middle element, eliminate half the search space each iteration. "
                    "Variations include: finding first/last occurrence, searching in rotated arrays, "
                    "binary search on answer (for optimization problems where the answer space is monotonic). "
                    "Requires: sorted array, comparison operation, target value. "
                    "Common pitfalls: integer overflow in midpoint calculation, off-by-one errors in boundary updates."
                ),
                tags=["algorithms", "searching", "divide_and_conquer", "logarithmic", "sorted_data"],
                relationships=["binary_search_tree", "interpolation_search", "ternary_search", "binary_search_on_answer"],
                confidence=0.92,
                metadata={"source": "framework/binary_search.py", "variants": ["standard", "find_first", "find_last", "rotated_array", "search_on_answer"]}
            ),
            KnowledgeFrame(
                id="currency_exchange",
                name="Currency Exchange System",
                description="Offline currency conversion system with exchange rate management",
                domain="finance",
                category="system",
                content=(
                    "The currency converter system enables offline currency exchange between supported currencies. "
                    "It uses a base currency (USD) as pivot for multi-currency paths. "
                    "Supported currencies include: USD, EUR, INR, GBP, JPY, AUD, CAD, SGD, CHF, CNY, NZD. "
                    "Conversion formula: amount_in_target = amount / rate_from * rate_to. "
                    "System operates in offline mode using pre-stored exchange rates."
                ),
                tags=["finance", "currency", "exchange", "offline", "conversion"],
                relationships=["exchange_rates", "financial_calculations", "unit_conversion"],
                confidence=0.88,
                metadata={"source": "currency converter.py", "supported_currencies": ["USD", "EUR", "INR", "GBP", "JPY", "AUD", "CAD", "SGD", "CHF", "CNY", "NZD"]}
            ),
            KnowledgeFrame(
                id="dns_resolution",
                name="DNS Resolution System",
                description="Domain Name System lookup and verification for network operations",
                domain="networking",
                category="system",
                content=(
                    "DNS (Domain Name System) translates domain names to IP addresses. "
                    "Key record types: A (IPv4), AAAA (IPv6), MX (mail), CNAME (alias). "
                    "DNS hierarchy: root servers → TLD servers → authoritative servers. "
                    "Common failure modes: NXDOMAIN (non-existent domain), SERVFAIL (server error), "
                    "TIMEOUT (unresponsive server), REFUSED (policy rejection). "
                    "DNS lookup involves iterative queries from client to recursive resolver to authoritative servers. "
                    "TTL (Time To Live) controls caching duration of DNS records."
                ),
                tags=["networking", "dns", "domain_names", "ip_address_mapping", "network_operations"],
                relationships=["tcp_ip_stack", "http_resolver", "ssl_certificate_verification"],
                confidence=0.85,
                metadata={"source": "DNS_Verifier.py", "record_types": ["A", "AAAA", "MX", "CNAME", "NS", "TXT"]}
            ),
            KnowledgeFrame(
                id="armstrong_numbers",
                name="Armstrong Numbers",
                description="Narcissistic numbers and their mathematical properties",
                domain="number_theory",
                category="concept",
                content=(
                    "An Armstrong number (narcissistic number) is a number that equals the sum of its own digits each raised to the power of the number of digits. "
                    "For example: 153 = 1^3 + 5^3 + 3^3 = 153. "
                    "In base 10, Armstrong numbers exist for 1-digit numbers (1-9), 3-digit numbers (153, 370, 371, 407), and beyond. "
                    "Detection algorithm: 1) Count digits, 2) Raise each digit to the count, 3) Sum and compare to original. "
                    "Only 88 Armstrong numbers exist in base 10."
                ),
                tags=["math", "number_theory", "digits", "mathematical_properties"],
                relationships=["prime_numbers", "special_numbers", "digital_invariants"],
                confidence=0.8,
                metadata={"source": "framework/Armstrong_number.py", "known_count": 88}
            ),
            KnowledgeFrame(
                id="system_shutdown",
                name="System Shutdown Process",
                description="Automated system shutdown sequence and timing",
                domain="system_operations",
                category="procedure",
                content=(
                    "The auto-shutdown functionality demonstrates: "
                    "1) User input processing with timeout, "
                    "2) Converting time units (minutes to seconds), "
                    "3) Process execution (shutdown system call), "
                    "4) Countdown notification system. "
                    "System shutdown involves: notifying processes, flushing file systems, stopping services, and powering off hardware."
                ),
                tags=["system", "operations", "shutdown", "automation", "timing"],
                relationships=["process_management", "system_lifecycle", "graceful_shutdown"],
                confidence=0.75,
                metadata={"source": "auto_shutdown.py", "platform": "Windows"}
            ),
            KnowledgeFrame(
                id="factors_and_factorization",
                name="Factor Finding Algorithm",
                description="Algorithm for finding factors of a number efficiently",
                domain="number_theory",
                category="algorithm",
                content=(
                    "Factors of a number n are integers that divide n without remainder. "
                    "Efficient approach: iterate up to √n, when a factor i is found, "
                    "both i and n/i are factors. "
                    "Time complexity: O(√n), Space: O(1). "
                    "This optimization is based on the fact that factors come in pairs. "
                    "For n = 36: factors are 1, 2, 3, 4, 6, 9, 12, 18, 36 (9 factors). "
                    "Application in: prime factorization, GCD computation, number theory problems."
                ),
                tags=["math", "number_theory", "factors", "optimization", "square_root"],
                relationships=["prime_factoring", "greatest_common_divisor", "least_common_multiple"],
                confidence=0.88,
                metadata={"source": "framework/factors.py", "complexity": "O(√n)"}
            )
        ]
        
        for frame in core_knowledge:
            self.frames[frame.id] = frame
        
        self.logger.info(f"Initialized {len(self.frames)} core knowledge frames")
    
    def get_relevant_frames(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve knowledge frames relevant to a query"""
        if not query:
            return []
        
        scored_frames = []
        for frame in self.frames.values():
            matches, score = frame.matches_query(query)
            if matches:
                scored_frames.append((frame, score))
        
        # Sort by score descending
        scored_frames.sort(key=lambda x: x[1], reverse=True)
        
        # Take top k
        results = []
        for frame, score in scored_frames[:top_k]:
            results.append({
                "id": frame.id,
                "name": frame.name,
                "domain": frame.domain,
                "content": frame.content,
                "tags": frame.tags,
                "relevance_score": score,
                "confidence": frame.confidence
            })
        
        return results
    
    def add_frame(self, frame: KnowledgeFrame) -> bool:
        """Add a new knowledge frame"""
        try:
            self.frames[frame.id] = frame
            self._save_frames()
            self.logger.info(f"Added knowledge frame: {frame.name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add frame {frame.name}: {e}")
            return False
    
    def search_by_domain(self, domain: str) -> List[KnowledgeFrame]:
        """Search frames by domain"""
        return [f for f in self.frames.values() if f.domain.lower() == domain.lower()]
    
    def search_by_tag(self, tag: str) -> List[KnowledgeFrame]:
        """Search frames by tag"""
        return [f for f in self.frames.values() if tag.lower() in [t.lower() for t in f.tags]]
    
    def get_related_frames(self, frame_id: str) -> List[KnowledgeFrame]:
        """Get frames related to a given frame by ID"""
        if frame_id not in self.frames:
            return []
        
        frame = self.frames[frame_id]
        related = []
        
        for rel in frame.relationships:
            for f in self.frames.values():
                if f.id == rel or rel.lower() in [t.lower() for t in f.tags] or rel.lower() in f.content.lower():
                    related.append(f)
        
        return list(set(related))[:5]  # Return top 5 unique related frames

# Global instance
_knowledge_frame_manager: Optional[KnowledgeFrameManager] = None

def get_knowledge_frame_manager() -> KnowledgeFrameManager:
    """Get global knowledge frame manager instance"""
    global _knowledge_frame_manager
    if _knowledge_frame_manager is None:
        from core.unified_config import get_config
        config = get_config()
        _knowledge_frame_manager = KnowledgeFrameManager(config.intelligence)
    return _knowledge_frame_manager