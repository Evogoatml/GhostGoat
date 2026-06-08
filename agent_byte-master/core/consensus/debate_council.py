"""GhostGoat Debate Council — Multi-Agent Consensus Engine."""
import json, logging, time
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from core.llm_router.router import LLMRouter

logger = logging.getLogger(__name__)

@dataclass
class Argument:
    agent_role: str
    agent_id: str
    position: str
    reasoning: str
    confidence: float = 0.5
    timestamp: float = field(default_factory=time.time)

@dataclass
class Consensus:
    winning_position: str
    arbiter_reasoning: str
    confidence: float
    arguments: List[Argument]
    dissents: List[Argument]

class DebateCouncil:
    def __init__(self, router: Optional[LLMRouter] = None,
                 roles: Optional[List[Dict[str, str]]] = None):
        self.router = router or LLMRouter()
        self.roles = roles or [
            {"id": "analyst-1", "name": "Analyst", "bias": "favor evidence and data"},
            {"id": "skeptic-1", "name": "Skeptic", "bias": "challenge assumptions, find holes"},
            {"id": "synthesizer-1", "name": "Synthesizer", "bias": "find common ground, reconcile"},
        ]
        self.arbiter_role = {"id": "arbiter-1", "name": "Arbiter", "bias": "pick the strongest argument"}

    def deliberate(self, question: str, context: Optional[str] = None,
                   max_rounds: int = 2) -> Consensus:
        arguments: List[Argument] = []
        for round_num in range(1, max_rounds + 1):
            for role in self.roles:
                position = self._argue(role, question, context, arguments, round_num)
                arguments.append(Argument(
                    agent_role=role["name"],
                    agent_id=role["id"],
                    position=position["stance"],
                    reasoning=position["reasoning"],
                    confidence=position.get("confidence", 0.5)
                ))

        winner = self._arbitrate(question, arguments)
        winning = [a for a in arguments if a.position == winner["position"]]
        dissents = [a for a in arguments if a.position != winner["position"]]
        return Consensus(
            winning_position=winner["position"],
            arbiter_reasoning=winner["reasoning"],
            confidence=winner.get("confidence", 0.5),
            arguments=winning,
            dissents=dissents
        )

    def _argue(self, role: Dict[str, str], question: str, context: Optional[str],
               prior_args: List[Argument], round_num: int) -> Dict[str, Any]:
        system = f"You are {role['name']}, an expert debater. Your bias: {role['bias']}. Provide stance + reasoning."
        prior = "\n---\n".join(f"[{a.agent_role}]: {a.position}\n{a.reasoning}" for a in prior_args) or "No prior arguments."
        prompt = f"Round {round_num}. Question: {question}\nContext: {context or 'None'}\nPrior arguments:\n{prior}\n\nProvide your stance (FOR, AGAINST, or NUANCED) and reasoning. JSON: {{\"stance\": \"...\", \"reasoning\": \"...\", \"confidence\": 0.0-1.0}}"
        raw = self.router.run_prompt(prompt, system=system, model="llama3.2", timeout=30)
        try:
            parsed = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
            return parsed
        except Exception:
            logger.warning("Debate parse failed for %s: %s", role["id"], raw[:100])
            return {"stance": "NUANCED", "reasoning": raw[:500], "confidence": 0.3}

    def _arbitrate(self, question: str, arguments: List[Argument]) -> Dict[str, Any]:
        system = f"You are {self.arbiter_role['name']}. Pick the single best stance based on strength of reasoning."
        all_args = "\n---\n".join(f"[{a.agent_role}] stance={a.position} conf={a.confidence}:\n{a.reasoning}" for a in arguments)
        prompt = f"Question: {question}\nArguments:\n{all_args}\n\nPick winning stance. JSON: {{\"position\": \"...\", \"reasoning\": \"...\", \"confidence\": 0.0-1.0}}"
        raw = self.router.run_prompt(prompt, system=system, model="llama3.2", timeout=30)
        try:
            return json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        except Exception:
            return {"position": "UNRESOLVED", "reasoning": raw[:500], "confidence": 0.0}

